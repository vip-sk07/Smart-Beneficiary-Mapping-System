from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, FormView
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from django import forms
from typing import Any
import random
import string

from .models import CustomUser, UserCategories, UserEligibility, Scheme
from .forms import (
    UserRegistrationForm, CategorySelectionForm, LoginForm,
    ForgotPasswordForm, OTPVerifyForm, ResetPasswordForm, ChangePasswordForm,
)


def get_custom_user(django_user):
    return CustomUser.objects.filter(email=django_user.email).first()


def _is_via_google(request):
    """
    True if the logged-in Django user authenticated via Google (allauth).
    Works by checking if a SocialAccount exists for this user.
    """
    if not request.user.is_authenticated:
        return False
    try:
        from allauth.socialaccount.models import SocialAccount
        return SocialAccount.objects.filter(user=request.user, provider='google').exists()
    except Exception:
        return False


# ── Home ───────────────────────────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'home.html')


# ── Register ───────────────────────────────────────────────────────────────
class UserRegistrationView(CreateView):
    model = CustomUser
    form_class = UserRegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        # If user is logged in via Google AND already has a CustomUser → go to dashboard
        if request.user.is_authenticated and _is_via_google(request):
            if get_custom_user(request.user):
                return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def _needs_google_mode(self):
        """True when Google user is logged in but has no CustomUser profile yet."""
        return (
            self.request.user.is_authenticated
            and _is_via_google(self.request)
            and not get_custom_user(self.request.user)
        )

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self._needs_google_mode():
            # Email pre-filled from Google, read-only
            form.fields['email'].initial = self.request.user.email
            form.fields['email'].widget.attrs['readonly'] = True
            # No password needed — allauth already created the Django user
            form.fields['password'].required = False
            form.fields['password'].widget = forms.HiddenInput()
        return form

    def get_initial(self):
        initial = super().get_initial()
        if self._needs_google_mode():
            initial['email'] = self.request.user.email
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['is_google_user'] = self._needs_google_mode()
        return ctx

    def form_valid(self, form: Any) -> HttpResponse:
        custom_user = form.save()
        email = form.cleaned_data['email']
        password = form.cleaned_data.get('password')

        if _is_via_google(self.request):
            # Google path — Django user already exists via allauth, just go to dashboard
            messages.success(self.request, 'Profile completed! Welcome to BenefitBridge.')
            return redirect(self.success_url)

        # Manual registration path — create Django auth user and log in
        try:
            django_user = User.objects.get(username=email)
            messages.info(self.request, 'Account exists! Logging you in.')
        except User.DoesNotExist:
            django_user = User.objects.create_user(
                username=email, email=email, password=password
            )
            messages.success(self.request, 'Registration successful! Welcome to BenefitBridge.')
        login(self.request, django_user,
              backend='django.contrib.auth.backends.ModelBackend')
        return redirect(self.success_url)


# ── Login ──────────────────────────────────────────────────────────────────
class UserLoginView(DjangoLoginView):
    form_class = LoginForm
    template_name = 'login.html'
    redirect_authenticated_user = True
    next_page = reverse_lazy('dashboard')


# ── Logout ─────────────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')


# ── Dashboard ──────────────────────────────────────────────────────────────
def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        if _is_via_google(request):
            # Google user logging in for first time — needs to complete profile
            messages.info(request, 'Please complete your profile to continue.')
            return redirect('register')
        else:
            # Manual user with no profile — log out and ask to register fresh
            logout(request)
            messages.error(request, 'Profile not found. Please register again.')
            return redirect('register')

    past_categories = UserCategories.objects.filter(
        user_id=custom_user.user_id
    ).select_related('category').order_by('-user_cat_id')[:5]

    eligible_schemes = UserEligibility.objects.filter(
        user_id=custom_user.user_id, eligibility_status='Eligible'
    ).select_related('scheme').order_by('-applied_on')

    return render(request, 'dashboard.html', {
        'past_categories': past_categories,
        'eligible_schemes': eligible_schemes,
        'user': custom_user,
    })


