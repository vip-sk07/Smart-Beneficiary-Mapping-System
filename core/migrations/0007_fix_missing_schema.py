"""
Migration 0007: Safely add missing columns/tables to Railway MySQL.
Uses raw SQL with IF NOT EXISTS patterns to be idempotent (safe to run multiple times).
"""
from django.db import migrations, connection


def add_schemes_is_active(apps, schema_editor):
    """Add is_active column to Schemes if it doesn't already exist."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'Schemes'
            AND COLUMN_NAME = 'is_active'
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute("ALTER TABLE Schemes ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
            print("  ✅ Added Schemes.is_active")
        else:
            print("  ⏭  Schemes.is_active already exists")


def add_schemes_eligibility_rules(apps, schema_editor):
    """Add eligibility_rules JSON column to Schemes if it doesn't already exist."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'Schemes'
            AND COLUMN_NAME = 'eligibility_rules'
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute("ALTER TABLE Schemes ADD COLUMN eligibility_rules JSON")
            print("  ✅ Added Schemes.eligibility_rules")
        else:
            print("  ⏭  Schemes.eligibility_rules already exists")


def ensure_announcements_table(apps, schema_editor):
    """Create Announcements table if it doesn't exist (safety net for Railway)."""
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'Announcements'
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            cursor.execute("""
                CREATE TABLE Announcements (
                    id         INT AUTO_INCREMENT PRIMARY KEY,
                    message    TEXT NOT NULL,
                    is_active  BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  ✅ Created Announcements table")
        else:
            print("  ⏭  Announcements table already exists")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_announcement'),
    ]

    operations = [
        migrations.RunPython(ensure_announcements_table, noop),
        migrations.RunPython(add_schemes_is_active, noop),
        migrations.RunPython(add_schemes_eligibility_rules, noop),
    ]
