"""
Roblox DataStore Manager - Advanced Production Configuration
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///data/app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = "memory://"

    # Caching
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    # App settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload

    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') or None


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/app.db'


class ProductionConfig(Config):
    """Production configuration for Webdock"""
    DEBUG = False

    # MySQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://sheetsdigita:Y2dBbLW7xrSn@localhost/sheetsdigita'

    # Security
    SESSION_COOKIE_SECURE = True

    # Redis caching (if available)
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or "SimpleCache"
    CACHE_REDIS_URL = os.environ.get('REDIS_URL') or None

    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
