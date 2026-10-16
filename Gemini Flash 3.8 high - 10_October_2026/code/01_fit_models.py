"""
01_fit_models.py
Autonomous Epidemiological Analysis Benchmark — FHB Prediction
Fits primary logistic regression models, conducts Leave-One-Year-Out Cross-Validation (LOYO-CV),
computes discrimination, calibration, and sensitivity analyses.
"""

import os
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.metrics import roc_auc_score, brier_score_loss, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from scipy import stats

def delong_roc_variance(ground_truth, predictions):
    """
    Computes DeLong's variance for ROC AUC.
    """
    order = np.argsort(-predictions)
    ground_truth = ground_truth[order]
    predictions = predictions[order]
    
    n_pos = np.sum(ground_truth == 1)
    n_neg = np.sum(ground_truth == 0)
    if n_pos == 0 or n_neg == 0:
        return np.nan
        
    pos_preds = predictions[ground_truth == 1]
    neg_preds = predictions[ground_truth == 0]
    
    # Structural components
    v10 = np.array([np.mean(p > neg_preds) + 0.5 * np.mean(p == neg_preds) for p in pos_preds])
    v01 = np.array([np.mean(pos_preds > n) + 0.5 * np.mean(pos_preds == n) for n in neg_preds])
    
    var = (np.var(v10, ddof=1) / n_pos) + (np.var(v01, ddof=1) / n_neg)
    return var

def evaluate_predictions(y_true, y_prob, cutoff=0.30):
    auc = roc_auc_score(y_true, y_prob)
    var = delong_roc_variance(np.array(y_true), np.array(y_prob))
    se = np.sqrt(var) if not np.isnan(var) else np.nan
    ci_lower = max(0.0, auc - 1.96 * se) if not np.isnan(se) else np.nan
    ci_upper = min(1.0, auc + 1.96 * se) if not np.isnan(se) else np.nan
    
    bs = brier_score_loss(y_true, y_prob)
    p_ref = np.mean(y_true)
    bs_ref = brier_score_loss(y_true, np.full_like(y_true, p_ref, dtype=float))
    bss = 1.0 - (bs / bs_ref) if bs_ref > 0 else 0.0
    
    # Calibration intercept and slope via logistic recalibration
    eps = 1e-6
    probs_clipped = np.clip(y_prob, eps, 1 - eps)
    logits = np.log(probs_clipped / (1 - probs_clipped))
    
    try:
        # Intercept (with slope fixed to 1): offset = logits
        # logit(y) = a + logits
        cal_int_mod = sm.GLM(y_true, np.ones(len(y_true)), family=sm.families.Binomial(), offset=logits).fit()
        cal_int = cal_int_mod.params[0]
        cal_int_se = cal_int_mod.bse[0]
    except Exception:
        cal_int, cal_int_se = np.nan, np.nan
        
    try:
        # Slope and intercept: logit(y) = a + b * logits
        cal_mod = sm.Logit(y_true, sm.add_constant(logits)).fit(disp=False)
        cal_slope = cal_mod.params[1]
        cal_slope_se = cal_mod.bse[1]
    except Exception:
        cal_slope, cal_slope_se = np.nan, np.nan
        
    # Classification at cutoff
    y_pred = (y_prob >= cutoff).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) > 0 else np.nan
    spec = tn / (tn + fp) if (tn + fp) > 0 else np.nan
    ppv = tp / (tp + fp) if (tp + fp) > 0 else np.nan
    npv = tn / (tn + fn) if (tn + fn) > 0 else np.nan
    acc = (tp + tn) / len(y_true)
    
    return {
        'auc': auc,
        'auc_se': se,
        'auc_ci_lower': ci_lower,
        'auc_ci_upper': ci_upper,
        'brier': bs,
        'brier_ref': bs_ref,
        'bss': bss,
        'cal_intercept': cal_int,
        'cal_intercept_se': cal_int_se,
        'cal_slope': cal_slope,
        'cal_slope_se': cal_slope_se,
        'cutoff': cutoff,
        'sensitivity': sens,
        'specificity': spec,
        'ppv': ppv,
        'npv': npv,
        'accuracy': acc,
        'confusion': {'tn': int(tn), 'fp': int(fp), 'fn': int(fn), 'tp': int(tp)}
    }

