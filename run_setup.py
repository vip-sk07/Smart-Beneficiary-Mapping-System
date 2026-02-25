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
            
        # Missing columns for CustomUser in Users table
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN pension_status BOOLEAN DEFAULT 0;")
            print("Added pension_status to Users.")
        except Exception as e:
            pass
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN disability_cert BOOLEAN DEFAULT 0;")
            print("Added disability_cert to Users.")
        except Exception as e:
            pass
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN unemployment_status BOOLEAN DEFAULT 0;")
            print("Added unemployment_status to Users.")
        except Exception as e:
            pass
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN business_turnover DECIMAL(15,2) NULL;")
            print("Added business_turnover to Users.")
        except Exception as e:
            pass

if __name__ == "__main__":
    setup_db()
