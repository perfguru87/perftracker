import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME', 'perftracker_db'),
        'USER': os.environ.get('DB_USER', 'perftracker_user'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'perftracker_password'),
        'HOST': os.environ.get('DB_HOST', 'db'),
        'PORT': os.environ.get('DB_PORT', '5432')
    }
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
MAX_UPLOAD_SIZE = 104857600
ARTIFACTS_STORAGE_DIR = '/usr/src/app/perftracker/artifacts/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_ROOT = 'static'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
}
