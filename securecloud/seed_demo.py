from app import create_app
from app.models import db, User, LoginEvent
from app.services.auth_service import hash_password
from datetime import datetime, timedelta
import pyotp

app = create_app()

def seed():
    with app.app_context():
        # Check if demo user exists
        if User.query.filter_by(username='demo').first():
            print("Demo user already exists.")
            return

        secret = pyotp.random_base32()
        user = User(
            username='demo',
            email='demo@example.com',
            password_hash=hash_password('Demo@12345'),
            totp_secret=secret,
            mfa_confirmed=True
        )
        db.session.add(user)
        db.session.commit()
        
        # Add some login history
        now = datetime.utcnow()
        history = [
            LoginEvent(user_id=user.id, ts=now - timedelta(days=2), hour=14, ip='192.168.1.5', risk_label='LOW', outcome='success'),
            LoginEvent(user_id=user.id, ts=now - timedelta(days=1), hour=15, ip='192.168.1.5', risk_label='LOW', outcome='success'),
            LoginEvent(user_id=user.id, ts=now - timedelta(hours=5), hour=4, ip='203.0.113.42', risk_label='HIGH', outcome='fail'),
        ]
        db.session.bulk_save_objects(history)
        db.session.commit()
        
        print("\n" + "="*50)
        print("DEMO USER CREATED")
        print("Username: demo")
        print("Password: Demo@12345")
        print(f"TOTP Secret: {secret}")
        print("="*50 + "\n")

if __name__ == '__main__':
    seed()
