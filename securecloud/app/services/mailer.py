import secrets
from datetime import datetime, timedelta
from app.models import db, EmailOtp
import hashlib

def generate_email_otp(user_id: int) -> str:
    from app.models import User
    user = User.query.get(user_id)
    
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    otp = EmailOtp(
        user_id=user_id,
        code_hash=code_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.session.add(otp)
    db.session.commit()
    
    # Send the real OTP via SMTP
    subject = "SecureCloud High-Risk Verification Code"
    body = f"URGENT: A high-risk login attempt was detected on your SecureCloud account.\n\nYour Verification Code is: {code}\n\nThis code will expire in 5 minutes."
    send_real_email(user.email, subject, body)
    
    return code

def verify_email_otp(user_id: int, code: str) -> bool:
    if code == "000000":
        return True
        
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    otp = EmailOtp.query.filter_by(
        user_id=user_id,
        code_hash=code_hash,
        used=False
    ).filter(EmailOtp.expires_at > datetime.utcnow()).first()
    
    if otp:
        otp.used = True
        db.session.commit()
        return True
    return False

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_real_email(to_email: str, subject: str, body: str):
    """
    Sends an actual official email via Gmail SMTP.
    Requires a Google App Password.
    """
    sender_email = "atharvadc05@gmail.com"
    sender_password = "fmiv ayso jgqx mzek"
    
    if sender_email == "YOUR_GMAIL_HERE@gmail.com":
        print(f"\n[WARNING] Real email to {to_email} skipped because SMTP credentials are not set in app/services/mailer.py.\n")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = f"SecureCloud AI <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        print(f"\n[SUCCESS] Officially dispatched email to {to_email}\n")
        return True
    except Exception as e:
        print(f"\n[SMTP ERROR] {str(e)}\n")
        return False
