import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    BASE_URL = "https://www.fitnesslogger.app"

class DevConfig(Config):
    DEBUG = True
    BASE_URL = "http://127.0.0.1:5000"
    TRUSTED_HOSTS = ['127.0.0.1', 'localhost']
    DB_PATH = os.path.join(Config.BASE_DIR, "dev.db")

class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    BASE_URL = "https://www.fitnesslogger.app"
    SESSION_COOKIE_SAMESITE='Lax'
    TRUSTED_HOSTS = ['fitnesslogger.app', 'www.fitnesslogger.app']
    DB_PATH = os.path.join(Config.BASE_DIR, "fitnesslogger.db")


    