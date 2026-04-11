"""
Django settings for Football_Player_Detection_and_Tracking project.
"""

from pathlib import Path
import os
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent


# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = 'django-insecure-wi-e(!&akyw1gh%i*b(-8u8e_%7_1ax3$lzy2_1-m@qg5v-!w$'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']

# FIX: CSRF_TRUSTED_ORIGINS is required for Hugging Face Spaces / iframe deployments
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://huggingface.co',
    'https://*.hf.space',
    'https://shankarlingam-football-analysis.hf.space',
]

# FIX: Cookie settings needed for cross-origin iframe environments (HuggingFace Spaces)
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE   = True
CSRF_COOKIE_SAMESITE    = 'None'
CSRF_COOKIE_SECURE      = True


# ── Application definition ────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'users',
    'admins',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # REMOVED: XFrameOptionsMiddleware blocks iframe embedding on Hugging Face
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Football_Player_Detection_and_Tracking.urls'

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

WSGI_APPLICATION = 'Football_Player_Detection_and_Tracking.wsgi.application'


# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://postgres:IaXENrbaUHWF2U6C@db.akpojkxhztgpueclpzzf.supabase.co:5432/postgres',
        conn_max_age=600
    )
}


# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ── Internationalization ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_MANIFEST_STRICT = False

# ── Media files ───────────────────────────────────────────────────────────────
# Cloudinary Storage Configuration
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dgf0nhyaf',
    'API_KEY': '435631362239581',
    'API_SECRET': 'sF6fdT9PEeazvuFSxsqLeRQEjyk',
}

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ── Misc ──────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# FIX: LOGIN_URL ensures @login_required decorators (if added later) redirect correctly
LOGIN_URL = '/UserLogin'
LOGIN_REDIRECT_URL = '/UserHome/'