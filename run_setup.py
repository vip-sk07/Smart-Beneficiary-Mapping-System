import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

def setup_db():
    print("Running Django Migrations...")
    from django.core.management import call_command
    call_command("migrate", interactive=False)
    
    print("Applying custom scheme flags if not present...")
    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE Schemes ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("Successfully added is_active to Schemes")
        except Exception as e:
            # If column exists, it will throw Duplicate Column error which we ignore
            print(f"Schema update skipped/failed (Expected if already exists): {e}")

if __name__ == "__main__":
    setup_db()
