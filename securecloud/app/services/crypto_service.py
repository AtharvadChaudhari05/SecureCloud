import os
import pandas as pd
from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
import app

def choose_cipher(sensitivity: int, session_risk: int, size_kb: int) -> int:
    if not app.crypto_policy_model:
        return 0 # Fallback
    
    features = pd.DataFrame([{
        'sensitivity': sensitivity,
        'session_risk': session_risk,
        'size_kb': size_kb
    }])
    
    return int(app.crypto_policy_model.predict(features)[0])

import base64

def get_master_key() -> bytes:
    env_key = os.environ.get('MASTER_KEY_B64')
    if env_key:
        return base64.b64decode(env_key)

    key_path = os.path.join(app.config.Config.STORAGE_FOLDER, 'master.key')
    if not os.path.exists(key_path):
        key = os.urandom(32)
        with open(key_path, 'wb') as f:
            f.write(key)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
    else:
        # Check permissions if not in demo
        if not os.environ.get('DEMO_MODE') and os.name != 'nt':
            st = os.stat(key_path)
            if st.st_mode & 0o077:
                raise PermissionError("master.key is world-readable! Aborting.")
        with open(key_path, 'rb') as f:
            key = f.read()
    return key

def encrypt_file_data(plaintext: bytes, cipher_class: int, aad: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    master_key = get_master_key()
    
    # 0 = AES-128-GCM, 1 = AES-256-GCM, 2 = ChaCha20-Poly1305
    if cipher_class == 0:
        file_key = os.urandom(16)
        cipher = AESGCM(file_key)
        algo_name = "AES-128-GCM"
    elif cipher_class == 1:
        file_key = os.urandom(32)
        cipher = AESGCM(file_key)
        algo_name = "AES-256-GCM"
    else:
        file_key = os.urandom(32)
        cipher = ChaCha20Poly1305(file_key)
        algo_name = "ChaCha20-Poly1305"
        
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, plaintext, None)
    
    # Wrap file key
    wrap_nonce = os.urandom(12)
    master_cipher = AESGCM(master_key)
    wrapped = master_cipher.encrypt(wrap_nonce, file_key, aad)
    
    wrapped_key_full = wrap_nonce + wrapped
    return ciphertext, nonce, wrapped_key_full, algo_name.encode()

def decrypt_file_data(ciphertext: bytes, nonce: bytes, wrapped_key_full: bytes, cipher_class_name: str, aad: bytes) -> bytes:
    master_key = get_master_key()
    master_cipher = AESGCM(master_key)
    
    wrap_nonce = wrapped_key_full[:12]
    wrapped = wrapped_key_full[12:]
    
    try:
        file_key = master_cipher.decrypt(wrap_nonce, wrapped, aad)
    except Exception as e:
        raise ValueError("Key unwrapping failed - possible tampering") from e
        
    if cipher_class_name == "AES-128-GCM" or cipher_class_name == "AES-256-GCM":
        cipher = AESGCM(file_key)
    else:
        cipher = ChaCha20Poly1305(file_key)
        
    try:
        plaintext = cipher.decrypt(nonce, ciphertext, None)
        return plaintext
    except Exception as e:
        raise ValueError("File decryption failed - possible tampering") from e
