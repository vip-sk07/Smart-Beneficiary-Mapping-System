import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

def setup_db():
    print("Running Django Migrations...")
    from django.core.management import call_command
    call_command("migrate", interactive=False)
    
    print("Applying custom schema updates if not present...")
    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE Schemes ADD COLUMN is_active BOOLEAN DEFAULT 1;")
            print("Successfully added is_active to Schemes.")
        except Exception as e:
            print(f"Schema update for Schemes skipped: {e}")

        try:
            cursor.execute("ALTER TABLE Grievances ADD COLUMN admin_remark TEXT NULL;")
            print("Successfully added admin_remark to Grievances.")
        except Exception as e:
            print(f"Schema update for Grievances skipped: {e}")

if __name__ == "__main__":
    setup_db()
