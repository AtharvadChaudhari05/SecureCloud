import pandas as pd
import numpy as np
import os

def generate_crypto_data(num_rows=100000, output_path="ml/data/crypto_policy_data.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.random.seed(42)
    
    # Features: sensitivity (0/1/2), session_risk (0/1/2), size_kb (1-10240)
    sensitivity = np.random.choice([0, 1, 2], size=num_rows, p=[0.5, 0.3, 0.2])
    session_risk = np.random.choice([0, 1, 2], size=num_rows, p=[0.7, 0.2, 0.1])
    size_kb = np.random.randint(1, 10241, size=num_rows)
    
    df = pd.DataFrame({
        'sensitivity': sensitivity,
        'session_risk': session_risk,
        'size_kb': size_kb
    })
    
    # Target: 0 = AES-128-GCM, 1 = AES-256-GCM, 2 = ChaCha20-Poly1305
    def compute_policy(row):
        sens = row['sensitivity']
        risk = row['session_risk']
        size = row['size_kb']
        
        base = min((sens + risk + 1) // 2, 2)
        if size > 3000 and sens > 0:
            base = min(base + 1, 2)
            
        return base
        
    df['cipher_class'] = df.apply(compute_policy, axis=1)
    
    # Add 3% label noise
    noise_indices = np.random.choice(df.index, size=int(num_rows * 0.03), replace=False)
    for idx in noise_indices:
        current = df.loc[idx, 'cipher_class']
        choices = [c for c in [0, 1, 2] if c != current]
        df.loc[idx, 'cipher_class'] = np.random.choice(choices)
        
    print("Cipher Class Distribution:")
    print(df['cipher_class'].value_counts(normalize=True))
    
    df.to_csv(output_path, index=False)
    print(f"Generated {num_rows} rows at {output_path}")

if __name__ == "__main__":
    generate_crypto_data()
