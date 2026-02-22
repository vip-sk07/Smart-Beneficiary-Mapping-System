"""
WSGI config for beneficiary_system project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""
import os
import sys

# ── CRITICAL: Patch PyMySQL BEFORE Django loads ANYTHING ──────────────────
# This must run before any Django import to prevent mysqlclient version check
import pymysql
pymysql.install_as_MySQLdb()

# Monkey-patch the version check that Django does on mysqlclient
pymysql.version_info = (2, 2, 1, "final", 0)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beneficiary_system.settings')

application = get_wsgi_application()