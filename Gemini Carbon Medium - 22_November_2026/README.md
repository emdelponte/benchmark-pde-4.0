# Autonomous Epidemiological Analysis Benchmark — Fusarium Head Blight (FHB) Prediction

This repository contains a complete, reproducible, and independently executed epidemiological modeling analysis of **Fusarium head blight (FHB)** of wheat using the publicly archived U.S. field-plot dataset (**Zenodo record [23189372](https://zenodo.org/records/23189372)**; DOI `10.5281/zenodo.23189372`, Version `2.1.0`).

The primary scientific goal is to predict the probability of a major FHB epidemic ($Y = \mathbb{I}(S \ge 10\%)$) **no later than wheat anthesis** (`window_end_day <= 0`) using a parsimonious, biologically defensible logistic regression model ($\le 3$ weather predictor parameters), validated across unseen years and geographic regions.

---

## 1. Summary of Key Findings

- **Recommended Parsimonious Model (`M2r`, 2 weather slope parameters):**
  $$\text{logit}\bigl(P(S \ge 10\%)\bigr) = -1.6177 - 0.1790\,\text{VPD.A.1} + 0.0888\,\text{T.A.2}$$
  combining **10-day pre-anthesis vapor pressure deficit** (`VPD.A.1`, days `[-10, 0]`, cluster-robust $p = 0.0001$) and **pre-heading mean air temperature** (`T.A.2`, days `[-20, -10]`, cluster-robust $p = 0.0060$), reduced transparently (`LRT p = 0.4955`) from the pre-specified 3-parameter specification `M2` (`TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2`). A 1-parameter fallback (`M0r: RH7`, 7-day pre-anthesis relative humidity) achieves nearly comparable skill.
- **Grouped Out-of-Sample Performance (`M2r`):**
  - **Leave-One-Year-Out CV (`32` years):** `ROC-AUC = 0.671` (`95% cluster bootstrap CI: [0.587, 0.743]`), `Brier = 0.185`, `Brier Skill Score = +7.8%`, `Calibration Slope = 0.894`, `Calibration Intercept = +0.008`, `ICI = 0.036`.
  - **Leave-One-State-Out CV (`17` states):** `ROC-AUC = 0.660` (`[0.569, 0.727]`), `Brier = 0.187`, `BSS = +7.2%`, `Calibration Slope = 0.807`, `ICI = 0.019`.
  - **5×10 Grouped `state × year` CV (`142` clusters):** `ROC-AUC = 0.661`, `Brier = 0.186`, `BSS = +7.2%`, `Calibration Slope = 0.861`.
- **Critical Audit & Validation Discoveries:**
  1. **Severe Clustering (`N = 999` plots $\rightarrow$ `545` weather profiles $\rightarrow$ `142` `state × year` clusters):** `state × year` ICC is `0.717` (`DEFF = 12.39`, $E_{\text{eff,sy}} = 22$ effective events). Observation-level random CV leaks shared weather profiles across folds, artificially inflating complex learners (`GAM`, `LASSO`), whereas under grouped CV, 1–2 parameter GLMs outperform high-dimensional and nonlinear models.
  2. **UTC `12H` ("Overnight") Physical Inversion:** Timestamps were retained in UTC (`20:00–08:00 UTC` = `15:00–03:00 CDT`), contaminating `"overnight"` `12H` variables with mid-afternoon heat (`12H` RH < `24H` RH in `79–86%` of rows).
  3. **Structural Ceiling & Regional Limits:** Omitting cultivar susceptibility (`resist`) and corn residue (`corn`) caps pure pre-anthesis weather discrimination (`adding resist + corn lifts LOYO AUC to 0.723, BSS to +13.6%`), and pre-anthesis weather alone fails to discriminate epidemic risk in **Northern Plains spring wheat** (`LOYO AUC = 0.568, BSS = -2.6%`).

---

## 2. Repository Structure & Deliverables

| Deliverable / Path | Description |
| :--- | :--- |
| [data_audit.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/data_audit.md) | **Deliverable 1:** Dataset description, Parquet-vs-YAML-vs-CSV schema cross-check, six metadata discrepancies, clustering/ICC audit, and effective sample size ($E_{\text{eff}}$) derivation. |
| [analysis_plan.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/analysis_plan.md) | **Deliverable 2:** Prospective analysis strategy written and locked *before* fitting any predictive models (preserved unmodified). |
| [code/](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code) | **Deliverable 3:** Reproducible, modular R scripts (`01` through `04`) executing the entire audit, modeling, validation, sensitivity, and figure pipeline. |
| [results.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/results.md) | **Deliverable 4:** Full model parameter estimates (naive vs. cluster-robust SEs), grouped validation metrics (`LOYO`, `LOSO`, `5×10` `state × year`), random-CV leakage benchmark, and sensitivity analyses (`S1`–`S5`). |
| [critical_assessment.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/critical_assessment.md) | **Deliverable 5:** Critical evaluation of biological plausibility, effective sample size, overfitting, regional transportability failures, calibration, and prospective validation needs. |
| [comparison_with_literature.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/comparison_with_literature.md) | **Deliverable 6:** Post-analysis comparison against published FHB studies (`De Wolf et al. 2003`; `Shah et al. 2013, 2019a, 2019b, 2021, 2023`), written strictly after locking Deliverables 1–5. |
| [analysis_log.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/analysis_log.md) | **Deliverable 7:** Chronological record of analytical decisions, technical resolutions, post-plan parsimony checks, and sequential workflow milestones. |
| [README.md](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/README.md) | **Deliverable 8:** Reproduction guide, software environment, dependencies, and file manifest. |

### Analysis Scripts (`code/`) and Generated Outputs (`output/`)
- [01_data_audit.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/01_data_audit.R) $\rightarrow$ Audits schema/metadata, UTC `12H` inversion, collinearity, and GLMM `nAGQ=20` ICCs; writes `output/audit_artifacts.rds`.
- [02_model_fitting_and_validation.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/02_model_fitting_and_validation.R) $\rightarrow$ Fits `M0`–`M5` and exploratory `E1`/`E2`, computes 142-cluster sandwich SEs, and runs `LOYO`, `LOSO`, `5×10` grouped `state × year` CV, and `5×10` random CV; writes `output/cv_performance_summary.csv`, `output/full_model_coefficients.csv`, `output/full_model_fit_summary.csv`, `output/loyo_by_year.csv`, `output/loso_by_state.csv`, and `output/modeling_results.rds`.
- [03_sensitivity_and_figures.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/03_sensitivity_and_figures.R) $\rightarrow$ Runs sensitivity checks `S1`–`S5` (`output/sens_s1_windows.csv` to `sens_s5_subpopulations.csv`) and generates Figures 1–4 in `output/figures/`.
- [04_posthoc_refinement_check.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/04_posthoc_refinement_check.R) $\rightarrow$ Evaluates nested parsimonious reductions (`M0r`, `M2r`), computes 2,000-replicate `state × year` cluster-bootstrap 95% CIs, and generates `output/posthoc_parsimony_reductions.csv` and `output/figures/fig5_final_m2r_risk_surface.png`.

---

## 3. Software Environment & Dependencies

All analyses were executed on Windows (x86_64-w64-mingw32/x64) using **R version 4.5.2 (2025-10-31 ucrt)** with the following verified package versions:

| Package | Version | Purpose |
| :--- | :--- | :--- |
| `nanoparquet` | `0.5.2` | Reading `FHBVer2.parquet` and extracting Parquet schema |
| `yaml` | `2.3.10` | Parsing `FHBVer2DataDict.yaml` variable definitions and units |
| `dplyr` | `1.2.1` | Data manipulation and grouped aggregation |
| `tidyr` | `1.3.2` | Reshaping validation and summary tables |
| `ggplot2` | `4.0.3` | Generating diagnostic, calibration, and risk-surface figures |
| `pROC` | `1.19.0.1` | Exact ROC-AUC computation (`direction = "<"`) |
| `glmnet` | `5.1` | Nested L1-penalized logistic screening (`M5`, `E1`) |
| `mgcv` | `1.9.3` | Penalized thin-plate regression spline GAM (`E2`) |
| `lme4` | `1.1.38` | Random-intercept binomial GLMMs (`nAGQ = 20`) for ICC audit |
| `Matrix` | `1.7.4` | Sparse/dense matrix algebra for `glmnet` and `lme4` |
| `boot` | `1.3.32` | Supporting bootstrap utilities |
| `splines` | `4.5.2` | Base R spline basis utilities |

To install any missing packages in R:
```r
install.packages(c(
  "nanoparquet", "yaml", "dplyr", "tidyr", "ggplot2",
  "pROC", "glmnet", "mgcv", "lme4"
))
```

---

## 4. Step-by-Step Reproduction Instructions

### Step 1: Data Placement (`data/`)
The Zenodo archive files from [https://zenodo.org/records/23189372](https://zenodo.org/records/23189372) are stored in `data/`. If reproducing from a fresh clone without `data/`, download the required files from Zenodo into `data/`:
```powershell
New-Item -ItemType Directory -Force -Path data | Out-Null
$base = "https://zenodo.org/api/records/23189372/files"
foreach ($f in @("FHBVer2.parquet","FHBVer2DataDict.yaml","README.txt","VariablesMetaData.csv","FHBVer2Codebook.pdf","FHBVer2.rds","FHBVer2.csv","VariablesMetaData.rds")) {
  Invoke-WebRequest -Uri "$base/$f/content" -OutFile "data/$f"
}
```

### Step 2: Execute the Full Analytical Pipeline
From the project root directory (`Gemini Carbon Medium - 22_November_2026`), run the four R scripts sequentially (all random seeds are fixed via `set.seed(20261122)` for exact numerical reproducibility; total runtime is ~2–3 minutes):

```powershell
$R = "C:\Program Files\R\R-4.5.2\bin\Rscript.exe"   # Or simply "Rscript" if on PATH
& $R code/01_data_audit.R
& $R code/02_model_fitting_and_validation.R
& $R code/03_sensitivity_and_figures.R
& $R code/04_posthoc_refinement_check.R
```

All tabular summaries are written to `output/*.csv` and all diagnostic figures (`fig1` through `fig5`) are written to `output/figures/*.png`.
