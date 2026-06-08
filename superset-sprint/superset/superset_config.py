# Superset Production Configuration
# Place in /app/pythonpath/superset_config.py inside container

import os

# Database
SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{os.getenv('SUPERSET_DB_USER', 'superset')}:{os.getenv('SUPERSET_DB_PASSWORD', 'superset_password_2024')}@{os.getenv('SUPERSET_DB_HOST', 'db')}:{os.getenv('SUPERSET_DB_PORT', 5432)}/{os.getenv('SUPERSET_DB_NAME', 'superset')}"

# Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'redis_password_2024')
CACHE_TYPE = "redis"
CACHE_REDIS_HOST = REDIS_HOST
CACHE_REDIS_PORT = REDIS_PORT
CACHE_REDIS_PASSWORD = REDIS_PASSWORD
CACHE_DEFAULT_TIMEOUT = 300

# Security
SECRET_KEY = os.getenv("SUPERSET_SECRET_KEY", "change-me-in-production-32chars-min")

# Feature Flags
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "ALERT_REPORTS": True,
    "DASHBOARD_NATIVE_FILTERS": True,
}

# Guest Token (for embedding)
GUEST_TOKEN_JWT_SECRET = os.getenv("GUEST_TOKEN_JWT_SECRET", SECRET_KEY)
GUEST_TOKEN_JWT_ALGO = "HS256"

# Row Level Security
ROW_LEVEL_SECURITY_ENABLED = True

# Celery
CELERY_CONFIG = {
    "broker_url": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0",
    "result_backend": f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/1",
}

# Logging
LOG_LEVEL = "INFO"
