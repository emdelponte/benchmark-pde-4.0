# Chronological Analysis Log — Autonomous FHB Prediction Benchmark

## Entry 1 — Project Initialization & Data Acquisition (2026-11-22 09:06 UTC-03:00)
- **Action:** Queried Zenodo API (`https://zenodo.org/api/records/23189372`) to inspect record metadata and file manifest without consulting related literature (strictly deferring literature review to Step 7 per protocol).
- **Findings from Zenodo manifest:**
  - Record title: *Field-plot dataset of Fusarium head blight (FHB) severity in wheat: fungicide-untreated small plots across the United States* (DOI: `10.5281/zenodo.23189372`, published 2026-10-06, creators include Denis A. Shah, Erick D. De Wolf, Pierce A. Paul, et al.).
  - Available files include `FHBVer2.parquet` (1.03 MB), `FHBVer2DataDict.yaml` (350.7 KB), `README.txt` (6.0 KB), `VariablesMetaData.csv` (45.8 KB), `FHBVer2Codebook.pdf` (1.67 MB), `FHBVer2Codebook.html` (10.9 MB), `FHBVer2.csv`, and RDS files.
- **Technical environment note:** Default `PATH` in PowerShell did not expose `python` or `Rscript` directly (Windows Store alias intercepted `python`). Initiated download of `README.txt`, `FHBVer2.parquet`, `FHBVer2DataDict.yaml`, `VariablesMetaData.csv`, and `FHBVer2Codebook.pdf` into `data/`, alongside filesystem discovery of installed R / Python environments.

## Entry 2 — Schema Cross-Check & Exploratory Data Audit (2026-11-22 09:12–09:21 UTC-03:00)
- **Actions & Technical Resolutions:**
  - Direct R `libcurl` download of `nanoparquet` encountered a Windows SSL connect error; resolved cleanly by fetching the CRAN Windows binary (`nanoparquet_0.5.2.zip`) via PowerShell native TLS (`Invoke-WebRequest`) and installing locally into R 4.5.2.
  - Executed `code/01_data_audit.R` (with one minor fix during script drafting: `time_step` column reference after joining YAML and CSV metadata, and upgrading GLMM variance-component estimation from Laplace `nAGQ=1` to 20-point adaptive Gauss–Hermite quadrature `nAGQ=20` after observing upward Laplace bias on small binary clusters).
  - Strictly avoided computing any correlations or models linking `S` (or binary epidemic indicators) to weather predictors during the audit so that `analysis_plan.md` remains genuinely prospective.
- **Key Audit Findings Documented in `data_audit.md`:**
  1. **Schema discrepancy across Zenodo files:** `FHBVer2.parquet`, `FHBVer2DataDict.yaml`, and `FHBVer2Codebook.pdf` contain `337` columns, whereas `FHBVer2.rds` and `FHBVer2.csv` contain `338` columns (`location` is present in `.rds`/`.csv` and absent from `.parquet`/`.yaml`, contradicting `README.txt` lines 8 & 113).
  2. **Missing binary response column:** Only continuous `S` (FHB index, %) is present in the schema and YAML dictionary. Adopted standard USWBSI threshold `S >= 10%` (`273` events [27.33%], `726` nonevents) as primary binary outcome, with pre-specified sensitivity checks at `5%`, `>10%`, and `15%`.
  3. **`win_length` off-by-one:** All 329 weather variables in `VariablesMetaData.csv` list `win_length = end - start`, whereas actual closed intervals `[start, end]` span `end - start + 1` days (`39` count variables exceed naive `win_length` bounds in the data).
  4. **UTC `12H` ("overnight") physical inversion:** Because weather timestamps were kept in UTC (`20:00–08:00 UTC` = `15:00–03:00 CDT` / `16:00–04:00 EDT`), `"overnight"` `12H` RH is *lower* than `24H` RH in 79–86% of rows and `"overnight"` VPD is *higher* than `24H` VPD in 80% of rows.
  5. **Hierarchical clustering & effective sample size:** The `999` plots represent only `545` unique weather profiles (`20.0%` of multi-plot weather profiles are discordant on `S >= 10%` due to cultivar `resist` and `corn` residue) and `142` `state × year` clusters (`ICC = 0.717`, Kish `DEFF = 12.39`, yielding `N_eff = 81` and `Events_eff = 22` at the state-year level).

