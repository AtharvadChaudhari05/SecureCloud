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

        # Create sample files
        from app.models import File
        from app.services.crypto_service import encrypt_file_data, choose_cipher
        import uuid

        # Create a sample text file
        sample_text = b"This is a highly confidential document."
        cipher_class = choose_cipher(2, 0, 1) # Sensitivity 2, Risk 0, Size 1KB
        ct, nonce, wrap, algo = encrypt_file_data(sample_text, cipher_class, b"demo_user_1")
        
        file_id = str(uuid.uuid4())
        with open(f"storage/{file_id}.bin", 'wb') as f:
            f.write(ct)
            
        f1 = File(
            id=file_id,
            user_id=user.id,
            original_name="Confidential_Report.txt",
            size=len(sample_text),
            sensitivity=2,
            algo=algo.decode(),
            nonce=nonce,
            wrapped_key=wrap
        )
        db.session.add(f1)
        db.session.commit()
        print("Sample encrypted file created.")

if __name__ == '__main__':
    seed()
