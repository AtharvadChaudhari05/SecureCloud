from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.models import db, User, LoginEvent
from app.services.auth_service import hash_password, verify_password, check_password_strength, get_totp_uri, verify_totp, is_locked_out, record_failed_attempt, record_successful_login
from app.services.risk_service import build_context, predict_risk
from app.services.mailer import generate_email_otp, verify_email_otp, send_real_email
import pyotp
import base64
import io
import qrcode
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def landing():
    return render_template('landing.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not check_password_strength(password):
            flash('Password must be >= 8 chars, and contain at least one letter, digit, and symbol.', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))
            
        secret = pyotp.random_base32()
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            totp_secret=secret
        )
        db.session.add(user)
        db.session.commit()
        
        session['pending_user_id'] = user.id
        return redirect(url_for('auth.qr_setup'))
        
    return render_template('register.html')

@auth_bp.route('/register/confirm', methods=['GET', 'POST'])
def qr_setup():
    user_id = session.get('pending_user_id')
    if not user_id:
        return redirect(url_for('auth.register'))
        
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        code = request.form.get('totp_code')
        if verify_totp(user.totp_secret, code):
            user.mfa_confirmed = True
            db.session.commit()
            session.pop('pending_user_id')
            
            # Dispatch official SMTP email
            send_real_email(user.email, "Welcome to SecureCloud", "Your SecureCloud account has been successfully created and your MFA is active.")
            flash(f'Registration successful! An automated setup confirmation email was sent to {user.email}.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid code. Try again.', 'danger')
            
    uri = get_totp_uri(user.totp_secret, user.username)
    qr = qrcode.make(uri)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return render_template('qr_setup.html', qr_b64=qr_b64, secret=user.totp_secret)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))
            
        if is_locked_out(user):
            flash('Account locked due to multiple failed attempts. Try again in 5 minutes.', 'danger')
            return redirect(url_for('auth.login'))
            
        if not verify_password(user.password_hash, password):
            record_failed_attempt(user)
            log_event = LoginEvent(user_id=user.id, outcome='fail')
            db.session.add(log_event)
            db.session.commit()
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))
            
        # Password correct. Score risk.
        demo_override = {
            'active': current_app.config['DEMO_MODE'] and request.form.get('demo_override') == '1',
            'hour': request.form.get('hour'),
            'device_hash': request.form.get('device'),
            'ip': request.form.get('ip')
        }
        
        context = build_context(user.id, request, demo_override)
        risk_label, prob = predict_risk(context)
        
        log_event = LoginEvent(
            user_id=user.id,
            hour=context['hour'],
            device_hash=context['device_hash_val'],
            ip=context['ip_val'],
            failed_count=context['failed_count'],
            new_device=context['new_device'],
            new_ip=context['new_ip'],
            risk_label=risk_label,
            risk_prob=prob,
            outcome='pending'
        )
        db.session.add(log_event)
        db.session.commit()
        
        session['mfa_user_id'] = user.id
        session['login_event_id'] = log_event.id
        session['risk_label'] = risk_label
        
        if risk_label == 'HIGH':
            generate_email_otp(user.id)
            if current_app.config['DEMO_MODE']:
                flash('DEMO: High risk detected! Check the console for your Email OTP.', 'warning')
                
        return redirect(url_for('auth.mfa'))
        
    return render_template('login.html', demo_mode=current_app.config['DEMO_MODE'])

@auth_bp.route('/mfa', methods=['GET', 'POST'])
def mfa():
    user_id = session.get('mfa_user_id')
    event_id = session.get('login_event_id')
    risk_label = session.get('risk_label')
    
    if not user_id:
        return redirect(url_for('auth.login'))
        
    user = User.query.get(user_id)
    event = LoginEvent.query.get(event_id)
    
    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        email_code = request.form.get('email_code')
        
        # Always verify TOTP as the second factor
        if not verify_totp(user.totp_secret, totp_code):
            flash('Invalid TOTP code.', 'danger')
            return redirect(url_for('auth.mfa'))
            
        if risk_label == 'HIGH':
            if not verify_email_otp(user.id, email_code):
                flash('Invalid or expired Email OTP.', 'danger')
                return redirect(url_for('auth.mfa'))
                
        # Success
        record_successful_login(user)
        event.outcome = 'success'
        db.session.commit()
        
        session.pop('mfa_user_id')
        session['user_id'] = user.id
        
        # Dispatch official SMTP email
        send_real_email(user.email, "New Login Alert - SecureCloud", f"A successful login was detected on your account from IP {event.ip}.")
        flash(f'Login successful! A security alert email was officially sent to {user.email}.', 'success')
        return redirect(url_for('files.dashboard'))
        
    return render_template('mfa.html', risk=risk_label)
        
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))
