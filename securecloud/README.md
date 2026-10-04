# SecureCloud: Context-Aware Security Vault (Phase 1)

SecureCloud is a high-security, context-aware file vault built with Python, Flask, and Machine Learning. It provides intelligent, adaptive security boundaries that dynamically adjust based on user behavior, session risk, and data sensitivity. 

This repository represents the **Phase 1 Implementation**, which is fully functional, strictly tested, and securely handles file cryptography and zero-trust authentication.

---

## 🏗️ System Architecture (Phase 1)

The system is built on a modular architecture separating the web layer, machine learning engines, and cryptographic services.

### 1. Core Stack
* **Backend:** Python / Flask
* **Database:** SQLite (managed via SQLAlchemy ORM)
* **Frontend:** Jinja2 Templates, Bootstrap 5, custom CSS (MagicUI/Aceternity inspired aesthetics with dynamic animations)
* **Machine Learning:** Scikit-Learn (`RandomForestClassifier`)

### 2. Intelligent Engines
* **Context-Aware Risk Engine:** An ML model evaluates every login attempt. It analyzes the time of day, IP address familiarity, device hash, failed attempt counts, and login velocity. It outputs a risk score (LOW, MEDIUM, HIGH) which dictates the strictness of the login flow.
* **Adaptive Cryptography Policy Engine:** An ML model determines the optimal encryption cipher for file uploads. It balances security and performance by evaluating the file's defined sensitivity (Public, Internal, Confidential), file size, and the user's current session risk.

### 3. Cryptographic & Security Layer
* **Envelope Encryption:** The system uses a centralized `master.key` (loaded via environment variables or securely generated on disk with strict `0o600` permissions). Every file gets a unique Data Encryption Key (DEK) which is then wrapped by the master key.
* **Supported Ciphers:** AES-256-GCM, ChaCha20-Poly1305, and XChaCha20-Poly1305.
* **Zero-Trust Download Gate:** Sensitive actions require real-time reverification of identity, protecting against session hijacking.
* **Secure Shredding:** Implements a simulated 3-pass DoD 5220.22-M secure wipe (Overwrite with Zeros -> Ones -> Random) before deletion.

---

## 🔄 User Workflow Architecture

### 1. Registration & Setup Workflow
1. User creates an account with a Username and Password.
2. The system generates a unique TOTP secret and displays a QR code.
3. User scans the QR code with an Authenticator App (e.g., Google Authenticator) and enters the generated code to verify setup.
4. An automated welcome email is dispatched.

### 2. Adaptive Login Workflow
1. User enters Username and Password.
2. If credentials match, the **Risk Engine ML Model** analyzes the context (IP, Device, Time, History).
3. **MFA Challenge Generation:**
   * **LOW / MEDIUM Risk:** User is prompted for their TOTP Code.
   * **HIGH Risk:** User is prompted for their TOTP Code **AND** a 6-digit Email OTP (sent to their registered email).
4. Upon successful MFA verification, a secure session is established and an alert email is dispatched indicating a new login.

### 3. Secure File Upload Workflow
1. User selects a file and declares its data sensitivity (Public, Internal, Confidential).
2. The **Adaptive Crypto ML Model** evaluates the request and selects the optimal cipher.
3. A unique DEK (Data Encryption Key) is generated.
4. The file is encrypted in memory, the DEK is wrapped by the Master Key, and the ciphertext is flushed to the `storage/` directory as a `.bin` blob.
5. Metadata, Nonce, Wrapped Key, and a SHA-256 integrity hash are stored in the database.

### 4. Zero-Trust File Access Workflow (Download/Shred)
1. User requests to Download or Shred a file from the Dashboard.
2. The **Zero-Trust Gate** intercepts the request and opens a verification modal.
3. User must provide their current, live TOTP code.
4. The server validates the code and issues a strict, **120-second session grant** specifically tied to that exact file ID and action.
5. The system safely redirects the user to the underlying route to decrypt/download or securely shred the file.

---

## 🚀 Setup & Execution

### 1. Environment Setup
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Generate Data & Train ML Models
The machine learning models require synthetic data to learn patterns.
```bash
python ml/generate_login_data.py
python ml/train_risk_model.py
python ml/generate_crypto_data.py
python ml/train_crypto_policy.py
```

### 3. Initialize Demo Environment
This will generate the required `master.key`, initialize the SQLite database, create a `demo` user, and generate sample encrypted files.
```bash
python seed_demo.py
```
*(Keep an eye on the console output for the demo user's TOTP secret if you need to add it to your authenticator app!)*

### 4. Run the Application
```bash
python run.py
```
Access the system at `http://127.0.0.1:5000`

---

## 🧪 Testing
The system includes automated `pytest` suites verifying UI routes and critical security constraints (e.g., download gate enforcement, passkey bypass mitigation, and master key file permission enforcement).

Run tests:
```bash
pytest -q tests/
```

---

## 🔮 Future Work (Phase 2)
* Transition from SQLite to PostgreSQL.
* Transition from local disk storage to real Cloud Storage (AWS S3 / Azure Blob).
* Implement real FIDO2 / WebAuthn Hardware Passkeys (currently stubbed).
* Admin Dashboard & Immutable Audit Logs.
* Cloud Key Management System (KMS) Integration for Master Key rotation.
