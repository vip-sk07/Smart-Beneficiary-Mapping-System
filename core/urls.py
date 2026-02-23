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

    # Scheme guide + apply
    path('scheme/<int:scheme_id>/apply/',     views.scheme_apply_guide, name='scheme_apply_guide'),
    path('scheme/<int:scheme_id>/apply-now/', views.apply_scheme,       name='apply_scheme'),

    # My Applications
    path('my-applications/', views.my_applications, name='my_applications'),

    # Grievances
    path('grievance/submit/', views.submit_grievance, name='submit_grievance'),
    path('my-grievances/',    views.my_grievances,    name='my_grievances'),

    # AI Finder (full page)
    path('find-schemes/', views.nlp_scheme_finder, name='nlp_scheme_finder'),

    # AI Voice Bot (AJAX endpoint)
    path('api/voice-bot/', views.voice_bot_nlp, name='voice_bot_nlp'),

    # Admin Stats
    path('admin-stats/', views.admin_stats, name='admin_stats'),

    # Password reset via OTP
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/',      views.verify_otp,      name='verify_otp'),
    path('reset-password/',  views.reset_password,  name='reset_password'),

    # Change password (logged-in)
    path('change-password/', views.change_password, name='change_password'),

    # Delete searches
    path('delete-search/all/',               views.delete_search_all, name='delete_search_all'),
    path('delete-search/<int:user_cat_id>/', views.delete_search,     name='delete_search'),

    # Edit Profile (Backtracking)
    path('edit-profile/', views.edit_profile, name='edit_profile'),

    # Re-check Eligibility
    path('recheck-eligibility/', views.recheck_eligibility, name='recheck_eligibility'),

    # Withdraw Application
    path('application/<int:app_id>/withdraw/', views.withdraw_application, name='withdraw_application'),

    # Admin Grievance Panel
    path('admin/grievances/',                      views.admin_grievances, name='admin_grievances'),
    path('admin/grievances/<int:grv_id>/resolve/', views.resolve_grievance, name='resolve_grievance'),
]