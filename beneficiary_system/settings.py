"""
Django settings for beneficiary_system project.
Production-ready for Railway deployment.
"""
from pathlib import Path
import os

# PyMySQL must be installed BEFORE Django loads any MySQL backend
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ───────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-^2w#)8o@q=$e-v$!kba7g3dh4fupg7l^z_ucsxrsdkuzilycy=')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# ── Proxy SSL & HTTPS Settings ─────────────────────────────────────────────
# This fixes the 'Error 400: redirect_uri_mismatch' on Google Login 
# by telling Django it's running behind an HTTPS proxy (Railway).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '.railway.app',
    os.environ.get('RAILWAY_PUBLIC_DOMAIN', ''),
]
ALLOWED_HOSTS = [h for h in ALLOWED_HOSTS if h]

# ── Installed Apps ─────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    'core',
]

SITE_ID = 1

# ── Auth backends ──────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL           = '/login/'
AUTH_USER_MODEL     = 'auth.User'

# ── Middleware ─────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'beneficiary_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'beneficiary_system.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────
MYSQL_HOST = (
    os.environ.get('MYSQL_HOST') or
    os.environ.get('MYSQLHOST') or
    ''
)
MYSQL_USER = (
    os.environ.get('MYSQL_USER') or
    os.environ.get('MYSQLUSER') or
    'root'
)
MYSQL_PASSWORD = (
    os.environ.get('MYSQL_PASSWORD') or
    os.environ.get('MYSQLPASSWORD') or
    ''
)
MYSQL_DATABASE = (
    os.environ.get('MYSQL_DATABASE') or
    os.environ.get('MYSQLDATABASE') or
    'railway'
)
MYSQL_PORT = (
    os.environ.get('MYSQL_PORT') or
    os.environ.get('MYSQLPORT') or
    '3306'
)

if MYSQL_HOST:
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.mysql',
            'NAME':     MYSQL_DATABASE,
            'USER':     MYSQL_USER,
            'PASSWORD': MYSQL_PASSWORD,
            'HOST':     MYSQL_HOST,
            'PORT':     MYSQL_PORT,
            'OPTIONS':  {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                # Force PyMySQL — bypasses mysqlclient version check
                'charset': 'utf8mb4',
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }

# ── Password validation ────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ───────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Kolkata'
USE_I18N      = True
USE_TZ        = True

# ── Static files ───────────────────────────────────────────────────────────
STATIC_URL   = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT  = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Email ──────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL  = f"BenefitBridge <{os.environ.get('EMAIL_HOST_USER', 'noreply@benefitbridge.in')}>"

# ── django-allauth ─────────────────────────────────────────────────────────
ACCOUNT_LOGIN_METHODS             = {'email'}
ACCOUNT_SIGNUP_FIELDS             = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION        = 'none'
ACCOUNT_UNIQUE_EMAIL              = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_USERNAME_REQUIRED         = False
SOCIALACCOUNT_ADAPTER             = 'core.adapters.MySocialAccountAdapter'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    }
}
SOCIALACCOUNT_LOGIN_ON_GET          = True
SOCIALACCOUNT_AUTO_SIGNUP           = True
SOCIALACCOUNT_SIGNUP_FIELDS         = []
SOCIALACCOUNT_EMAIL_REQUIRED        = True
SOCIALACCOUNT_EMAIL_VERIFICATION    = 'none'
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

# ── CSRF ───────────────────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = ['https://*.railway.app']
railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
if railway_domain:
    CSRF_TRUSTED_ORIGINS.append(f'https://{railway_domain}')