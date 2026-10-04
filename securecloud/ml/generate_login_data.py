import pandas as pd
import numpy as np
import os

def generate_login_data(num_rows=100000, output_path="ml/data/login_data.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.random.seed(42)
    
    # Features: hour, day_of_week, new_device, new_ip, failed_count, minutes_since_last_login, login_velocity
    # Generate user types
    # 70% Normal, 20% Moderate, 10% Attack
    user_types = np.random.choice(['normal', 'moderate', 'attack'], size=num_rows, p=[0.7, 0.2, 0.1])
    
    hours = []
    days = []
    new_devices = []
    new_ips = []
    failed_counts = []
    mins_since_last = []
    velocities = []
    
    for utype in user_types:
        if utype == 'normal':
            hours.append(np.random.randint(7, 23))
            new_devices.append(np.random.choice([0, 1], p=[0.95, 0.05]))
            new_ips.append(np.random.choice([0, 1], p=[0.90, 0.10]))
            failed_counts.append(np.random.randint(0, 2))
            mins_since_last.append(np.random.randint(120, 10080))
            velocities.append(np.random.randint(0, 2))
        elif utype == 'moderate':
            hours.append(np.random.randint(0, 24))
            new_devices.append(np.random.choice([0, 1], p=[0.70, 0.30]))
            new_ips.append(np.random.choice([0, 1], p=[0.60, 0.40]))
            failed_counts.append(np.random.randint(1, 4))
            mins_since_last.append(np.random.randint(30, 1440))
            velocities.append(np.random.randint(1, 4))
        else: # attack
            hours.append(np.random.randint(0, 6))
            new_devices.append(np.random.choice([0, 1], p=[0.10, 0.90]))
            new_ips.append(np.random.choice([0, 1], p=[0.05, 0.95]))
            failed_counts.append(np.random.randint(3, 11))
            mins_since_last.append(np.random.randint(0, 30))
            velocities.append(np.random.randint(3, 11))
            
        days.append(np.random.randint(0, 7))

    df = pd.DataFrame({
        'hour': hours,
        'day_of_week': days,
        'new_device': new_devices,
        'new_ip': new_ips,
        'failed_count': failed_counts,
        'minutes_since_last_login': mins_since_last,
        'login_velocity': velocities
    })
    
    # Calculate hidden risk score
    # 2.0*new_device + 1.0*new_ip + 0.9*failed_count + 1.5*(night) + 0.4*(velocity>3) + 0.5*(minutes_since_last_login<2) + Gaussian noise(0, 0.5)
    is_night = ((df['hour'] >= 0) & (df['hour'] <= 5)).astype(int)
    is_high_velocity = (df['login_velocity'] > 3).astype(int)
    is_fast_login = (df['minutes_since_last_login'] < 2).astype(int)
    
    score = (2.0 * df['new_device'] + 
             1.0 * df['new_ip'] + 
             0.9 * df['failed_count'] + 
             1.5 * is_night + 
             0.4 * is_high_velocity + 
             0.5 * is_fast_login + 
             np.random.normal(0, 0.5, num_rows))
             
    # Label: <2 LOW (0), 2-4 MEDIUM (1), >4 HIGH (2)
    def assign_label(s):
        if s < 2: return 0
        elif s <= 4: return 1
        else: return 2
        
    df['risk_label'] = score.apply(assign_label)
    
    # Print label distribution
    print("Risk Label Distribution:")
    print(df['risk_label'].value_counts(normalize=True))
    
    df.to_csv(output_path, index=False)
    print(f"Generated {num_rows} rows at {output_path}")

if __name__ == "__main__":
    # Generate a bit more data to make it substantial but manageable for local dev
    generate_login_data(500000, "ml/data/login_data.csv")
