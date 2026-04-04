import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-t-travel-mvp-development-key",
)
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost,testserver",
).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.common",
    "apps.accounts",
    "apps.cities",
    "apps.carriers",
    "apps.tickets",
    "apps.routes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sqlite_database_config():
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DJANGO_SQLITE_NAME", str(BASE_DIR / "t_travel.sqlite3")),
        "OPTIONS": {
            "timeout": int(os.getenv("DJANGO_SQLITE_TIMEOUT", "30")),
        },
    }


def _postgres_database_config():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError("DATABASE_URL must use postgres:// or postgresql://")
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
        options = {}
        for key in (
            "sslmode",
            "sslrootcert",
            "sslcert",
            "sslkey",
            "target_session_attrs",
            "application_name",
            "options",
        ):
            if query.get(key):
                options[key] = query[key]
        if os.getenv("POSTGRES_SSLMODE", "").strip():
            options["sslmode"] = os.getenv("POSTGRES_SSLMODE", "").strip()
        if os.getenv("POSTGRES_APPLICATION_NAME", "").strip():
            options["application_name"] = os.getenv("POSTGRES_APPLICATION_NAME", "").strip()
        if os.getenv("POSTGRES_OPTIONS", "").strip():
            options["options"] = os.getenv("POSTGRES_OPTIONS", "").strip()
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote((parsed.path or "/")[1:] or ""),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "127.0.0.1",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": _env_flag("POSTGRES_CONN_HEALTH_CHECKS", True),
            "OPTIONS": options,
        }

    postgres_db = os.getenv("POSTGRES_DB", "").strip()
    if not postgres_db:
        return None

    options = {}
    if os.getenv("POSTGRES_SSLMODE", "").strip():
        options["sslmode"] = os.getenv("POSTGRES_SSLMODE", "").strip()
    if os.getenv("POSTGRES_APPLICATION_NAME", "").strip():
        options["application_name"] = os.getenv("POSTGRES_APPLICATION_NAME", "").strip()
    if os.getenv("POSTGRES_OPTIONS", "").strip():
        options["options"] = os.getenv("POSTGRES_OPTIONS", "").strip()

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": postgres_db,
        "USER": os.getenv("POSTGRES_USER", "").strip(),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "PORT": os.getenv("POSTGRES_PORT", "5432").strip() or "5432",
        "CONN_MAX_AGE": int(os.getenv("POSTGRES_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": _env_flag("POSTGRES_CONN_HEALTH_CHECKS", True),
        "OPTIONS": options,
    }


DATABASES = {
    "default": _postgres_database_config() or _sqlite_database_config()
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Novosibirsk")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}

DATA_DIR = Path(os.getenv("T_TRAVEL_DATA_DIR", str(PROJECT_ROOT / "data")))

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
