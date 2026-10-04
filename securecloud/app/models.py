from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    totp_secret = db.Column(db.String(32), nullable=False)
    mfa_confirmed = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LoginEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    ts = db.Column(db.DateTime, default=datetime.utcnow)
    hour = db.Column(db.Integer)
    device_hash = db.Column(db.String(64))
    ip = db.Column(db.String(45))
    failed_count = db.Column(db.Integer)
    new_device = db.Column(db.Integer)
    new_ip = db.Column(db.Integer)
    risk_label = db.Column(db.String(20))
    risk_prob = db.Column(db.Float)
    outcome = db.Column(db.String(20)) # success, fail, pending

class FileRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer)
    sensitivity = db.Column(db.Integer) # 0, 1, 2
    session_risk = db.Column(db.Integer) # 0, 1, 2
    algo = db.Column(db.String(50))
    nonce = db.Column(db.LargeBinary(12))
    wrapped_key = db.Column(db.LargeBinary)
    sha256 = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
class EmailOtp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
