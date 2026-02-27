import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
django.setup()

def _add_column(cursor, sql, desc):
    try:
        cursor.execute(sql)
        print(f"  ✅ Added: {desc}")
    except Exception as e:
        if 'duplicate column' in str(e).lower() or '1060' in str(e):
            print(f"  ⏭  Already exists: {desc}")
        else:
            print(f"  ❌ FAILED {desc}: {e}")

def _create_table(cursor, sql, desc):
    try:
        cursor.execute(sql)
        print(f"  ✅ Created table: {desc}")
    except Exception as e:
        print(f"  ⏭  Table {desc}: {e}")

def setup_db():
    print("=" * 50)

    # ── Create critical tables FIRST (before migrate, so they always exist) ──
    print("\n[Pre-migrate: Creating missing tables]")
    with connection.cursor() as cursor:
        _create_table(cursor, """
            CREATE TABLE IF NOT EXISTS Announcements (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                message    TEXT NOT NULL,
                is_active  BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, "Announcements")

    print("\nRunning Django Migrations...")
    from django.core.management import call_command
    try:
        call_command("migrate", interactive=False)
    except Exception as e:
        print(f"  ⚠️  migrate warning (non-fatal): {e}")

    print("\nApplying custom schema patches...")
    with connection.cursor() as cursor:

        # ── Create tables that Django migrations might have missed ──────────
        print("\n[Tables]")
        # Announcements already created above, but ensure again
        _create_table(cursor, """
            CREATE TABLE IF NOT EXISTS Announcements (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                message    TEXT NOT NULL,
                is_active  BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, "Announcements")

        # ── Schemes columns ─────────────────────────────────────────────────
        print("\n[Schemes columns]")
        _add_column(cursor,
            "ALTER TABLE Schemes ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
            "Schemes.is_active")
        _add_column(cursor,
            "ALTER TABLE Schemes ADD COLUMN eligibility_rules JSON",
            "Schemes.eligibility_rules")

        # ── Grievances columns ──────────────────────────────────────────────
        print("\n[Grievances columns]")
        _add_column(cursor,
            "ALTER TABLE Grievances ADD COLUMN admin_remark TEXT NULL",
            "Grievances.admin_remark")
        _add_column(cursor,
            "ALTER TABLE Grievances ADD COLUMN resolved_on DATETIME NULL",
            "Grievances.resolved_on")
        _add_column(cursor,
            "ALTER TABLE Grievances ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Open'",
            "Grievances.status")

        # ── Users columns ───────────────────────────────────────────────────
        print("\n[Users columns]")
        for col, typedef in [
            ("pension_status",      "BOOLEAN DEFAULT 0"),
            ("disability_cert",     "BOOLEAN DEFAULT 0"),
            ("unemployment_status", "BOOLEAN DEFAULT 0"),
            ("business_turnover",   "DECIMAL(15,2) NULL"),
        ]:
            _add_column(cursor,
                f"ALTER TABLE Users ADD COLUMN {col} {typedef}",
                f"Users.{col}")

        # ── Rule_Engine columns ─────────────────────────────────────────────
        print("\n[Rule_Engine columns]")
        for col, typedef in [
            ("pension_status",          "BOOLEAN DEFAULT 0"),
            ("disability_cert",         "BOOLEAN DEFAULT 0"),
            ("unemployment_status",     "BOOLEAN DEFAULT 0"),
            ("education_required",      "VARCHAR(100) NULL"),
            ("business_turnover_limit", "DECIMAL(15,2) NULL"),
        ]:
            _add_column(cursor,
                f"ALTER TABLE Rule_Engine ADD COLUMN {col} {typedef}",
                f"Rule_Engine.{col}")

    print("\n" + "=" * 50)
    print("Schema setup complete.")

if __name__ == "__main__":
    setup_db()
