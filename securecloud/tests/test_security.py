import pytest
import os
from flask import session
from app.models import db, User, FileRecord, AccessEvent
from app.services.auth_service import hash_password
from app.services.crypto_service import get_master_key
import uuid

def test_passkey_login_removed(client):
    # Prove that passkey_login endpoint is removed (Issue 1 fix)
    response = client.post('/passkey_login')
    assert response.status_code == 404

def test_download_gate_enforcement(client, app):
    # Prove that download requires a server-side grant (Issue 2 fix)
    with app.app_context():
        user = User(username='testuser', email='test@test.com', password_hash='hash', totp_secret='secret')
        db.session.add(user)
        db.session.commit()
        
        file_id = 999
        record = FileRecord(
            id=file_id, owner_id=user.id, original_name='test.txt', stored_name='test.bin',
            size=10, sensitivity=0, session_risk=0, algo='AES', nonce=b'123', wrapped_key=b'123', sha256='hash'
        )
        db.session.add(record)
        db.session.commit()
        uid = user.id
        
    with client.session_transaction() as sess:
        sess['user_id'] = uid
        
    # Attempt to download without grant -> should redirect to dashboard
    resp = client.get(f'/download/{file_id}')
    assert resp.status_code == 302
    assert '/dashboard' in resp.headers['Location']

def test_master_key_not_world_readable(app, monkeypatch):
    # Prove master key permission check (Issue 3 fix)
    # We simulate a world-readable master.key
    with app.app_context():
        # Clean up any loaded key in env
        if 'MASTER_KEY_B64' in os.environ:
            del os.environ['MASTER_KEY_B64']
            
        key_path = os.path.join(app.config['STORAGE_FOLDER'], 'master.key')
        if not os.path.exists(key_path):
            with open(key_path, 'wb') as f:
                f.write(b'x'*32)
                
        # Fake os.name and DEMO_MODE to trigger check
        monkeypatch.setattr(os, 'name', 'posix')
        monkeypatch.delenv('DEMO_MODE', raising=False)
        
        # Mock os.stat to return world-readable mode
        class DummyStat:
            st_mode = 0o644 # World readable
        monkeypatch.setattr(os, 'stat', lambda path: DummyStat())
        
        with pytest.raises(PermissionError, match="master.key is world-readable"):
            get_master_key()