def main():
    print("Loading FHBVer2.parquet...")
    data_path = 'FHBVer2.parquet'
    df = pd.read_parquet(data_path)
    
    # Primary binary epidemic target: S >= 10.0%
    df['epidemic'] = (df['S'] >= 10.0).astype(int)
    df['env_id'] = df['year'].astype(str) + '_' + df['state'].astype(str) + '_' + df['fdate'].astype(str)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Epidemic prevalence: {df['epidemic'].mean():.4f} ({df['epidemic'].sum()}/{len(df)})")
    
    # Define models
    model_defs = {
        'M1_Baseline_RH': {
            'name': 'M1: Baseline Overnight RH (1 Weather Term)',
            'formula': 'epidemic ~ RH_A_PRE7_12H',
            'vars': ['RH.A.PRE7.12H'],
            'clean_vars': ['RH_A_PRE7_12H'],
            'n_weather_params': 1,
            'n_total_params': 2
        },
        'M2_Bivariable_RHT': {
            'name': 'M2: Overnight RH + Conducive Temp (2 Weather Terms)',
            'formula': 'epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H',
            'vars': ['RH.A.PRE7.12H', 'T.9T30.PRE7.24H'],
            'clean_vars': ['RH_A_PRE7_12H', 'T_9T30_PRE7_24H'],
            'n_weather_params': 2,
            'n_total_params': 3
        },
        'M3_Interaction_RHT': {
            'name': 'M3: Moisture x Thermal Interaction (3 Weather Terms)',
            'formula': 'epidemic ~ RH_A_PRE7_12H * T_9T30_PRE7_24H',
            'vars': ['RH.A.PRE7.12H', 'T.9T30.PRE7.24H'],
            'clean_vars': ['RH_A_PRE7_12H', 'T_9T30_PRE7_24H'],
            'n_weather_params': 3,
            'n_total_params': 4
        },
        'M4_Joint_TRH': {
            'name': 'M4: Single Joint Conduciveness Metric (1 Weather Term)',
            'formula': 'epidemic ~ TRH_9T30nRHG80_PRE7_24H',
            'vars': ['TRH.9T30nRHG80.PRE7.24H'],
            'clean_vars': ['TRH_9T30nRHG80_PRE7_24H'],
            'n_weather_params': 1,
            'n_total_params': 2
        },
        'M5_Weather_Resistance': {
            'name': 'M5: Weather (RH+T) + Host Resistance (2 Weather + 3 Host Terms)',
            'formula': 'epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H + C(resist, Treatment(reference="VS"))',
            'vars': ['RH.A.PRE7.12H', 'T.9T30.PRE7.24H', 'resist'],
            'clean_vars': ['RH_A_PRE7_12H', 'T_9T30_PRE7_24H', 'resist'],
            'n_weather_params': 2,
            'n_total_params': 6
        }
    }
    
    # Clean variable names for statsmodels formula
    clean_df = df.copy()
    clean_df['RH_A_PRE7_12H'] = df['RH.A.PRE7.12H']
    clean_df['T_9T30_PRE7_24H'] = df['T.9T30.PRE7.24H']
    clean_df['TRH_9T30nRHG80_PRE7_24H'] = df['TRH.9T30nRHG80.PRE7.24H']
    
    # 1. Fit models on Full Dataset (In-sample inference with cluster-robust SEs)
    print("\n================== FULL DATASET MODEL FITS ==================", flush=True)
    full_fit_results = {}
    for m_key, m_info in model_defs.items():
        print(f"\nFitting {m_info['name']}...", flush=True)
        model = smf.logit(m_info['formula'], data=clean_df)
        res_std = model.fit(disp=False)
        res_robust = model.fit(cov_type='cluster', cov_kwds={'groups': clean_df['env_id']}, disp=False)
        
        # Predict on full data
        preds = res_std.predict(clean_df)
        in_eval = evaluate_predictions(clean_df['epidemic'], preds)
        
        # Collect parameters
        param_table = []
        for p_name in res_std.params.index:
            coef = res_std.params[p_name]
            se_std = res_std.bse[p_name]
            se_rob = res_robust.bse[p_name]
            pval_rob = res_robust.pvalues[p_name]
            or_val = np.exp(coef)
            ci_low = np.exp(coef - 1.96 * se_rob)
            ci_high = np.exp(coef + 1.96 * se_rob)
            param_table.append({
                'term': p_name,
                'coef': coef,
                'se_model': se_std,
                'se_cluster': se_rob,
                'p_value_cluster': pval_rob,
                'odds_ratio': or_val,
                'or_ci_95': [ci_low, ci_high]
            })
            
        full_fit_results[m_key] = {
            'info': m_info,
            'aic': res_std.aic,
            'bic': res_std.bic,
            'log_likelihood': res_std.llf,
            'pseudo_r2': res_std.prsquared,
            'params': param_table,
            'in_sample_eval': in_eval
        }
        print(f"AIC: {res_std.aic:.2f}, BIC: {res_std.bic:.2f}, In-sample AUC: {in_eval['auc']:.4f}", flush=True)
        for p in param_table:
            print(f"  {p['term']}: beta={p['coef']:.4f} (SE_rob={p['se_cluster']:.4f}, p={p['p_value_cluster']:.4e}), OR={p['odds_ratio']:.3f} [{p['or_ci_95'][0]:.3f}, {p['or_ci_95'][1]:.3f}]", flush=True)
            
    # 2. Leave-One-Year-Out Cross-Validation (LOYO-CV)
    print("\n================== LEAVE-ONE-YEAR-OUT CV ==================")
    years = sorted(clean_df['year'].unique())
    print(f"Total validation years: {len(years)} ({min(years)} to {max(years)})")
    
    loyo_preds = {m_key: np.zeros(len(clean_df)) for m_key in model_defs.keys()}
    loyo_preds['M6_RandomForest_Benchmark'] = np.zeros(len(clean_df))
    
    # Store annual results
    annual_results = {m_key: [] for m_key in model_defs.keys()}
    annual_results['M6_RandomForest_Benchmark'] = []
    
    for yr in years:
        train_idx = clean_df['year'] != yr
        test_idx = clean_df['year'] == yr
        
        train_df = clean_df[train_idx]
        test_df = clean_df[test_idx]
        
        # Check if train has both classes
        if train_df['epidemic'].nunique() < 2:
            print(f"Warning: Year {yr} train set has only one class! Skipping.")
            continue
            
        # Fit each logistic model
        for m_key, m_info in model_defs.items():
            mod = smf.logit(m_info['formula'], data=train_df)
            res_fold = mod.fit(disp=False)
            preds_fold = res_fold.predict(test_df)
            loyo_preds[m_key][test_idx] = preds_fold
            
            # Annual metrics if test fold has both classes
            n_ev = test_df['epidemic'].sum()
            n_tot = len(test_df)
            if n_ev > 0 and n_ev < n_tot:
                yr_auc = roc_auc_score(test_df['epidemic'], preds_fold)
            else:
                yr_auc = np.nan
            yr_bs = brier_score_loss(test_df['epidemic'], preds_fold)
            annual_results[m_key].append({
                'year': int(yr),
                'n_plots': int(n_tot),
                'n_events': int(n_ev),
                'prevalence': float(n_ev / n_tot),
                'auc': float(yr_auc) if not np.isnan(yr_auc) else None,
                'brier': float(yr_bs)
            })
            
        # Benchmark M6: Random Forest on weather features
        rf_features = ['RH_A_PRE7_12H', 'T_9T30_PRE7_24H']
        rf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
        rf.fit(train_df[rf_features], train_df['epidemic'])
        rf_preds = rf.predict_proba(test_df[rf_features])[:, 1]
        loyo_preds['M6_RandomForest_Benchmark'][test_idx] = rf_preds
        
        n_ev = test_df['epidemic'].sum()
        n_tot = len(test_df)
        yr_auc = roc_auc_score(test_df['epidemic'], rf_preds) if (n_ev > 0 and n_ev < n_tot) else np.nan
        yr_bs = brier_score_loss(test_df['epidemic'], rf_preds)
        annual_results['M6_RandomForest_Benchmark'].append({
            'year': int(yr),
            'n_plots': int(n_tot),
            'n_events': int(n_ev),
            'prevalence': float(n_ev / n_tot),
            'auc': float(yr_auc) if not np.isnan(yr_auc) else None,
            'brier': float(yr_bs)
        })

    # Overall LOYO-CV Evaluation
    print("\n=== OVERALL LOYO-CV VALIDATION PERFORMANCE ===")
    cv_eval_summary = {}
    for m_key in list(model_defs.keys()) + ['M6_RandomForest_Benchmark']:
        eval_metrics = evaluate_predictions(clean_df['epidemic'], loyo_preds[m_key])
        
        # Summarize annual AUCs where both classes present
        valid_ann_aucs = [a['auc'] for a in annual_results[m_key] if a['auc'] is not None and not np.isnan(a['auc'])]
        valid_ann_bs = [a['brier'] for a in annual_results[m_key]]
        
        cv_eval_summary[m_key] = {
            'metrics': eval_metrics,
            'annual_auc_mean': float(np.mean(valid_ann_aucs)) if valid_ann_aucs else np.nan,
            'annual_auc_median': float(np.median(valid_ann_aucs)) if valid_ann_aucs else np.nan,
            'annual_auc_iqr': [float(np.percentile(valid_ann_aucs, 25)), float(np.percentile(valid_ann_aucs, 75))] if valid_ann_aucs else [],
            'annual_brier_mean': float(np.mean(valid_ann_bs)),
            'annual_brier_median': float(np.median(valid_ann_bs))
        }
        print(f"\n{m_key}:")
        print(f"  LOYO-CV AUC: {eval_metrics['auc']:.4f} (95% CI: [{eval_metrics['auc_ci_lower']:.4f}, {eval_metrics['auc_ci_upper']:.4f}])")
        print(f"  Brier Score: {eval_metrics['brier']:.4f} (BSS: {eval_metrics['bss']:.4f})")
        print(f"  Calibration Intercept: {eval_metrics['cal_intercept']:.4f} (SE={eval_metrics['cal_intercept_se']:.4f})")
        print(f"  Calibration Slope:     {eval_metrics['cal_slope']:.4f} (SE={eval_metrics['cal_slope_se']:.4f})")
        print(f"  At cutoff 0.30: Sens={eval_metrics['sensitivity']:.3f}, Spec={eval_metrics['specificity']:.3f}, PPV={eval_metrics['ppv']:.3f}, NPV={eval_metrics['npv']:.3f}")
        print(f"  Annual AUC (mean/median): {cv_eval_summary[m_key]['annual_auc_mean']:.3f} / {cv_eval_summary[m_key]['annual_auc_median']:.3f}")

    # 3. Decile Calibration Table
    print("\n=== CALIBRATION DECILES FOR M2 (PRIMARY MODEL) ===")
    m2_probs = loyo_preds['M2_Bivariable_RHT']
    clean_df['m2_pred'] = m2_probs
    clean_df['prob_bin'] = pd.qcut(clean_df['m2_pred'], q=10, duplicates='drop')
    cal_table = clean_df.groupby('prob_bin', observed=True).agg({
        'm2_pred': ['count', 'mean'],
        'epidemic': ['sum', 'mean']
    }).reset_index()
    cal_table.columns = ['prob_bin', 'N', 'pred_mean', 'events', 'obs_prop']
    print(cal_table.to_string())

    # 4. Sensitivity Analyses
    print("\n================== SENSITIVITY ANALYSES ==================")
    
    # 4.1 Window Sensitivity: 7d vs 10d vs 14d
    print("\n--- 4.1 Exposure Window Sensitivity (7d vs 10d vs 14d) ---")
    window_results = {}
    windows = {
        '7-day': {'rh': 'RH.A.PRE7.12H', 't': 'T.9T30.PRE7.24H'},
        '10-day': {'rh': 'RH.A.PRE10.12H', 't': 'T.9T30.PRE10.24H'},
        '14-day': {'rh': 'RH.A.PRE14.12H', 't': 'T.9T30.PRE14.24H'}
    }
    
    for w_name, w_vars in windows.items():
        w_df = clean_df.copy()
        w_df['rh_term'] = df[w_vars['rh']]
        w_df['t_term'] = df[w_vars['t']]
        
        # LOYO-CV
        w_preds = np.zeros(len(w_df))
        for yr in years:
            train_idx = w_df['year'] != yr
            test_idx = w_df['year'] == yr
            if w_df.loc[train_idx, 'epidemic'].nunique() < 2:
                continue
            m = smf.logit('epidemic ~ rh_term + t_term', data=w_df[train_idx]).fit(disp=False)
            w_preds[test_idx] = m.predict(w_df[test_idx])
            
        w_eval = evaluate_predictions(w_df['epidemic'], w_preds)
        window_results[w_name] = w_eval
        print(f"Window {w_name}: LOYO AUC={w_eval['auc']:.4f}, Brier={w_eval['brier']:.4f}, Cal Slope={w_eval['cal_slope']:.4f}")

    # 4.2 Threshold Sensitivity: S >= 5% vs S >= 7% vs S >= 10%
    print("\n--- 4.2 Severity Threshold Sensitivity (5% vs 7% vs 10%) ---")
    thresh_results = {}
    for thresh in [5.0, 7.0, 10.0]:
        t_df = clean_df.copy()
        t_df['y_t'] = (t_df['S'] >= thresh).astype(int)
        
        t_preds = np.zeros(len(t_df))
        for yr in years:
            train_idx = t_df['year'] != yr
            test_idx = t_df['year'] == yr
            if t_df.loc[train_idx, 'y_t'].nunique() < 2:
                continue
            m = smf.logit('y_t ~ RH_A_PRE7_12H + T_9T30_PRE7_24H', data=t_df[train_idx]).fit(disp=False)
            t_preds[test_idx] = m.predict(t_df[test_idx])
            
        t_eval = evaluate_predictions(t_df['y_t'], t_preds)
        thresh_results[f"S >= {thresh}%"] = t_eval
        print(f"Threshold S >= {thresh}%: Prevalence={t_df['y_t'].mean():.3f}, LOYO AUC={t_eval['auc']:.4f}, Brier={t_eval['brier']:.4f}")

    # 4.3 Wheat Class Stratification: Winter vs Spring
    print("\n--- 4.3 Wheat Class Stratification (Winter vs Spring) ---")
    type_results = {}
    for w_type in ['winter', 'spring']:
        sub_df = clean_df[clean_df['type'] == w_type].copy()
        sub_years = sorted(sub_df['year'].unique())
        sub_preds = np.zeros(len(sub_df))
        sub_df = sub_df.reset_index(drop=True)
        
        for yr in sub_years:
            train_idx = sub_df['year'] != yr
            test_idx = sub_df['year'] == yr
            if sub_df.loc[train_idx, 'epidemic'].nunique() < 2:
                continue
            m = smf.logit('epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H', data=sub_df[train_idx]).fit(disp=False)
            sub_preds[test_idx] = m.predict(sub_df[test_idx])
            
        sub_eval = evaluate_predictions(sub_df['epidemic'], sub_preds)
        type_results[w_type] = sub_eval
        print(f"Wheat class '{w_type}' (N={len(sub_df)}): LOYO AUC={sub_eval['auc']:.4f}, Brier={sub_eval['brier']:.4f}")

    # Save all results to JSON for results.md compilation
    output_payload = {
        'full_models': full_fit_results,
        'loyo_summary': cv_eval_summary,
        'calibration_deciles_m2': cal_table.to_dict(orient='records'),
        'window_sensitivity': window_results,
        'threshold_sensitivity': thresh_results,
        'type_sensitivity': type_results,
        'annual_breakdown_m2': annual_results['M2_Bivariable_RHT']
    }
    
    with open('model_results_output.json', 'w') as f:
        json.dump(output_payload, f, indent=2, default=str)
    print("\nSaved full output payload to model_results_output.json.")

if __name__ == '__main__':
    main()
