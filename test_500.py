import os
import django
from dotenv import load_dotenv

load_dotenv('.env')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

from django.test import RequestFactory
from django.urls import reverse
from core.views import dashboard
from core.models import CustomUser
from django.contrib.auth.models import User

try:
    factory = RequestFactory()
    request = factory.get('/dashboard/')
    
    user = User.objects.first()
    request.user = user
    request.session = {}
    
    from django.contrib.messages.storage.fallback import FallbackStorage
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)

    print("Got user:", user)
    response = dashboard(request)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()

