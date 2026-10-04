import pandas as pd
from datetime import datetime, timedelta
from app.models import LoginEvent
import app

def build_context(user_id: int, request, demo_override: dict = None) -> dict:
    now = datetime.utcnow()
    hour = now.hour
    day_of_week = now.weekday()
    
    device_hash = str(hash(request.headers.get('User-Agent', '')))
    ip = request.remote_addr
    
    if demo_override and demo_override.get('active'):
        hour = int(demo_override.get('hour', hour))
        device_hash = demo_override.get('device_hash', device_hash)
        ip = demo_override.get('ip', ip)
        
    # Query past logins for this user
    past_15m = now - timedelta(minutes=15)
    failed_count = LoginEvent.query.filter(
        LoginEvent.user_id == user_id,
        LoginEvent.outcome == 'fail',
        LoginEvent.ts >= past_15m
    ).count()
    
    # Check if new device or IP
    prev_device = LoginEvent.query.filter_by(user_id=user_id, device_hash=device_hash, outcome='success').first()
    new_device = 0 if prev_device else 1
    
    prev_ip = LoginEvent.query.filter_by(user_id=user_id, ip=ip, outcome='success').first()
    new_ip = 0 if prev_ip else 1
    
    last_login = LoginEvent.query.filter_by(user_id=user_id, outcome='success').order_by(LoginEvent.ts.desc()).first()
    if last_login:
        mins_since = int((now - last_login.ts).total_seconds() / 60)
    else:
        mins_since = 10080 # default to 1 week if no prior login
        
    past_1h = now - timedelta(hours=1)
    velocity = LoginEvent.query.filter(LoginEvent.user_id == user_id, LoginEvent.ts >= past_1h).count()
    
    return {
        'hour': hour,
        'day_of_week': day_of_week,
        'new_device': new_device,
        'new_ip': new_ip,
        'failed_count': failed_count,
        'minutes_since_last_login': mins_since,
        'login_velocity': velocity,
        'device_hash_val': device_hash,
        'ip_val': ip
    }

def predict_risk(context: dict) -> tuple[str, float]:
    if not app.risk_model:
        # Fallback if model not loaded
        return 'LOW', 1.0
        
    features = pd.DataFrame([{
        'hour': context['hour'],
        'day_of_week': context['day_of_week'],
        'new_device': context['new_device'],
        'new_ip': context['new_ip'],
        'failed_count': context['failed_count'],
        'minutes_since_last_login': context['minutes_since_last_login'],
        'login_velocity': context['login_velocity']
    }])
    
    probs = app.risk_model.predict_proba(features)[0]
    label_idx = probs.argmax()
    
    labels = {0: 'LOW', 1: 'MEDIUM', 2: 'HIGH'}
    return labels[label_idx], probs[label_idx]