# ── Category selection ─────────────────────────────────────────────────────
class CategorySelectionView(FormView):
    template_name = 'categories.html'
    form_class = CategorySelectionForm
    success_url = reverse_lazy('dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: Any) -> HttpResponse:
        selected_categories = form.cleaned_data['categories']
        custom_user = get_custom_user(self.request.user)
        if not custom_user:
            messages.error(self.request, 'User profile not found.')
            return redirect('register')
        for category in selected_categories:
            UserCategories.objects.get_or_create(
                user_id=custom_user.user_id,
                category_id=category.category_id
            )
        with connection.cursor() as cursor:
            cursor.callproc('check_user_eligibility', [custom_user.user_id])
        messages.success(self.request, 'Eligibility checked! View your results below.')
        return super().form_valid(form)


# ── Delete searches ────────────────────────────────────────────────────────
def delete_search(request, user_cat_id):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        custom_user = get_custom_user(request.user)
        if custom_user:
            try:
                uc = UserCategories.objects.get(
                    user_cat_id=user_cat_id, user_id=custom_user.user_id
                )
                UserEligibility.objects.filter(
                    user_id=custom_user.user_id,
                    scheme__target_category_id=uc.category_id
                ).delete()
                uc.delete()
                messages.success(request, f'Search for "{uc.category.category_name}" removed.')
            except UserCategories.DoesNotExist:
                messages.error(request, 'Search record not found.')
    return redirect('dashboard')


def delete_search_all(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        custom_user = get_custom_user(request.user)
        if custom_user:
            UserEligibility.objects.filter(user_id=custom_user.user_id).delete()
            UserCategories.objects.filter(user_id=custom_user.user_id).delete()
            messages.success(request, 'All past searches cleared.')
    return redirect('dashboard')


def eligibility_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect('dashboard')


# ── Scheme Apply Guide ─────────────────────────────────────────────────────
def scheme_apply_guide(request, scheme_id):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        return redirect('login')
    scheme = get_object_or_404(Scheme, scheme_id=scheme_id)
    apply_url = scheme.registration_link or scheme.official_link
    return render(request, 'scheme_apply_guide.html', {
        'scheme': scheme,
        'user': custom_user,
        'apply_url': apply_url,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — EMAIL OTP FLOW
# Step 1: forgot_password  → enter email → OTP sent
# Step 2: verify_otp       → enter 6-digit OTP
# Step 3: reset_password   → enter new password
# ─────────────────────────────────────────────────────────────────────────────

def _generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = ForgotPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].lower().strip()

        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            # Security: same message whether email exists or not
            messages.success(request, 'If that email is registered, an OTP has been sent.')
            return redirect('forgot_password')

        otp = _generate_otp()
        request.session['otp_code']     = otp
        request.session['otp_email']    = email
        request.session['otp_attempts'] = 0

        send_mail(
            subject='BenefitBridge — Password Reset OTP',
            message=(
                f"Hello,\n\n"
                f"Your OTP to reset your BenefitBridge password is:\n\n"
                f"    {otp}\n\n"
                f"This code expires in 10 minutes. Do not share it.\n\n"
                f"If you didn't request this, ignore this email.\n\n"
                f"— BenefitBridge Team"
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@benefitbridge.in'),
            recipient_list=[email],
            fail_silently=False,
        )

        messages.success(request, f'OTP sent to {email}. Check your inbox.')
        return redirect('verify_otp')

    return render(request, 'forgot_password.html', {'form': form})


def verify_otp(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if 'otp_code' not in request.session:
        messages.error(request, 'Session expired. Please request a new OTP.')
        return redirect('forgot_password')

    form = OTPVerifyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        entered  = form.cleaned_data['otp'].strip()
        stored   = request.session.get('otp_code', '')
        attempts = request.session.get('otp_attempts', 0)

        if attempts >= 5:
            for key in ['otp_code', 'otp_email', 'otp_attempts']:
                request.session.pop(key, None)
            messages.error(request, 'Too many wrong attempts. Request a new OTP.')
            return redirect('forgot_password')

        if entered == stored:
            request.session['otp_verified'] = True
            request.session.pop('otp_code', None)
            return redirect('reset_password')
        else:
            request.session['otp_attempts'] = attempts + 1
            remaining = 5 - request.session['otp_attempts']
            messages.error(request, f'Wrong OTP. {remaining} attempt(s) left.')

    return render(request, 'verify_otp.html', {'form': form})


def reset_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if not request.session.get('otp_verified'):
        messages.error(request, 'Please verify your OTP first.')
        return redirect('forgot_password')

    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email    = request.session.get('otp_email', '')
        password = form.cleaned_data['password']

        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()

            for key in ['otp_verified', 'otp_email']:
                request.session.pop(key, None)

            messages.success(request, 'Password reset! Log in with your new password.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Something went wrong. Please try again.')
            return redirect('forgot_password')

    return render(request, 'reset_password.html', {'form': form})


# ── Change Password (logged-in users) ─────────────────────────────────────
def change_password(request):
    if not request.user.is_authenticated:
        return redirect('login')

    form = ChangePasswordForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully!')
        return redirect('dashboard')

    return render(request, 'change_password.html', {'form': form})