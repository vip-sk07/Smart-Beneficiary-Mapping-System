from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, FormView
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings
from django import forms
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
import json
import random
import string
from typing import Any

from .models import CustomUser, UserCategories, UserEligibility, Scheme, Application, Grievance, Category, RuleEngine
from .forms import (
    UserRegistrationForm, CategorySelectionForm, LoginForm,
    ForgotPasswordForm, OTPVerifyForm, ResetPasswordForm, ChangePasswordForm,
    GrievanceForm, EditProfileForm,
)




def _is_via_google(request):
    if not request.user.is_authenticated:
        return False
    try:
        from allauth.socialaccount.models import SocialAccount
        return SocialAccount.objects.filter(user=request.user, provider='google').exists()
    except Exception:
        return False


# ── Home ───────────────────────────────────────────────────────────────────
def get_custom_user(django_user):
    if not django_user.is_authenticated:
        return None
    email = django_user.email
    if not email:
        return None
    return CustomUser.objects.filter(email__iexact=email).first()


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
        if request.user.is_authenticated and _is_via_google(request):
            if get_custom_user(request.user):
                return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def _needs_google_mode(self):
        return (
            self.request.user.is_authenticated
            and _is_via_google(self.request)
            and not get_custom_user(self.request.user)
        )

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self._needs_google_mode():
            form.fields['email'].initial = self.request.user.email
            form.fields['email'].widget.attrs['readonly'] = True
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
            messages.success(self.request, 'Profile completed! Welcome to Smart Beneficiary Mapping System.')
            return redirect('dashboard')

        django_user, _ = User.objects.get_or_create(
            username=email, defaults={'email': email}
        )
        if password:
            django_user.set_password(password)
            django_user.email = email
            django_user.save()

        login(self.request, django_user,
              backend='django.contrib.auth.backends.ModelBackend')
        messages.success(self.request, 'Account created! Welcome to Smart Beneficiary Mapping System.')
        return redirect('dashboard')


# ── Login ──────────────────────────────────────────────────────────────────
class UserLoginView(DjangoLoginView):
    template_name = 'login.html'
    form_class = LoginForm

    def get_success_url(self):
        return reverse_lazy('dashboard')


def logout_view(request):
    logout(request)
    return redirect('home')


# ── Helper: match score ────────────────────────────────────────────────────
def _calculate_match_score(custom_user, scheme):
    """Returns 0-100 representing how well the user fits the scheme rules."""
    try:
        rules = RuleEngine.objects.filter(scheme=scheme)
        if not rules.exists():
            return 75

        from datetime import date
        today = date.today()
        dob = custom_user.dob
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        total_criteria = 0
        matched_criteria = 0

        for rule in rules:
            if rule.age_min is not None or rule.age_max is not None:
                total_criteria += 1
                age_ok = True
                if rule.age_min is not None and age < rule.age_min:
                    age_ok = False
                if rule.age_max is not None and age > rule.age_max:
                    age_ok = False
                if age_ok:
                    matched_criteria += 1

            if rule.gender:
                total_criteria += 1
                if rule.gender.lower() in ['any', 'all'] or \
                   rule.gender.lower() == (custom_user.gender or '').lower():
                    matched_criteria += 1

            if rule.min_income is not None or rule.max_income is not None:
                total_criteria += 1
                income = float(custom_user.income or 0)
                income_ok = True
                if rule.min_income is not None and income < float(rule.min_income):
                    income_ok = False
                if rule.max_income is not None and income > float(rule.max_income):
                    income_ok = False
                if income_ok:
                    matched_criteria += 1

        if total_criteria == 0:
            return 80
        return min(100, int((matched_criteria / total_criteria) * 100))
    except Exception:
        return 75


