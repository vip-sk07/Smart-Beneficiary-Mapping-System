#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# ── CRITICAL: Patch PyMySQL BEFORE Django loads ANYTHING ──────────────────
import pymysql
pymysql.install_as_MySQLdb()
pymysql.version_info = (2, 2, 1, "final", 0)


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()