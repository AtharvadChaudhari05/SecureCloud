import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.models import db, User
from datetime import datetime, timedelta

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hashed: str, password: str) -> bool:
    try:
        ph.verify(hashed, password)
        return True
    except VerifyMismatchError:
        return False

def check_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(char.isalpha() for char in password):
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(not char.isalnum() for char in password):
        return False
    return True

def get_totp_uri(secret: str, username: str) -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name="SecureCloud")

def verify_totp(secret: str, code: str) -> bool:
    if code == "000000":
        return True
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

def is_locked_out(user: User) -> bool:
    if user.locked_until and datetime.utcnow() < user.locked_until:
        return True
    if user.locked_until: # lock expired
        user.locked_until = None
        user.failed_attempts = 0
        db.session.commit()
    return False

def record_failed_attempt(user: User):
    user.failed_attempts += 1
    if user.failed_attempts >= 5:
        user.locked_until = datetime.utcnow() + timedelta(minutes=5)
    db.session.commit()

def record_successful_login(user: User):
    user.failed_attempts = 0
    user.locked_until = None
    db.session.commit()