# ── Dashboard ──────────────────────────────────────────────────────────────
def dashboard(request):
    try:
        if not request.user.is_authenticated:
            return redirect('login')
            
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_stats')
            
        custom_user = get_custom_user(request.user)
        if not custom_user:
            if _is_via_google(request):
                messages.info(request, 'Please complete your profile to continue.')
                return redirect('register')
            else:
                logout(request)
                messages.error(request, 'Profile not found. Please register again.')
                return redirect('register')

        past_categories = UserCategories.objects.filter(
            user_id=custom_user.user_id
        ).select_related('category').order_by('-user_cat_id')[:5]

        # Search & filter
        search_q    = request.GET.get('q', '').strip()
        filter_state = request.GET.get('state', '').strip()
        filter_type  = request.GET.get('type', '').strip()

        eligible_qs = UserEligibility.objects.filter(
            user_id=custom_user.user_id, eligibility_status='Eligible'
        ).select_related('scheme').order_by('-applied_on')

        if search_q:
            eligible_qs = eligible_qs.filter(
                Q(scheme__scheme_name__icontains=search_q) |
                Q(scheme__description__icontains=search_q) |
                Q(scheme__benefits__icontains=search_q)
            )
        if filter_state:
            eligible_qs = eligible_qs.filter(scheme__state__iexact=filter_state)
        if filter_type:
            eligible_qs = eligible_qs.filter(scheme__benefit_type__iexact=filter_type)

        # Add match score
        eligible_schemes = []
        for el in eligible_qs:
            score = _calculate_match_score(custom_user, el.scheme)
            eligible_schemes.append({'eligibility': el, 'score': score})

        # Dropdown options
        all_eligible = UserEligibility.objects.filter(
            user_id=custom_user.user_id, eligibility_status='Eligible'
        ).select_related('scheme')
        states = sorted(set(e.scheme.state for e in all_eligible if e.scheme.state))
        benefit_types = sorted(set(e.scheme.benefit_type for e in all_eligible if e.scheme.benefit_type))

        total_eligible   = UserEligibility.objects.filter(
            user_id=custom_user.user_id, eligibility_status='Eligible').count()
        total_categories = UserCategories.objects.filter(user_id=custom_user.user_id).count()

        applications = Application.objects.filter(
            user_id=custom_user.user_id
        ).select_related('scheme').order_by('-applied_on')[:5]

        grievances = Grievance.objects.filter(
            user_id=custom_user.user_id
        ).select_related('scheme').order_by('-raised_on')[:3]

        active_announcement = Announcement.objects.filter(is_active=True).first()

        return render(request, 'dashboard.html', {
            'past_categories':  past_categories,
            'eligible_schemes': eligible_schemes,
            'user':             custom_user,
            'search_q':         search_q,
            'filter_state':     filter_state,
            'filter_type':      filter_type,
            'announcement':     active_announcement,
            'states':           states,
            'benefit_types':    benefit_types,
            'total_eligible':   total_eligible,
            'total_categories': total_categories,
            'applications':     applications,
            'grievances':       grievances,
        })
    except Exception as e:
        import traceback
        return HttpResponse(f"<pre>{traceback.format_exc()}</pre>", status=500)


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

    existing_app = Application.objects.filter(
        user_id=custom_user.user_id, scheme_id=scheme_id
    ).first()

    score = _calculate_match_score(custom_user, scheme)

    return render(request, 'scheme_apply_guide.html', {
        'scheme':       scheme,
        'user':         custom_user,
        'apply_url':    apply_url,
        'existing_app': existing_app,
        'match_score':  score,
    })


# ── Apply to a Scheme ──────────────────────────────────────────────────────
@require_POST
def apply_scheme(request, scheme_id):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        return redirect('login')

    scheme = get_object_or_404(Scheme, scheme_id=scheme_id)
    is_eligible = UserEligibility.objects.filter(
        user_id=custom_user.user_id, scheme_id=scheme_id,
        eligibility_status='Eligible'
    ).exists()

    if not is_eligible:
        messages.error(request, 'You are not eligible for this scheme.')
        return redirect('scheme_apply_guide', scheme_id=scheme_id)

    app, created = Application.objects.get_or_create(
        user_id=custom_user.user_id,
        scheme_id=scheme_id,
        defaults={'status': 'Pending'}
    )

    if created:
        messages.success(
            request,
            f'Application submitted! Reference ID: BB-{app.app_id}. '
            f'Track it under "My Applications".'
        )
    else:
        messages.info(
            request,
            f'You already applied. Reference ID: BB-{app.app_id} | Status: {app.status}'
        )
    return redirect('scheme_apply_guide', scheme_id=scheme_id)


