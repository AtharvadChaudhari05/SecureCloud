import os
import json
import pandas as pd
from flask import Blueprint, render_template, current_app

report_bp = Blueprint('report', __name__)

@report_bp.route('/report')
def show_report():
    reports_dir = os.path.join(os.path.dirname(current_app.root_path), 'ml', 'reports')
    
    risk_metrics = {}
    crypto_metrics = {}
    benchmark = {}
    model_comp = []
    
    risk_metrics_path = os.path.join(reports_dir, 'metrics.json')
    if os.path.exists(risk_metrics_path):
        with open(risk_metrics_path) as f:
            risk_metrics = json.load(f)
            
    crypto_metrics_path = os.path.join(reports_dir, 'crypto_metrics.json')
    if os.path.exists(crypto_metrics_path):
        with open(crypto_metrics_path) as f:
            crypto_metrics = json.load(f)
            
    bench_path = os.path.join(reports_dir, 'cipher_benchmark.json')
    if os.path.exists(bench_path):
        with open(bench_path) as f:
            benchmark = json.load(f)
            
    comp_path = os.path.join(reports_dir, 'model_comparison.csv')
    if os.path.exists(comp_path):
        df = pd.read_csv(comp_path)
        model_comp = df.to_dict('records')
        
    # Copy images to static so they can be served
    import shutil
    static_img = os.path.join(current_app.root_path, 'static', 'img')
    os.makedirs(static_img, exist_ok=True)
    for img in ['confusion_matrix.png', 'feature_importance.png', 'crypto_tree.png']:
        src = os.path.join(reports_dir, img)
        if os.path.exists(src):
            shutil.copy(src, static_img)
            
    return render_template(
        'report.html',
        risk_metrics=risk_metrics,
        crypto_metrics=crypto_metrics,
        benchmark=benchmark,
        model_comp=model_comp
    )
