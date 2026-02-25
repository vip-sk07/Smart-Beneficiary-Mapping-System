import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
import django
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass

django.setup()

from django.test import Client
from django.contrib.auth.models import User
import traceback

c = Client(SERVER_NAME='localhost')
try:
    u = User.objects.filter(email='karanraj2006rk@gmail.com').first()
    if u:
        c.force_login(u)
        r = c.get('/admin-stats/')
        print('Status:', r.status_code)
        if r.status_code == 500:
            print(r.content.decode('utf-8'))
    else:
        print("User not found")
except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()

try:
    u = User.objects.filter(email='navis.donel@gmail.com').first()
    if u:
        c.force_login(u)
        r = c.get('/dashboard/')
        print('Status:', r.status_code)
        if r.status_code == 500:
            print(r.content.decode('utf-8'))
    else:
        print("User not found")
except Exception as e:
    print("Exception occurred mapping dashboard:")
    traceback.print_exc()
