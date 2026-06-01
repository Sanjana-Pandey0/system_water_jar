import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'wjs-secret-key-change-in-production-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'water_jar.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    WTF_CSRF_ENABLED = True
    BUSINESS_NAME = "AquaFlow Water Supply"
    BUSINESS_ADDRESS = "123 Water Lane, Industrial Area"
    BUSINESS_CITY = "Mumbai"
    BUSINESS_STATE = "Maharashtra"
    BUSINESS_PIN = "400001"
    BUSINESS_MOBILE = "+91 98765 43210"
    BUSINESS_EMAIL = "info@aquaflow.com"
    BUSINESS_GST = "27AABCU9603R1ZX"
    DEFAULT_JAR_RATE = 30.00
    JAR_WARNING_THRESHOLD = 10

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
