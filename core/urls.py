from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/',    views.UserLoginView.as_view(),        name='login'),
    path('logout/',   views.logout_view,                    name='logout'),
    path('dashboard/', views.dashboard,                     name='dashboard'),
    path('categories/', views.CategorySelectionView.as_view(), name='categories'),
    path('eligibility/', views.eligibility_view,            name='eligibility'),

    # Scheme apply guide
    path('scheme/<int:scheme_id>/apply/', views.scheme_apply_guide, name='scheme_apply_guide'),

    # ── Password reset via OTP ─────────────────────────────────────────────
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/',      views.verify_otp,      name='verify_otp'),
    path('reset-password/',  views.reset_password,  name='reset_password'),

    # ── Change password (logged-in) ────────────────────────────────────────
    path('change-password/', views.change_password, name='change_password'),

    # Delete searches
    path('delete-search/all/',           views.delete_search_all,         name='delete_search_all'),
    path('delete-search/<int:user_cat_id>/', views.delete_search,         name='delete_search'),
]