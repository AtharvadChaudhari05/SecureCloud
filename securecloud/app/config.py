import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-super-secret-key-do-not-use-in-prod')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///securecloud.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEMO_MODE = os.environ.get('DEMO_MODE', 'True').lower() == 'true'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    
    WEBAUTHN_RP_ID = os.environ.get('WEBAUTHN_RP_ID', 'localhost')
    WEBAUTHN_RP_NAME = os.environ.get('WEBAUTHN_RP_NAME', 'SecureCloud')
    WEBAUTHN_ORIGIN = os.environ.get('WEBAUTHN_ORIGIN', 'http://localhost:5000')
    STORAGE_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'storage')
    os.makedirs(STORAGE_FOLDER, exist_ok=True)