## Entry 3 — Pre-Modeling Analysis Strategy Locked (2026-11-22 09:24 UTC-03:00)
- **Action:** Authored and locked `analysis_plan.md` prior to fitting any predictive models.
- **Core Design Choices:**
  - Pre-specified six compact logistic regression specifications (`M0`–`M5`), each strictly capped at `p <= 3` weather terms and `p <= 3` slope parameters, grounded in `24h` pre-anthesis thermal, moisture, and joint hydrothermal mechanisms (`[-7, 0]`, `[-10, 0]`, `[-15, 0]`, `[-20, -10]`).
  - Selected three grouped validation designs—Leave-One-Year-Out CV (32 years), Leave-One-State-Out CV (17 states), and 5×10-fold `state × year` Grouped CV (142 clusters)—with all scaling and `M5` penalized variable selection nested strictly inside training folds.

## Entry 4 — Model Execution, Bug Fixes, and Post-Plan Parsimony Reduction Check (2026-11-22 09:28–10:11 UTC-03:00)
- **Execution & Technical Issues Resolved:**
  1. Initial run of `code/02_model_fitting_and_validation.R` completed `LOYO` (32 years) and `LOSO` (17 states) cleanly, then halted during per-fold summary calculation in `5×10` grouped CV because `E1_LASSO174_1se` (`cv.glmnet` at `lambda.1se` across 174 predictors) shrunk all slope coefficients to `0` in several folds, producing zero variance in `logit(p_hat)` and causing `glm(y ~ lp)` to omit the slope column. Fixed by guarding `sd(lp) < 1e-8 -> Cal_Slope = NA_real_`, adding `na.rm = TRUE` to across-fold quantiles, and adding `dfmax = 30` to `E1_LASSO174` path-fitting.
  2. Re-ran `code/02_model_fitting_and_validation.R` and `code/03_sensitivity_and_figures.R` to completion (`exit code 0`), generating all CV tables, sensitivity analyses (`S1`–`S5`), and Figures 1–4.
- **Empirical Findings Prompting Transparent Post-Plan Parsimony Check (`code/04_posthoc_refinement_check.R`):**
  - Across all three grouped validation schemes, pre-specified 3-term `M2_Hydro3` (`TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2`) and 2-term baseline `M0_Base7d` (`T.A.PRE7.24H + RH7`) achieved the best out-of-sample probability accuracy and calibration (`LOYO Brier = 0.187` and `0.189`, `Cal_Slope = 0.827` and `0.847`), whereas data-driven L1-selected 3-term GLM (`M5a`), unconstrained 174-variable LASSO (`E1`), and bivariate spline GAM (`E2`) exhibited substantial overfitting (`LOYO Cal_Slope = 0.660`, `-0.808`, and `0.445`, respectively).
  - Crucially, cluster-robust inference on `state × year` (`142` clusters) showed that:
    - In `M0`, `T.A.PRE7.24H` was statistically indistinguishable from zero ($\hat{\beta} = -0.0266 \pm 0.0528$, $p = 0.614$), leaving `RH7` as the sole active predictor;
    - In `M2`, `TRH.15T30nRHG80.PRE15.24H` was completely redundant ($\hat{\beta} = +0.0014 \pm 0.0040$, $p = 0.732$) once 10-d evaporative demand (`VPD.A.1`, $p = 0.0005$) and 20-to-10-d pre-heading temperature (`T.A.2`, $p = 0.0234$) were included.
  - Rather than overwriting `analysis_plan.md` or discarding `M0`–`M5`, authored `code/04_posthoc_refinement_check.R` to formally evaluate the two nested parsimonious reductions (`M0r: epid10 ~ RH7` [1 parameter] and `M2r: epid10 ~ VPD.A.1 + T.A.2` [2 parameters]) alongside all original pre-specified models.

