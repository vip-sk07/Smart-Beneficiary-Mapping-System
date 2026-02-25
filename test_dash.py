import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

c = Client(SERVER_NAME='localhost')
email = 'testnewuser@example.com'
u, _ = User.objects.get_or_create(username=email, email=email)
from core.models import CustomUser
CustomUser.objects.get_or_create(email=email, defaults={'name': 'Test New', 'dob': '2000-01-01', 'aadhaar_no': '123456789012'})
c.force_login(u)
try:
    r = c.get('/dashboard/')
    print("Status", r.status_code)
    if r.status_code == 500:
         print(r.content.decode('utf-8'))
except Exception as e:
    import traceback
    traceback.print_exc()
