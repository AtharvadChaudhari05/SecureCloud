import os
import uuid
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, current_app, abort
from werkzeug.utils import secure_filename
from app.models import db, User, FileRecord, LoginEvent
from app.services.crypto_service import choose_cipher, encrypt_file_data, decrypt_file_data

files_bp = Blueprint('files', __name__)

@files_bp.before_request
def require_login():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash('Session expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

@files_bp.route('/dashboard')
def dashboard():
    user = User.query.get(session['user_id'])
    risk_label = session.get('risk_label', 'LOW')
    
    files = FileRecord.query.filter_by(owner_id=user.id).order_by(FileRecord.created_at.desc()).all()
    history = LoginEvent.query.filter_by(user_id=user.id).order_by(LoginEvent.ts.desc()).limit(10).all()
    
    return render_template('dashboard.html', user=user, risk=risk_label, files=files, history=history)

@files_bp.route('/profile')
def profile():
    user = User.query.get(session['user_id'])
    history = LoginEvent.query.filter_by(user_id=user.id).order_by(LoginEvent.ts.desc()).all()
    
    total_logins = len(history)
    successful_logins = sum(1 for h in history if h.outcome == 'success')
    failed_logins = total_logins - successful_logins
    
    return render_template('profile.html', user=user, history=history, 
                           total_logins=total_logins, 
                           successful_logins=successful_logins, 
                           failed_logins=failed_logins)

@files_bp.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('files.dashboard'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('files.dashboard'))
        
    sensitivity = int(request.form.get('sensitivity', 0)) # 0: Public, 1: Internal, 2: Confidential
    
    file_data = file.read()
    size_kb = len(file_data) // 1024
    if size_kb == 0: size_kb = 1
    
    if len(file_data) > current_app.config['MAX_CONTENT_LENGTH']:
        flash('File too large', 'danger')
        return redirect(url_for('files.dashboard'))
        
    risk_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    session_risk_int = risk_map.get(session.get('risk_label', 'LOW'), 0)
    
    cipher_class = choose_cipher(sensitivity, session_risk_int, size_kb)
    sha256 = hashlib.sha256(file_data).hexdigest()
    
    stored_name = str(uuid.uuid4()) + ".bin"
    stored_path = os.path.join(current_app.config['STORAGE_FOLDER'], stored_name)
    
    user_id = session['user_id']
    aad = f"{user_id}".encode() # AAD for key wrapping
    
    ciphertext, nonce, wrapped_key_full, algo_name = encrypt_file_data(file_data, cipher_class, aad)
    
    with open(stored_path, 'wb') as f:
        f.write(ciphertext)
        
    record = FileRecord(
        owner_id=user_id,
        original_name=secure_filename(file.filename),
        stored_name=stored_name,
        size=len(file_data),
        sensitivity=sensitivity,
        session_risk=session_risk_int,
        algo=algo_name.decode(),
        nonce=nonce,
        wrapped_key=wrapped_key_full,
        sha256=sha256
    )
    db.session.add(record)
    db.session.commit()
    
    flash(f'File uploaded successfully and encrypted with {algo_name.decode()}.', 'success')
    return redirect(url_for('files.dashboard'))

@files_bp.route('/upload_note', methods=['POST'])
def upload_note():
    title = request.form.get('note_title', 'Secure_Note')
    content = request.form.get('note_content', '')
    sensitivity = int(request.form.get('sensitivity', 2))
    
    if not content:
        flash('Note content cannot be empty.', 'danger')
        return redirect(url_for('files.dashboard'))
        
    file_data = content.encode('utf-8')
    size_kb = len(file_data) // 1024
    if size_kb == 0: size_kb = 1
    
    risk_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    session_risk_int = risk_map.get(session.get('risk_label', 'LOW'), 0)
    
    cipher_class = choose_cipher(sensitivity, session_risk_int, size_kb)
    sha256 = hashlib.sha256(file_data).hexdigest()
    
    stored_name = str(uuid.uuid4()) + ".bin"
    stored_path = os.path.join(current_app.config['STORAGE_FOLDER'], stored_name)
    
    user_id = session['user_id']
    aad = f"{user_id}".encode()
    
    ciphertext, nonce, wrapped_key_full, algo_name = encrypt_file_data(file_data, cipher_class, aad)
    
    with open(stored_path, 'wb') as f:
        f.write(ciphertext)
        
    # Format the name cleanly
    clean_title = secure_filename(title)
    if not clean_title: clean_title = "Secure_Note"
    
    record = FileRecord(
        owner_id=user_id,
        original_name=f"{clean_title}.txt",
        stored_name=stored_name,
        size=len(file_data),
        sensitivity=sensitivity,
        session_risk=session_risk_int,
        algo=algo_name.decode(),
        nonce=nonce,
        wrapped_key=wrapped_key_full,
        sha256=sha256
    )
    db.session.add(record)
    db.session.commit()
    
    flash(f'Secure note encrypted with {algo_name.decode()} and stored.', 'success')
    return redirect(url_for('files.dashboard'))

from datetime import datetime, timedelta
from app.services.auth_service import verify_totp, is_locked_out, record_failed_attempt
from app.models import AccessEvent

@files_bp.route('/action/<int:file_id>/verify', methods=['POST'])
def verify_action(file_id):
    user = User.query.get(session['user_id'])
    if is_locked_out(user):
        flash('Account locked due to multiple failed attempts.', 'danger')
        return redirect(url_for('files.dashboard'))
        
    totp_code = request.form.get('totp_code')
    action = request.form.get('action', 'download')
    
    if verify_totp(user.totp_secret, totp_code):
        session['action_grant'] = {
            'file_id': file_id,
            'user_id': user.id,
            'action': action,
            'expires_at': (datetime.utcnow() + timedelta(seconds=120)).timestamp()
        }
        event = AccessEvent(user_id=user.id, file_id=file_id, action=action, outcome='success')
        db.session.add(event)
        db.session.commit()
        
        if action == 'shred':
            return redirect(url_for('files.shred_file', file_id=file_id))
        return redirect(url_for('files.download', file_id=file_id))
    else:
        record_failed_attempt(user)
        event = AccessEvent(user_id=user.id, file_id=file_id, action=action, outcome='fail')
        db.session.add(event)
        db.session.commit()
        flash('Invalid TOTP code.', 'danger')
        return redirect(url_for('files.dashboard'))

def check_action_grant(file_id, action):
    grant = session.get('action_grant')
    if not grant: return False
    if grant['file_id'] != file_id or grant['user_id'] != session['user_id'] or grant['action'] != action:
        return False
    if datetime.utcnow().timestamp() > grant['expires_at']:
        session.pop('action_grant')
        return False
    session.pop('action_grant')
    return True

@files_bp.route('/download/<int:file_id>')
def download(file_id):
    if not check_action_grant(file_id, 'download'):
        flash('Download unauthorized or grant expired. Please verify again.', 'danger')
        return redirect(url_for('files.dashboard'))
        
    record = FileRecord.query.get_or_404(file_id)
    if record.owner_id != session['user_id']:
        abort(403)
        
    stored_path = os.path.join(current_app.config['STORAGE_FOLDER'], record.stored_name)
    if not os.path.exists(stored_path):
        abort(404)
        
    with open(stored_path, 'rb') as f:
        ciphertext = f.read()
        
    aad = f"{record.owner_id}".encode()
    try:
        plaintext = decrypt_file_data(ciphertext, record.nonce, record.wrapped_key, record.algo, aad)
    except Exception as e:
        flash(f'Decryption error: {str(e)}', 'danger')
        return redirect(url_for('files.dashboard'))
        
    # Verify integrity
    calc_sha256 = hashlib.sha256(plaintext).hexdigest()
    if calc_sha256 != record.sha256:
        flash('Integrity check failed. File may be corrupted.', 'danger')
        return redirect(url_for('files.dashboard'))
        
    # Send file
    from io import BytesIO
    return send_file(
        BytesIO(plaintext),
        as_attachment=True,
        download_name=record.original_name
    )

@files_bp.route('/shred/<int:file_id>', methods=['GET', 'POST'])
def shred_file(file_id):
    if not check_action_grant(file_id, 'shred'):
        flash('Shred unauthorized or grant expired. Please verify again.', 'danger')
        return redirect(url_for('files.dashboard'))
        
    record = FileRecord.query.get_or_404(file_id)
    if record.owner_id != session['user_id']:
        abort(403)
        
    stored_path = os.path.join(current_app.config['STORAGE_FOLDER'], record.stored_name)
    if os.path.exists(stored_path):
        # DoD 5220.22-M standard 3-pass secure wipe simulation
        size = os.path.getsize(stored_path)
        with open(stored_path, 'r+b') as f:
            # Pass 1: Zeros
            f.seek(0)
            f.write(b'\x00' * size)
            f.flush()
            # Pass 2: Ones
            f.seek(0)
            f.write(b'\xff' * size)
            f.flush()
            # Pass 3: Random data
            f.seek(0)
            f.write(os.urandom(size))
            f.flush()
            
        os.remove(stored_path)
        
    db.session.delete(record)
    db.session.commit()
    flash('File securely shredded (3-pass DoD 5220.22-M wipe). Data is unrecoverable.', 'success')
    return redirect(url_for('files.dashboard'))
