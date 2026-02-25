import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def get_error():
    c = Client(SERVER_NAME='localhost')
    u = User.objects.filter(is_superuser=True).first()
    if u:
        c.force_login(u)
        
    for url in ['/platform-admin/schemes/', '/platform-admin/announcements/', '/platform-admin/grievances/']:
        print(f"\n--- Testing URL: {url} ---")
        try:
            r = c.get(url)
            print("Status:", r.status_code)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    get_error()
