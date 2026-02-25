import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

from django.db import connection

def fix_db():
    print("Fixing db tables...")
    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE Schemes ADD COLUMN is_active BOOLEAN DEFAULT 1;")
            print("Added is_active to Schemes")
        except Exception as e:
            print(f"Failed to add is_active to Schemes: {e}")

        try:
            cursor.execute("ALTER TABLE Grievances ADD COLUMN admin_remark TEXT NULL;")
            print("Added admin_remark to Grievances")
        except Exception as e:
            print(f"Failed to add admin_remark to Grievances: {e}")

if __name__ == "__main__":
    fix_db()
