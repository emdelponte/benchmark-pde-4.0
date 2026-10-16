# Autonomous Epidemiological Analysis Benchmark: Fusarium Head Blight (FHB) Risk Prediction

This repository contains the complete, autonomous scientific investigation, predictive modeling pipeline, and critical evaluation of Fusarium head blight (FHB) epidemic risk in wheat using weather information available strictly no later than anthesis.

---

## 1. Project Overview & Scientific Objective

The primary objective is to develop and critically evaluate a parsimonious, scientifically defensible statistical model for predicting FHB epidemic risk ($S \ge 10.0\%$) using meteorological predictors available **strictly no later than wheat flowering (anthesis)**.

- **Dataset Source:** Zenodo Record [10.5281/zenodo.23189372](https://zenodo.org/records/23189372) (Version 2.1.0, published October 6, 2026).
- **Authors/Curators:** Denis A. Shah, Erick D. De Wolf, Pierce A. Paul, Laurence V. Madden.
- **Observational Unit:** Fungicide-untreated small field plots ($N = 999$) across 17 US states from 1982 to 2015.
- **Prevalence:** 273 epidemic events ($27.33\%$) and 726 non-events.
- **Key Methodological Principle:** Strict parsimony ($\le 3$ weather predictor terms) evaluated via Leave-One-Year-Out Cross-Validation (LOYO-CV across 32 years) to prevent intra-cluster environmental leakage.

---

## 2. Directory Structure & Deliverables

```
├── README.md                      # Instructions for reproducing the analysis and project guide
├── data_audit.md                  # Comprehensive dataset audit, metadata cross-check, and quality assessment
├── analysis_plan.md               # Pre-modeling protocol formulated prior to fitting predictive models
├── results.md                     # Model parameters, LOYO-CV validation metrics, and sensitivity analyses
├── critical_assessment.md         # Independent appraisal of plausibility, parsimony, and transportability
├── comparison_with_literature.md  # Post-hoc comparative analysis against peer-reviewed literature
├── analysis_log.md                # Chronological record of decisions, attempts, challenges, and revisions
├── FHBVer2.parquet                # Primary dataset matrix (999 rows x 337 columns)
├── FHBVer2DataDict.yaml           # Machine-readable data dictionary and glossary
├── VariablesMetaData.csv          # Metadata on 329 weather predictors
├── README.txt                     # Provenance documentation from dataset authors
├── FHBVer2Codebook.pdf            # PDF codebook describing distributions
├── model_results_output.json      # Structured machine-readable results from LOYO-CV and sensitivity checks
├── code/
│   ├── 01_fit_models.py           # Primary Python pipeline: models, LOYO-CV, and sensitivity tests
│   ├── 01_fit_models.R            # Equivalent reproducible R pipeline
│   └── 02_generate_figures.py     # High-resolution figure generation script
└── figures/
    ├── roc_curves.png             # LOYO-CV ROC curves comparing all models
    ├── calibration_plot.png       # Decile calibration curves (M2 vs M5)
    └── annual_performance.png     # Annual LOYO AUC and Brier scores across seasons (2000–2015)
```

---

## 3. Environment & Software Requirements

The analysis is fully reproducible in either **Python 3** or **R (>= 4.4)**.

### Python Environment (Tested on Python 3.9.6 arm64)
Required packages:
```bash
pip install pyarrow pandas numpy statsmodels scikit-learn scipy matplotlib pyyaml
```
Package versions used:
- `pyarrow`: 21.0.0
- `pandas`: 2.3.3
- `numpy`: 2.0.2
- `statsmodels`: 0.14.6
- `scikit-learn`: 1.6.1
- `scipy`: 1.13.1
- `matplotlib`: 3.9.4
- `pyyaml`: 6.0.3

### R Environment (Tested on R 4.4.0 arm64)
Required packages:
```R
install.packages(c("arrow", "dplyr", "pROC", "yaml", "readr"))
```

---

## 4. Instructions for Reproducing the Analysis

### Step 1: Execute Primary Modeling Pipeline (Python)
Run the complete model estimation, cluster-robust inference, LOYO-CV validation, and sensitivity analyses:
```bash
python3 code/01_fit_models.py
```
This produces terminal logs and saves the complete results payload to `model_results_output.json`.

### Step 2: Generate Publication Figures
Generate high-resolution PNG figures in `figures/`:
```bash
python3 code/02_generate_figures.py
```

### Step 3: Optional R Cross-Verification
Execute the equivalent R reproduction script:
```bash
Rscript code/01_fit_models.R
```
This verifies exact metric parity (AUC, Brier score, calibration slope) across both programming languages.

---

## 5. Summary of Key Findings

1. **Selected Primary Weather Model (Model 2: Bivariable Logistic Regression):**
   $$\text{logit}(P(Y=1)) = -9.5015 + 0.0616 \cdot \text{RH.A.PRE7.12H} + 0.0234 \cdot \text{T.9T30.PRE7.24H}$$
   - **Out-of-Fold LOYO-CV ROC AUC:** **0.6557** ($95\%\text{ CI: } [0.619, 0.692]$)
   - **Brier Score:** **0.1884** (Brier Skill Score $BSS = +0.0515$)
   - **Calibration Intercept:** $-0.0036$ (near-zero bias)
   - **Calibration Slope:** $0.8471$
2. **Empirical Justification for Parsimony:**
   Adding a 3-parameter non-linear interaction term (`RH` $\times$ `T`) increased in-sample fit but **degraded out-of-fold generalization** (LOYO AUC dropped to 0.6513, calibration slope deteriorated to 0.7860). Complex machine learning (Random Forest) collapsed entirely under temporal cross-validation ($\text{AUC} = 0.5999$, $BSS = -0.0047$, slope $= 0.4611$).
3. **Decisive Moderating Effect of Cultivar Resistance (Model 5):**
   Integrating host genetics with pre-anthesis weather increased out-of-fold LOYO-CV AUC to **0.7084** ($95\%\text{ CI: } [0.673, 0.743]$) and $BSS$ to $+0.0950$, with Moderately Resistant cultivars experiencing an $82.4\%$ reduction in epidemic odds relative to Very Susceptible cultivars ($\text{OR} = 0.176$).
4. **Exposure Window Robustness:**
   Pre-anthesis exposure windows of 7 days ($\text{AUC} = 0.6557$), 10 days ($\text{AUC} = 0.6518$), and 14 days ($\text{AUC} = 0.6545$) yielded near-identical predictive skill ($\Delta\text{AUC} < 0.004$), proving that performance is not an artifact of an over-tuned window boundary.
5. **Critical Regional Vulnerability (Spring vs. Winter Wheat):**
   The weather model demonstrated solid transferability across 15 winter wheat states ($\text{AUC} = 0.6642$, slope $= 0.8302$), but broke down in spring wheat in North Dakota and Minnesota ($\text{AUC} = 0.5616$, slope $= 0.1188$). In continental spring wheat systems, flowering occurs later in mid-summer where post-anthesis convective rain events govern infection realization.

---

## 6. Citation of Source Data & Benchmark
- **Data Archive:** Shah, D. A., De Wolf, E. D., Paul, P. A., & Madden, L. V. (2026). *Field-plot dataset of Fusarium head blight (FHB) severity in wheat: fungicide-untreated small plots across the United States* (Version 2.1.0). Zenodo. [https://doi.org/10.5281/zenodo.23189372](https://doi.org/10.5281/zenodo.23189372).
- **Core Reference Papers:**
  - De Wolf et al. (2003), *Phytopathology* 93:428–435.
  - Shah et al. (2013), *Phytopathology* 103:906–919.
  - Shah et al. (2014), *Phytopathology* 104:630–641.
  - Shah et al. (2021), *PLOS Comput. Biol.* 17:e1008831.
