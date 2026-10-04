# SecureCloud (Phase 1)

## Overview
Context-Aware Cloud Security file vault.
Implements:
- Registration & TOTP MFA.
- Login Risk ML engine to require Email OTP on high-risk logins.
- Adaptive Cryptography ML engine to select ciphers based on file sensitivity and session risk.

## Setup
1. Create venv: `python -m venv venv` and activate it.
2. Install reqs: `pip install -r requirements.txt`
3. Generate data and train ML: 
   - `python ml/generate_login_data.py`
   - `python ml/train_risk_model.py`
   - `python ml/generate_crypto_data.py`
   - `python ml/train_crypto_policy.py`
4. Seed demo user: `python seed_demo.py` (check console for TOTP secret).
5. Run: `python run.py`

## Testing
Run `pytest -q`

## Future Work (Phase 2)
- Admin dashboard + audit logs
- Key management and rotation (KMS)
- Real cloud storage (S3/Azure)
