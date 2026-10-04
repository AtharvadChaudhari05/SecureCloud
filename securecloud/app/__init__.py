from flask import Flask
from .config import Config
from .models import db
from flask_wtf.csrf import CSRFProtect
import joblib
import os

csrf = CSRFProtect()
risk_model = None
crypto_policy_model = None

def load_ml_models():
    global risk_model, crypto_policy_model
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml', 'models')
    
    risk_path = os.path.join(models_dir, 'risk_model.joblib')
    crypto_path = os.path.join(models_dir, 'crypto_policy.joblib')
    
    if os.path.exists(risk_path):
        risk_model = joblib.load(risk_path)
    if os.path.exists(crypto_path):
        crypto_policy_model = joblib.load(crypto_path)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    csrf.init_app(app)
    
    load_ml_models()
    
    from .routes.auth import auth_bp
    from .routes.files import files_bp
    from .routes.report import report_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(report_bp)
    
    with app.app_context():
        db.create_all()
        
    return app
