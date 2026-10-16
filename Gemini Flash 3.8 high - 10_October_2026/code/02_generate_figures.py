"""
02_generate_figures.py
Generates publication-quality figures for FHB predictive modeling results.
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve, roc_auc_score

def main():
    os.makedirs('figures', exist_ok=True)
    
    df = pd.read_parquet('FHBVer2.parquet')
    df['epidemic'] = (df['S'] >= 10.0).astype(int)
    
    # We will load loyo predictions from running 01_fit_models
    # Let's re-run a fast calculation or compute predictions
    import statsmodels.formula.api as smf
    from sklearn.ensemble import RandomForestClassifier
    
    clean_df = df.copy()
    clean_df['RH_A_PRE7_12H'] = df['RH.A.PRE7.12H']
    clean_df['T_9T30_PRE7_24H'] = df['T.9T30.PRE7.24H']
    clean_df['TRH_9T30nRHG80_PRE7_24H'] = df['TRH.9T30nRHG80.PRE7.24H']
    
    years = sorted(clean_df['year'].unique())
    
    models = {
        'M1 (Overnight RH)': 'epidemic ~ RH_A_PRE7_12H',
        'M2 (Overnight RH + Temp)': 'epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H',
        'M3 (Interaction RH x Temp)': 'epidemic ~ RH_A_PRE7_12H * T_9T30_PRE7_24H',
        'M4 (Joint TRH)': 'epidemic ~ TRH_9T30nRHG80_PRE7_24H',
        'M5 (Weather + Host Resist)': 'epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H + C(resist, Treatment(reference="VS"))'
    }
    
    preds_dict = {m: np.zeros(len(clean_df)) for m in models}
    rf_preds = np.zeros(len(clean_df))
    
    for yr in years:
        tr_idx = clean_df['year'] != yr
        te_idx = clean_df['year'] == yr
        if clean_df.loc[tr_idx, 'epidemic'].nunique() < 2:
            continue
        tr_data = clean_df[tr_idx]
        te_data = clean_df[te_idx]
        
        for m_name, formula in models.items():
            mod = smf.logit(formula, data=tr_data).fit(disp=False)
            preds_dict[m_name][te_idx] = mod.predict(te_data)
            
        rf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
        rf.fit(tr_data[['RH_A_PRE7_12H', 'T_9T30_PRE7_24H']], tr_data['epidemic'])
        rf_preds[te_idx] = rf.predict_proba(te_data[['RH_A_PRE7_12H', 'T_9T30_PRE7_24H']])[:, 1]
        
    preds_dict['M6 (Random Forest)'] = rf_preds
    
    # 1. Figure 1: ROC Curves (LOYO-CV)
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    
    colors = {
        'M1 (Overnight RH)': '#4A90E2',
        'M2 (Overnight RH + Temp)': '#2C3E50',
        'M3 (Interaction RH x Temp)': '#E67E22',
        'M4 (Joint TRH)': '#95A5A6',
        'M5 (Weather + Host Resist)': '#27AE60',
        'M6 (Random Forest)': '#E74C3C'
    }
    linewidths = {
        'M1 (Overnight RH)': 1.8,
        'M2 (Overnight RH + Temp)': 2.5,
        'M3 (Interaction RH x Temp)': 1.8,
        'M4 (Joint TRH)': 1.5,
        'M5 (Weather + Host Resist)': 2.5,
        'M6 (Random Forest)': 1.5
    }
    linestyles = {
        'M1 (Overnight RH)': '--',
        'M2 (Overnight RH + Temp)': '-',
        'M3 (Interaction RH x Temp)': ':',
        'M4 (Joint TRH)': '-.',
        'M5 (Weather + Host Resist)': '-',
        'M6 (Random Forest)': '--'
    }
    
    y_true = clean_df['epidemic']
    for m_name, p in preds_dict.items():
        fpr, tpr, _ = roc_curve(y_true, p)
        auc = roc_auc_score(y_true, p)
        ax.plot(fpr, tpr, label=f"{m_name} (AUC = {auc:.3f})",
                color=colors[m_name], linewidth=linewidths[m_name], linestyle=linestyles[m_name])
        
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.5, label='Random Chance (AUC = 0.500)')
    ax.set_xlabel('1 - Specificity (False Positive Rate)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Sensitivity (True Positive Rate)', fontsize=12, fontweight='bold')
    ax.set_title('Leave-One-Year-Out Cross-Validation ROC Curves\nFHB Epidemic Risk Prediction (Pre-Anthesis)', fontsize=14, fontweight='bold', pad=12)
    ax.legend(loc='lower right', frameon=True, fontsize=10)
    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    plt.tight_layout()
    plt.savefig('figures/roc_curves.png', dpi=300)
    plt.close()
    print("Saved figures/roc_curves.png")

    # 2. Figure 2: Calibration Plot (M2 vs M5)
    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    
    for m_key, m_col, m_lbl in [('M2 (Overnight RH + Temp)', '#2C3E50', 'M2: Weather (RH + Temp)'),
                                ('M5 (Weather + Host Resist)', '#27AE60', 'M5: Weather + Cultivar Resistance')]:
        clean_df['prob'] = preds_dict[m_key]
        clean_df['bin'] = pd.qcut(clean_df['prob'], q=10, duplicates='drop')
        agg = clean_df.groupby('bin', observed=True).agg({'prob': 'mean', 'epidemic': ['mean', 'count']})
        pred_m = agg[('prob', 'mean')]
        obs_m = agg[('epidemic', 'mean')]
        cnt = agg[('epidemic', 'count')]
        
        ax.plot(pred_m, obs_m, marker='o', markersize=8, linewidth=2, color=m_col, label=m_lbl)
        
    ax.plot([0, 0.7], [0, 0.7], 'k--', alpha=0.6, label='Perfect Calibration (1:1 Line)')
    ax.set_xlabel('Mean Predicted Probability', fontsize=12, fontweight='bold')
    ax.set_ylabel('Observed Epidemic Proportion', fontsize=12, fontweight='bold')
    ax.set_title('Out-of-Fold Calibration (Deciles of Predicted Risk)\nLeave-One-Year-Out Cross-Validation', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlim([0, 0.7])
    ax.set_ylim([0, 0.7])
    ax.legend(loc='upper left', frameon=True, fontsize=11)
    plt.tight_layout()
    plt.savefig('figures/calibration_plot.png', dpi=300)
    plt.close()
    print("Saved figures/calibration_plot.png")

    # 3. Figure 3: Annual Performance Variation (2000-2015)
    with open('model_results_output.json', 'r') as f:
        res_json = json.load(f)
    ann_data = res_json['annual_breakdown_m2']
    ann_df = pd.DataFrame(ann_data)
    ann_df = ann_df[ann_df['year'] >= 2000]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, dpi=300)
    
    # Plot AUC
    valid_auc = ann_df.dropna(subset=['auc'])
    ax1.plot(valid_auc['year'], valid_auc['auc'], marker='s', color='#2C3E50', linewidth=2, markersize=7, label='Annual Out-of-Fold AUC')
    ax1.axhline(0.6557, color='#E74C3C', linestyle='--', label='Overall Pooled AUC (0.656)')
    ax1.axhline(0.5, color='gray', linestyle=':', label='Chance (0.50)')
    ax1.set_ylabel('Annual ROC AUC', fontsize=11, fontweight='bold')
    ax1.set_ylim([0.2, 1.0])
    ax1.legend(loc='lower left', frameon=True, fontsize=10)
    ax1.set_title('Temporal Stability of M2 Weather Model Across Seasons (2000–2015)', fontsize=13, fontweight='bold')
    
    # Plot Brier Score & Prevalence
    ax2.bar(ann_df['year'] - 0.2, ann_df['prevalence'], width=0.4, color='#3498DB', alpha=0.7, label='Observed Epidemic Prevalence')
    ax2.bar(ann_df['year'] + 0.2, ann_df['brier'], width=0.4, color='#E67E22', alpha=0.8, label='Out-of-Fold Brier Score')
    ax2.set_xlabel('Harvest Year', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Prevalence / Brier Score', fontsize=11, fontweight='bold')
    ax2.set_xticks(ann_df['year'])
    ax2.set_xticklabels(ann_df['year'], rotation=45)
    ax2.legend(loc='upper right', frameon=True, fontsize=10)
    
    plt.tight_layout()
    plt.savefig('figures/annual_performance.png', dpi=300)
    plt.close()
    print("Saved figures/annual_performance.png")

if __name__ == '__main__':
    main()