# ── My Applications ────────────────────────────────────────────────────────
def my_applications(request):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        return redirect('login')

    applications = Application.objects.filter(
        user_id=custom_user.user_id
    ).select_related('scheme', 'scheme__target_category').order_by('-applied_on')

    approved_count  = applications.filter(status='Approved').count()
    pending_count   = applications.filter(status='Pending').count()
    rejected_count  = applications.filter(status='Rejected').count()
    withdrawn_count = applications.filter(status='Withdrawn').count()

    return render(request, 'my_applications.html', {
        'applications':    applications,
        'user':            custom_user,
        'approved_count':  approved_count,
        'pending_count':   pending_count,
        'rejected_count':  rejected_count,
        'withdrawn_count': withdrawn_count,
    })


# ── Grievance Submission ───────────────────────────────────────────────────
def submit_grievance(request):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        return redirect('login')

    eligible_scheme_ids = UserEligibility.objects.filter(
        user_id=custom_user.user_id, eligibility_status='Eligible'
    ).values_list('scheme_id', flat=True)
    eligible_schemes = Scheme.objects.filter(scheme_id__in=eligible_scheme_ids)

    if request.method == 'POST':
        form = GrievanceForm(request.POST, scheme_queryset=eligible_schemes)
        if form.is_valid():
            scheme_obj = form.cleaned_data.get('scheme')
            # Duplicate check — same scheme + status Open
            duplicate_qs = Grievance.objects.filter(
                user_id=custom_user.user_id,
                status='Open',
            )
            if scheme_obj:
                duplicate_qs = duplicate_qs.filter(scheme=scheme_obj)
            else:
                duplicate_qs = duplicate_qs.filter(scheme__isnull=True)
            if duplicate_qs.exists():
                messages.error(
                    request,
                    'You already have an open grievance for this scheme. '
                    'Please wait for it to be resolved before raising another.'
                )
                return render(request, 'grievance_form.html', {
                    'form': form, 'user': custom_user,
                })
            grievance = Grievance(
                user_id=custom_user.user_id,
                scheme=scheme_obj,
                complaint=form.cleaned_data['complaint'],
                status='Open',
            )
            grievance.save()
            messages.success(
                request,
                f'Grievance GRV-{grievance.grievance_id} submitted. We will review it shortly.'
            )
            return redirect('my_grievances')
    else:
        form = GrievanceForm(scheme_queryset=eligible_schemes)

    return render(request, 'grievance_form.html', {
        'form': form,
        'user': custom_user,
    })


# ── My Grievances ──────────────────────────────────────────────────────────
def my_grievances(request):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        return redirect('login')

    grievances = Grievance.objects.filter(
        user_id=custom_user.user_id
    ).select_related('scheme').order_by('-raised_on')

    return render(request, 'my_grievances.html', {
        'grievances': grievances,
        'user':       custom_user,
    })


