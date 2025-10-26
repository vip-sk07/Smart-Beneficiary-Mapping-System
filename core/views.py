from django.shortcuts import render, redirect
from django.views.generic import CreateView, FormView
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.db import connection
from typing import Any
from .models import CustomUser, UserCategories, UserEligibility, Scheme
from .forms import UserRegistrationForm, CategorySelectionForm, LoginForm

def home(request):
    return render(request, 'home.html')

class UserRegistrationView(CreateView):
    model = CustomUser
    form_class = UserRegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('dashboard')  # Redirect to dashboard after register

    def form_valid(self, form: Any) -> HttpResponse:
        custom_user = form.save()
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        
        # Handle duplicate: Get or create Django User, login either way
        try:
            django_user = User.objects.get(username=email)
            messages.info(self.request, 'User exists! Logging you in.')
        except User.DoesNotExist:
            django_user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )
            messages.success(self.request, 'Registration successful! Welcome to dashboard.')
        
        login(self.request, django_user)
        return super().form_valid(form)

class LoginView(LoginView):
    form_class = LoginForm
    template_name = 'login.html'
    redirect_authenticated_user = True  # Redirect if already logged in
    next_page = reverse_lazy('dashboard')  # Redirect to dashboard after login

class CategorySelectionView(FormView):
    template_name = 'categories.html'
    form_class = CategorySelectionForm
    success_url = reverse_lazy('dashboard')  # Redirect to dashboard after selection

    def form_valid(self, form: Any) -> HttpResponse:
        selected_categories = form.cleaned_data['categories']
        django_user = self.request.user
        custom_user = CustomUser.objects.get(email=django_user.email)
        for category in selected_categories:
            UserCategories.objects.get_or_create(
                user_id=custom_user.user_id, 
                category_id=category.category_id
            )
        with connection.cursor() as cursor:
            cursor.callproc('check_user_eligibility', [custom_user.user_id])
        messages.success(self.request, 'Eligibility checked! View your dashboard.')
        return super().form_valid(form)

def eligibility_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect('dashboard')  # Redirect to dashboard (combined view)

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    django_user = request.user
    custom_user = CustomUser.objects.get(email=django_user.email)
    
    # Past categories (latest 5)
    past_categories = UserCategories.objects.filter(
        user_id=custom_user.user_id
    ).select_related('category').order_by('-user_cat_id')[:5]
    
    # Eligible schemes history
    eligible_schemes = UserEligibility.objects.filter(
        user_id=custom_user.user_id, eligibility_status='Eligible'
    ).select_related('scheme').order_by('-applied_on')
    
    context = {
        'past_categories': past_categories,
        'eligible_schemes': eligible_schemes,
        'user': custom_user
    }
    return render(request, 'dashboard.html', context)