# Independent results — before literature search

The reproducible audit completed on the 999-row version 2.1.0 dataset. No predictive model was fitted. The released YAML, README, weather metadata and HTML codebook document continuous severity S, but neither a binary epidemic label nor its cutoff. Logistic regression to S would violate the specified binary target; treating S>0 or applying an assumed severity threshold would change the estimand without documentation.

| Requested result | Independent status |
|---|---|
| Binary prevalence; events and nonevents | Undefined: target definition missing |
| Baseline logistic estimates | Not fitted: outcome gate failed |
| Scientifically motivated alternative | Prespecified conditionally in analysis_plan.md; not fitted |
| ROC AUC; Brier score; log loss | Not estimable for an undefined binary target |
| Calibration intercept/slope/plot | Not estimable |
| Predictor effect confidence intervals | Not estimable without fitting |
| Influence diagnostics | Not estimable; predictor-extreme scan is descriptive only |
| Validation-group variability | Counts/continuous severity available; binary model performance unavailable |

Robust descriptive findings: 337 columns exactly match the YAML; only corn has missing values (4). Numeric CSV and Parquet values agree. S ranges from 0 to 86.18%, median 2.868%; 186 rows are zero. Geography and years are unevenly represented. There are 545 distinct complete weather profiles and 142 state-years, indicating substantial potential dependence.

151 of 174 summaries labeled pre-anthesis contain day 0 under the YAML closed-window convention. At the documented 00 UTC prediction instant they are ineligible. 23 summaries end strictly earlier. The CSV window lengths conflict with the YAML by one day for all 329 weather variables. These constraints would still matter if a valid response definition were obtained.

See data_audit.md and the machine-readable outputs for all checks. This independent conclusion is finalized before the literature search. Any subsequent literature-informed analysis must be explicitly marked and preserve this record.