## Entry 5 — Independent Results & Critical Assessment Completed and Locked (2026-11-22 10:15 UTC-03:00)
- **Actions:**
  - Executed `code/04_posthoc_refinement_check.R` (`exit code 0`), confirming that `M2r` (`epid10 ~ VPD.A.1 + T.A.2`, 2 slope parameters) improves out-of-sample generalization across all three grouped validation schemes (`LOYO AUC = 0.671, Brier = 0.185, BSS = +7.8%, Cal_Slope = 0.894`; `LOSO AUC = 0.660, Brier = 0.187, BSS = +7.2%, Cal_Slope = 0.807`; `5×10 Grouped CV AUC = 0.661, BSS = +7.2%`), with `LRT p = 0.4955` against 3-term `M2`.
  - Authored and locked `results.md` and `critical_assessment.md`, documenting all pre-specified models (`M0`–`M5`), post-plan parsimony checks (`M0r`, `M2r`), secondary benchmarks (`E1`, `E2`), sensitivity analyses (`S1`–`S5`), cluster-robust uncertainty, spring-wheat failure mode, omitted-host-resistance ceiling, and UTC `12H` artifacts.
- **Milestone Verification:** All independent analytical deliverables (`data_audit.md`, `analysis_plan.md`, `code/`, `results.md`, `critical_assessment.md`) are now finalized prior to initiating the Step 7 literature search.


## Entry 6 — Post-Analysis Literature Search, Synthesis & Reproducibility Documentation (2026-11-22 10:18–10:24 UTC-03:00)
- **Actions:**
  - Conducted the Step 7 literature review strictly after locking Deliverables 1–5 (`data_audit.md`, `analysis_plan.md`, `code/`, `results.md`, `critical_assessment.md`).
  - Reviewed the six core peer-reviewed studies spanning this dataset's lineage: `De Wolf et al. (2003)` (*Phytopathology* 93:428–435), `Shah et al. (2013)` (*Phytopathology* 103:906–919), `Shah et al. (2019a)` (*Phytopathology* 109:96–110), `Shah et al. (2019b)` (*Phil. Trans. R. Soc. B* 374:20180273), `Shah et al. (2021)` (*PLOS Comput. Biol.* 17:e1008831, analyzing the exact `N = 999` `FHBVer2` dataset), and `Shah et al. (2023)` (*Phytopathology* 113:1483–1493, Random Forests on `FHBVer2`).
  - Authored `comparison_with_literature.md`, synthesizing agreements (identical `S >= 10%` threshold, limited marginal signal of proximal `[-7, 0]` temperature, complementary signal of 10-d VPD `VPD.A.1` + pre-heading temperature `T.A.2`, and high inter-model prediction correlation) and novel critical insights from our independent workflow (discovery of the UTC `12H` afternoon-contamination artifact, optimism of plot-level random 10-fold CV across 545 shared weather profiles and 142 `state × year` clusters, decomposition of the `resist` + post-anthesis skill ceiling reconciling our LOYO Brier of `0.185` [and `0.173` with `resist + corn`] with `Shah et al. 2021`'s `0.160–0.183`, and identification of the Northern Plains spring-wheat transportability failure).
  - Authored `README.md` with exact verified R 4.5.2 and package versions, full repository manifest, and step-by-step reproduction commands.
  - Verified that all eight benchmark deliverables (`data_audit.md`, `analysis_plan.md`, `code/`, `results.md`, `critical_assessment.md`, `comparison_with_literature.md`, `analysis_log.md`, `README.md`) and all generated outputs/figures are complete, non-empty, and unmodified as required by sequential integrity rules.
