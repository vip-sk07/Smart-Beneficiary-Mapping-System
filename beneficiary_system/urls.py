from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Override allauth pages with our own
    path('auth/login/',             RedirectView.as_view(url='/login/',    permanent=False)),
    path('auth/signup/',            RedirectView.as_view(url='/register/', permanent=False)),
    path('auth/3rdparty/signup/',   RedirectView.as_view(url='/register/', permanent=False)),
    path('auth/', include('allauth.urls')),
    path('', include('core.urls')),
]