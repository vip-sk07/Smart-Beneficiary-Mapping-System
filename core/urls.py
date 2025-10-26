from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),  # Login path
    path('dashboard/', views.dashboard, name='dashboard'),
    path('categories/', views.CategorySelectionView.as_view(), name='categories'),
    path('eligibility/', views.eligibility_view, name='eligibility'),
    path('logout/', views.logout_view, name='logout'),
]