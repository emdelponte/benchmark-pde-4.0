# FHB prediction at anthesis
Start with data_audit.md, then analysis_plan.md, results.md, critical_assessment.md and comparison_with_literature.md. The plan is preserved as written before fitting. See analysis_log.md for the sequencing and subsequent diagnostics.

## Reproduction
Tested in Python 3.12.14 on Linux. From this directory, in an environment with Python and curl:
~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python code/acquire.py
python code/audit.py
python code/model.py
python code/uncertainty.py
~~~
The archive includes all nine source files and the record JSON, so the acquire step can be skipped offline. The acquisition script checks the deposited hashes against the version-specific API. Model fits use deterministic Newton scoring. The paired diagnostic uses seed 23189372 and 5,000 bootstrap samples. No tuning split is required. Re-running the code regenerates the audit tables, fold predictions, diagnostics, metrics and figure. The Markdown reports preserve the interpretation and decision sequence.

## Outputs
- schema.csv and eligible_correlations.csv provide the per-field checks and correlation matrix. audit_year.csv and audit_state.csv list sample sizes, events and prevalence for the derived endpoint.
- coefficients.csv includes estimates, cluster standard errors and 95% limits (log-odds). fold_coefficients.csv contains every training-fold fit. influence.csv records the five largest approximate row-level Cook distances for each specification.
- predictions.csv retains the original plot ID and held-out risk. Join to data/FHBVer2.parquet by id. Model name “null” is a literal string; use keep_default_na=False when reading model labels with pandas. equal_cluster and weighted_additive give each state/date cluster unit total weight. strict_endpoint and strict_additive use S > 10%.
- performance.csv gives pooled scores; folds.csv gives individual group results. Blank metrics are unestimable. An offset is estimated with calibration slope fixed to one; the reported slope comes from a separate logistic recalibration with a free intercept. Calibration.png (filename calibration.png) and calibration_bins.csv use design-specific quintiles for each model. paired_brier.csv gives conditional uncertainty.
- The projected use is a forecast for an untreated plot at 00 UTC on flowering date. No management threshold or prospective efficacy has been established.

## Data attribution
Shah DA, De Wolf ED, Paul PA, Madden LV. Field-plot dataset of Fusarium head blight (FHB) severity in wheat: fungicide-untreated small plots across the United States. Zenodo version 2.1.0, CC BY 4.0. https://doi.org/10.5281/zenodo.23189372
