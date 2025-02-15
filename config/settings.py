"""
Django settings for podtrack project.

Generated by 'django-admin startproject' using Django 5.0.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
import os
from huey import SqliteHuey

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-9*)v#^@+#-fvdhiy&hw%^s-!)n9h&(-%azjphj3^yythb$$6mc"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite 默认开发服务器端口
    "http://127.0.0.1:5173",
]

# 如果上面的配置还不能解决，可以尝试更宽松的配置：
CORS_ALLOW_ALL_ORIGINS = True  # 开发环境可以使用，生产环境不建议


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",
    'django_filters',
    'drf_spectacular',
    'huey.contrib.djhuey',

    "apps.articles",
    "apps.vocabulary",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Huey Configuration
HUEY = {
    'huey_class': 'huey.SqliteHuey',   # 使用 SQLite 后端
    'name': 'podtrack',                 # 队列名称
    'filename': str(BASE_DIR / 'huey.db'),  # SQLite 数据库文件路径
    'results': True,                    # 启用结果存储
    'store_none': False,                # 不存储 None 结果
    'immediate': False,                 # 使用异步模式
    'utc': True,                        # 使用 UTC 时间
    'consumer': {
        'workers': 4,                   # 工作线程数
        'worker_type': 'thread',        # 使用线程
        'initial_delay': 0.1,           # 启动延迟
        'backoff': 1.15,                # 重试延迟增长率
        'max_delay': 10.0,              # 最大重试延迟
        'scheduler_interval': 1,         # 调度器检查间隔
        'periodic': True,               # 启用周期性任务
        'check_worker_health': True,    # 检查工作线程健康
        'health_check_interval': 1,     # 健康检查间隔
    },
}

DICTIONARY_PATH = BASE_DIR / 'data/stardict.db'

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.CustomPageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': '词汇管理API',
    'DESCRIPTION': '用于管理播客词汇学习的API',
    'VERSION': '1.0.0',
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