# ── AI Voice Bot NLP (AJAX) ────────────────────────────────────────────────
def voice_bot_nlp(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    custom_user = get_custom_user(request.user)
    if not custom_user:
        return JsonResponse({'error': 'Profile not found'}, status=400)

    try:
        data  = json.loads(request.body)
        query = data.get('query', '').lower().strip()
    except (json.JSONDecodeError, AttributeError):
        query = request.POST.get('query', '').lower().strip()

    if not query:
        return JsonResponse({'error': 'query is required'}, status=400)

    intent_map = [
        {'intent': 'Agricultural Support',   'keywords': ['farmer','farming','crop','kisan','agriculture','field','harvest','irrigation','paddy','wheat','rural'], 'confidence': 0.95},
        {'intent': 'Senior Citizen Welfare', 'keywords': ['pension','old','elderly','senior','retired','grandmother','grandfather','aged'], 'confidence': 0.92},
        {'intent': 'Educational Support',    'keywords': ['student','school','scholarship','college','education','study','tuition','degree','university','merit'], 'confidence': 0.93},
        {'intent': 'Women Empowerment',      'keywords': ['woman','women','female','girl','mahila','widow','mother','maternity'], 'confidence': 0.91},
        {'intent': 'Disability & Health',    'keywords': ['disabled','disability','handicap','divyang','blind','health','medical','hospital'], 'confidence': 0.90},
        {'intent': 'Business & MSME',        'keywords': ['business','loan','msme','startup','entrepreneur','shop','trade','industry'], 'confidence': 0.89},
        {'intent': 'Housing Support',        'keywords': ['house','housing','home','shelter','construction','pmay','awas'], 'confidence': 0.88},
        {'intent': 'Unemployment & Labour',  'keywords': ['unemployed','unemployment','job','work','labour','worker','wage','mgnrega','skill'], 'confidence': 0.87},
    ]

    matched_intent = 'General Welfare'
    confidence = 0.60
    for entry in intent_map:
        if any(kw in query for kw in entry['keywords']):
            matched_intent = entry['intent']
            confidence = entry['confidence']
            break

    eligible = UserEligibility.objects.filter(
        user_id=custom_user.user_id, eligibility_status='Eligible'
    ).select_related('scheme')

    query_words = set(query.split())
    scored = []
    for ue in eligible:
        text = (
            (ue.scheme.scheme_name or '') + ' ' +
            (ue.scheme.description or '') + ' ' +
            (ue.scheme.benefits or '')
        ).lower()
        score = sum(1 for w in query_words if w in text)
        scored.append((score, ue.scheme))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched = [s for sc, s in scored if sc > 0][:5]
    if not matched:
        matched = [s for _, s in scored[:3]]

    return JsonResponse({
        'intent':          matched_intent,
        'confidence':      confidence,
        'matched_schemes': [{'id': s.scheme_id, 'name': s.scheme_name} for s in matched],
        'total_eligible':  eligible.count(),
    })


# ── NLP Scheme Finder (full page) ─────────────────────────────────────────
def nlp_scheme_finder(request):
    if not request.user.is_authenticated:
        return redirect('login')

    custom_user = get_custom_user(request.user)
    results = []
    query   = ''

    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        if query:
            stop_words = {'want','need','looking','help','with','that','this','have',
                          'from','about','what','schemes','scheme','benefit','government',
                          'india','apply','get','some','please','find'}
            keywords = [w for w in query.lower().split() if len(w) > 3 and w not in stop_words]

            if keywords:
                q_filter = Q()
                for kw in keywords:
                    q_filter |= (
                        Q(scheme_name__icontains=kw) |
                        Q(description__icontains=kw) |
                        Q(benefits__icontains=kw) |
                        Q(benefit_type__icontains=kw)
                    )
                matched_schemes = Scheme.objects.filter(q_filter).distinct()[:12]
                for scheme in matched_schemes:
                    score = _calculate_match_score(custom_user, scheme) if custom_user else 70
                    results.append({'scheme': scheme, 'score': score})
                results.sort(key=lambda x: x['score'], reverse=True)

    return render(request, 'nlp_finder.html', {
        'user':    custom_user,
        'results': results,
        'query':   query,
    })


# ── Admin Stats Dashboard ──────────────────────────────────────────────────
def admin_stats(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_staff:
        messages.error(request, 'Admin access only.')
        return redirect('dashboard')

    total_users      = CustomUser.objects.count()
    total_apps       = Application.objects.count()
    total_grievances = Grievance.objects.count()
    open_grievances  = Grievance.objects.filter(status='Open').count()
    total_eligible   = UserEligibility.objects.filter(eligibility_status='Eligible').count()
    total_checks     = UserEligibility.objects.count()
    total_schemes    = Scheme.objects.count()
    total_categories = Category.objects.count()
    eligibility_rate = round((total_eligible / total_checks) * 100, 1) if total_checks else 0

    apps_by_status = (
        Application.objects
        .values('status')
        .annotate(count=Count('app_id'))
        .order_by('status')
    )
    top_schemes = (
        Application.objects
        .values('scheme__scheme_name', 'scheme__benefit_type', 'scheme__state')
        .annotate(count=Count('app_id'))
        .order_by('-count')[:5]
    )
    schemes_by_category = (
        Scheme.objects
        .values('target_category__category_name')
        .annotate(count=Count('scheme_id'))
        .order_by('-count')[:8]
    )
    recent_users = CustomUser.objects.order_by('-created_at')[:10]

    return render(request, 'admin_stats.html', {
        'total_users':         total_users,
        'total_apps':          total_apps,
        'total_grievances':    total_grievances,
        'open_grievances':     open_grievances,
        'total_eligible':      total_eligible,
        'total_checks':        total_checks,
        'total_schemes':       total_schemes,
        'total_categories':    total_categories,
        'eligibility_rate':    eligibility_rate,
        'apps_by_status':      apps_by_status,
        'top_schemes':         top_schemes,
        'schemes_by_category': schemes_by_category,
        'recent_users':        recent_users,
    })


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET — EMAIL OTP FLOW
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
            messages.success(request, 'If that email is registered, an OTP has been sent.')
            return redirect('forgot_password')

        otp = _generate_otp()
        request.session['otp_code']     = otp
        request.session['otp_email']    = email
        request.session['otp_attempts'] = 0

        try:
            send_mail(
                subject='Smart Beneficiary Mapping System — Password Reset OTP',
                message=(
                    f"Hello,\n\nYour OTP to reset your Smart Beneficiary Mapping System password is:\n\n"
                    f"    {otp}\n\nThis code expires in 10 minutes. Do not share it.\n\n"
                    f"If you didn't request this, ignore this email.\n\n— Smart Beneficiary Mapping System Team"
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@benefitbridge.in'),
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f'OTP sent to {email}. Check your inbox.')
            return redirect('verify_otp')
        except Exception as e:
            print(f"Email Error: {e}")
            messages.error(request, 'Unable to send email right now due to a server configuration issue. Please try again later.')
            return redirect('forgot_password')
            
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


# ── Change Password ────────────────────────────────────────────────────────
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


# ── Edit Profile (Backtracking) ─────────────────────────────────────────────
def edit_profile(request):
    if not request.user.is_authenticated:
        return redirect('login')
    custom_user = get_custom_user(request.user)
    if not custom_user:
        return redirect('login')

    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=custom_user)
        if form.is_valid():
            form.save()
            # Re-run eligibility with updated profile data
            with connection.cursor() as cursor:
                cursor.callproc('check_user_eligibility', [custom_user.user_id])
            messages.success(request, 'Profile updated! Your eligibility has been recalculated.')
            return redirect('dashboard')
    else:
        form = EditProfileForm(instance=custom_user)

    return render(request, 'edit_profile.html', {'form': form, 'user': custom_user})


# ── Re-check Eligibility ───────────────────────────────────────────────
def recheck_eligibility(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        custom_user = get_custom_user(request.user)
        if custom_user:
            with connection.cursor() as cursor:
                cursor.callproc('check_user_eligibility', [custom_user.user_id])
            messages.success(request, 'Eligibility rechecked successfully!')
    return redirect('dashboard')


# ── Withdraw Application ─────────────────────────────────────────────────
def withdraw_application(request, app_id):
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        custom_user = get_custom_user(request.user)
        if custom_user:
            try:
                app = Application.objects.get(
                    app_id=app_id, user_id=custom_user.user_id, status='Pending'
                )
                app.status = 'Withdrawn'
                app.save()
                messages.success(request, f'Application BB-{app_id} withdrawn successfully.')
            except Application.DoesNotExist:
                messages.error(request, 'Application not found or cannot be withdrawn.')
    return redirect('my_applications')


# ── Admin: List All Grievances ───────────────────────────────────────────
def admin_grievances(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_staff:
        messages.error(request, 'Admin access only.')
        return redirect('dashboard')
        
    try:
        status_filter = request.GET.get('status', 'Open')
        grievances_qs = Grievance.objects.select_related('user', 'scheme').order_by('-raised_on')

        if status_filter in ['Open', 'Resolved']:
            grievances_qs = grievances_qs.filter(status=status_filter)

        open_count     = Grievance.objects.filter(status='Open').count()
        resolved_count = Grievance.objects.filter(status='Resolved').count()

        return render(request, 'admin_grievances.html', {
            'grievances':    grievances_qs,
            'status_filter': status_filter,
            'open_count':    open_count,
            'resolved_count': resolved_count,
        })
    except Exception as e:
        import traceback
        return HttpResponse(f"<pre>{traceback.format_exc()}</pre>", status=500)


# ── Admin: Resolve a Grievance ─────────────────────────────────────────────
def resolve_grievance(request, grv_id):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_staff:
        messages.error(request, 'Admin access only.')
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            from django.utils import timezone
            grv = Grievance.objects.select_related('user').get(grievance_id=grv_id)
            grv.status      = 'Resolved'
            grv.resolved_on = timezone.now()
            grv.admin_remark = request.POST.get('admin_remark', '').strip()
            grv.save()
            # Email the user
            user_email = grv.user.email
            if user_email:
                scheme_name = grv.scheme.scheme_name if grv.scheme else 'General'
                send_mail(
                    subject=f'Smart Beneficiary Mapping System — Grievance GRV-{grv_id} Resolved',
                    message=(
                        f"Dear {grv.user.name},\n\n"
                        f"Your grievance (GRV-{grv_id}) related to '{scheme_name}' "
                        f"has been resolved.\n\n"
                        f"Admin Remark: {grv.admin_remark or 'No additional remarks.'}\n\n"
                        f"Thank you for reaching out to Smart Beneficiary Mapping System.\n\n"
                        f"\u2014 Smart Beneficiary Mapping System Team"
                    ),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@benefitbridge.in'),
                    recipient_list=[user_email],
                    fail_silently=True,
                )
            messages.success(request, f'Grievance GRV-{grv_id} marked as Resolved.')
        except Grievance.DoesNotExist:
            messages.error(request, 'Grievance not found.')
    return redirect('admin_grievances')


# ─────────────────────────────────────────────────────────────────────────────
# NEW FEATURES: GEMINI CHAT, ADMIN TOOLS, SCHEME MANAGER
# ─────────────────────────────────────────────────────────────────────────────

import csv
import google.generativeai as genai
from .models import Announcement
from .forms import SchemeForm

@require_POST
def gemini_chat(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
        
    user_msg = request.POST.get('message', '').strip()
    if not user_msg:
        return JsonResponse({'error': 'Empty message'}, status=400)
        
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        return JsonResponse({'error': 'AI Chat is currently unavailable (Missing API Key)'}, status=503)
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Build prompt context
        custom_user = get_custom_user(request.user)
        context = "You are a helpful assistant for the Smart Beneficiary Mapping System in India.\n"
        if custom_user:
            context += f"The user asking is {custom_user.name}, Age: {custom_user.dob}, Gender: {custom_user.gender}, Income: {custom_user.income}, Occupation: {custom_user.occupation}.\n"
            
            eligible = UserEligibility.objects.filter(user_id=custom_user.user_id, eligibility_status='Eligible').select_related('scheme')
            if eligible.exists():
                schemes = ", ".join([e.scheme.scheme_name for e in eligible])
                context += f"They are currently eligible for: {schemes}.\n"
                
        context += "Answer their query clearly, concisely, and exclusively regarding government schemes, benefits or platform navigation.\n"
        context += f"User Query: {user_msg}"
        
        response = model.generate_content(context)
        return JsonResponse({'reply': response.text})
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return JsonResponse({'error': 'Failed to connect to AI server. Please try again later.'}, status=500)


def admin_users(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
        
    search_query = request.GET.get('q', '').strip()
    users = CustomUser.objects.all().order_by('-created_at')
    
    if search_query:
        users = users.filter(Q(name__icontains=search_query) | Q(email__icontains=search_query) | Q(aadhaar_no__icontains=search_query))
        
    return render(request, 'admin_users.html', {'users': users, 'search_query': search_query})


def admin_export_csv(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="smart_beneficiary_system_export.csv"'
    writer = csv.writer(response)
    
    # Export Data Choice
    export_type = request.GET.get('type', 'users')
    
    if export_type == 'users':
        writer.writerow(['User ID', 'Name', 'Email', 'Phone', 'DOB', 'Gender', 'Aadhaar', 'Income', 'Occupation'])
        for u in CustomUser.objects.all():
            writer.writerow([u.user_id, u.name, u.email, u.phone, u.dob, u.gender, u.aadhaar_no, u.income, u.occupation])
            
    elif export_type == 'applications':
        writer.writerow(['App ID', 'User Name', 'Scheme Name', 'Status', 'Applied On'])
        for a in Application.objects.select_related('user', 'scheme').all():
            writer.writerow([a.app_id, a.user.name if a.user else '', a.scheme.scheme_name if a.scheme else '', a.status, a.applied_on])
            
    return response


def admin_announcements(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
        
    try:
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'create':
                msg = request.POST.get('message', '').strip()
                is_active = request.POST.get('is_active') == 'on'
                if msg:
                    # If marking as active, optionally set all others to inactive
                    if is_active:
                        Announcement.objects.all().update(is_active=False)
                    Announcement.objects.create(message=msg, is_active=is_active)
                    messages.success(request, 'Announcement created successfully.')
            elif action == 'delete':
                ann_id = request.POST.get('ann_id')
                Announcement.objects.filter(id=ann_id).delete()
                messages.success(request, 'Announcement deleted.')
            elif action == 'toggle':
                ann_id = request.POST.get('ann_id')
                ann = Announcement.objects.filter(id=ann_id).first()
                if ann:
                    if not ann.is_active:
                        Announcement.objects.all().update(is_active=False)
                    ann.is_active = not ann.is_active
                    ann.save()
                
            return redirect('admin_announcements')
            
        announcements = Announcement.objects.all().order_by('-created_at')
        return render(request, 'admin_announcements.html', {'announcements': announcements})
    except Exception as e:
        import traceback
        return HttpResponse(f"<pre>{traceback.format_exc()}</pre>", status=500)


def admin_schemes(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
    try:
        schemes = Scheme.objects.all().order_by('scheme_name')
        return render(request, 'scheme_manager.html', {'schemes': schemes})
    except Exception as e:
        import traceback
        return HttpResponse(f"<pre>{traceback.format_exc()}</pre>", status=500)


def scheme_create(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
    if request.method == 'POST':
        form = SchemeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scheme created successfully!')
            return redirect('admin_schemes')
    else:
        form = SchemeForm()
    return render(request, 'scheme_form.html', {'form': form, 'title': 'Create New Scheme'})


def scheme_edit(request, scheme_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
    scheme = get_object_or_404(Scheme, pk=scheme_id)
    if request.method == 'POST':
        form = SchemeForm(request.POST, instance=scheme)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scheme updated successfully!')
            return redirect('admin_schemes')
    else:
        form = SchemeForm(instance=scheme)
    return render(request, 'scheme_form.html', {'form': form, 'title': 'Edit Scheme'})


def scheme_delete(request, scheme_id):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect('home')
    scheme = get_object_or_404(Scheme, pk=scheme_id)
    if request.method == 'POST':
        scheme.delete()
        messages.success(request, 'Scheme deleted successfully!')
        return redirect('admin_schemes')
    return render(request, 'scheme_confirm_delete.html', {'scheme': scheme})