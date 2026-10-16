# Analysis plan — FHB epidemic risk at anthesis

**Version 1.0, written 2026-10-10 after the audit (`data_audit.md`) and before fitting any model or computing any outcome–predictor association.** This version is frozen; any later change is added as a dated amendment at the end of this file, not by editing the text above it.

Disclosure of prior knowledge: from training I have general knowledge of the US FHB forecasting literature (De Wolf, Shah, Paul, Madden and colleagues), including that a 10% FHB index is commonly used to define an epidemic and that humidity/temperature durations around anthesis are commonly used. While trying to locate the record, I also saw (but did not open) search-result titles including Shah et al. 2013 (see `analysis_log.md`). The choices below are justified by mechanism and by the audit; where they coincide with published practice, that is stated rather than hidden.

## 1. Prediction target and intended use

* **Target:** probability that a fungicide-untreated wheat plot reaches an FHB epidemic, defined as **FHB index S ≥ 10%** (`epi10`).
* **Prediction time:** anthesis (flowering date). Use: a season- and site-specific risk estimate at early flowering to support the decision whether to apply a flowering fungicide, for wheat regions and cultivar types like those in the data (US winter and spring wheat, 1982–2015).
* **Why 10%:** the dataset documents no binary outcome (audit §3), so one must be derived. 10% is a level at which FHB causes economically important yield and grain-quality (mycotoxin) losses in susceptible cultivars, it splits the data into 273 events / 726 non-events (27%) so both classes are well represented, and it is the conventional threshold in this research area (stated openly: I knew this before the analysis). Thresholds of 5% and 15% are pre-specified sensitivity analyses.
* Unit of analysis: the plot (row), because that is what the outcome refers to; but inference and validation respect the clustering of plots within weather environments, state-years and years.

## 2. Admissible predictors (timing rule)

* **Excluded:** all 137 post-anthesis and 18 pre-post variables (incl. INT3, RH.A.3); 5 deprecated duplicates.
* **Primary admissible set:** variables with `analysis_period == "pre"` (window end ≤ day 0). Day 0 (00–23 UTC of the flowering date) is accepted as "available at anthesis": operationally, a decision made during the flowering day can use observations or near-certain short-range forecasts for that day, and flowering of a field spans several days. This is a judgement, not a fact, and the audit shows day-0 windows extend up to ~1 day (24H) or ~1.3 days (12H) past the 00 UTC reference.
* **Strict sensitivity set:** only windows ending ≤ day −5 (23 variables), i.e. information available ≥ 5 days before anthesis.
* Non-weather predictors known at anthesis: `resist` (cultivar resistance), `corn` (corn residue), `type` (spring/winter). They are not weather terms and are used only in a pre-specified host-context model (M4), reported separately.

## 3. Epidemiological reasoning and candidate weather variables

The FHB cycle that weather before anthesis can influence:
1. **Inoculum production** — *Fusarium graminearum* perithecia mature on crop residue and release ascospores mainly when residue is wet and temperatures are moderate-to-warm, during the 1–3 weeks before flowering. → moisture duration and temperature over ~1–2 weeks pre-anthesis.
2. **Infection at flowering** — needs spores plus wetness/high humidity at and just after anthesis with temperatures ~15–30 °C. Post-anthesis weather is excluded by design; pre-anthesis humidity in the last days before flowering acts as a proxy for persistent wet regimes (weather persistence).
3. Cold or dry conditions suppress both.

Therefore the weather predictors are chosen to represent **two dimensions — moisture and temperature — over a single primary window of 10 days before anthesis (days −10…0)**, which covers spore maturation/release and the run-up to flowering, and is long enough to average out single-day station error. I will not search over windows for the primary models.

Pre-specified primary variables (YAML names; all windows −10…0, 24H):
* `RH.A.PRE10.24H` — mean daily RH (%): overall moisture regime.
* `T.A.PRE10.24H` — mean daily air temperature (°C): thermal suitability for pathogen development.
* `TRH.15T30nRHG90.PRE10.24H` — hours with 15 ≤ T ≤ 30 °C and RH ≥ 90%: duration of jointly favourable conditions (count, 0–264).

## 4. Models (all logistic regression)

| Model | Weather terms (parameters) | Other parameters | Rationale |
|---|---|---|---|
| M0 | none | intercept | reference: predicts training-fold prevalence |
| **M1 baseline** | RH.A.PRE10.24H, T.A.PRE10.24H (2) | intercept | simplest two-mechanism model, linear |
| M2 duration | √(TRH.15T30nRHG90.PRE10.24H), T.A.PRE10.24H (2) | intercept | moisture *duration* under suitable T instead of mean RH; √ for a right-skewed count |
| M3 interaction | RH, T, RH×T (3) | intercept | moisture effect plausibly depends on temperature (and vice versa) |
| M4 host context | M1 weather terms (2) | intercept + resist (3 dummies, VS reference) + corn (1) | resistance & residue are known at anthesis and explain within-environment variation; complete cases (4 rows with missing corn dropped) |
| M5 window-tuned | as M1, but the window (5, 7, 10, 14, 15 d) for RH and for T chosen by AIC **inside each training fold** | intercept | quantifies whether tuning the exposure window helps once its selection cost is accounted for |
| M6 strict-timing | VPD.L11.CHD.1 (hours VPD ≤ 1.1 kPa, −15…−5), T.A.2 (mean T, −20…−10) (2) | intercept | same two mechanisms using only information ≥ 5 d before anthesis |

Weather-term counts never exceed 3; total estimated predictor parameters (excl. intercept): M1 2, M2 2, M3 3, M4 6, M5 2 (+ window choice, a tuning step), M6 2. Continuous predictors are entered linearly after centring (scaling only affects interpretation). Linearity of M1 terms is checked in a sensitivity model with restricted cubic splines (3 knots → 2 parameters each, 4 total; this exceeds no weather-term limit but is a complexity check, not a candidate final model).

## 5. Collinearity

One variable per mechanism; RH and T within the same window are expected to be only moderately correlated. I will report environment-level correlation and VIFs among the terms of each model. Mean RH and the TRH duration are alternative representations of moisture and are never in the same model.

## 6. Complexity control and final-model rule

* No automated search over the 174 pre-anthesis variables for the primary analysis. The only tuning (M5) is nested in the validation folds.
* Events per parameter: ~273 row-level / ~155–170 environment-level events vs 2–3 weather parameters (≥ 50 environment-level events per parameter); M4 has 6 parameters (~25–28). This is defensible because the models are pre-specified (no selection optimism), but shrinkage is still checked via the out-of-fold calibration slope.
* **Final-model rule (pre-specified):** among weather-only models, prefer the one with fewest parameters whose leave-one-year-out pooled AUC is within 0.02 of the best, whose Brier score is not worse by more than 0.005, and whose out-of-fold calibration slope lies in 0.8–1.2. Ties go to the more mechanistically interpretable model. M4 is reported as the recommended *applied* model if adding host information clearly improves performance, but the weather-only model is the answer to the benchmark question. If no model beats M0 meaningfully (AUC < 0.65 or Brier no better than M0), I will conclude that the data do not support a useful weather-only model.

## 7. Validation design

* **Primary: leave-one-year-out (LOYO)**, 32 folds. Year is the natural forecasting unit (a new season), and every weather environment and state-year falls inside one fold. Out-of-fold predictions are pooled across folds for AUC, Brier and calibration, because many years are tiny and 9 have no events.
* **Secondary: leave-one-state-out (LOSO)**, 17 folds — spatial transportability.
* **Temporal hold-out:** train on 1982–2008 (374 rows), test on 2009–2015 (625 rows) — closest to prospective use.
* **Optimism contrast (diagnostic only):** 10-fold CV with folds grouped by weather environment, and plain row-level 10-fold CV, to show how much clustering would inflate performance if ignored.
* All preprocessing (centring, window selection in M5, spline knots, imputation) is done inside training folds.

## 8. Performance metrics

* Discrimination: ROC AUC (pooled out-of-fold), with 95% CI from a cluster bootstrap over years (1,000 resamples of years, applied to the pooled out-of-fold predictions).
* Overall accuracy: Brier score and scaled Brier (1 − Brier/Brier of M0's out-of-fold predictions); log loss.
* Calibration: calibration intercept (calibration-in-the-large, logit offset) and calibration slope (logistic regression of outcome on logit of out-of-fold prediction); calibration plot (deciles of predicted risk, observed proportion with binomial CIs).
* Heterogeneity: per-year and per-state AUC where the fold has ≥ 3 events and ≥ 3 non-events, plus per-fold observed vs mean predicted prevalence for all folds.
* Decision-oriented (secondary): sensitivity and specificity at the training prevalence as the probability cut-off.
* Model comparison: paired cluster-bootstrap differences in AUC and Brier vs M1.

## 9. Effects and uncertainty

Final models are refitted on all data. Coefficients are reported as odds ratios per interpretable unit (e.g. per 10% RH, per 1 °C, per 10 h) with **cluster-robust (state-year) 95% CIs**, plus naive model-based CIs for contrast. Effects are interpreted as predictive associations, not causal effects (exposures are station-based proxies, confounded by region, cultivar mix, residue and inoculum).

## 10. Sensitivity analyses (all pre-specified)

1. Epidemic threshold 5% and 15% (M1, M2).
2. Window length 5, 7, 14, 15 d instead of 10 for M1 (all reported, none selected).
3. 12H ("overnight", UTC) instead of 24H mean RH (`RH.A.PRE10.12H`).
4. Strict timing (M6).
5. Linearity: M1 with restricted cubic splines.
6. Clustering in estimation: weights 1/(environment size) so each environment counts once, and GEE with exchangeable correlation within state-years, for coefficient stability.
7. Exclusion of years before 1995 (sparse early data).
8. Supplementary non-logistic benchmark: random forest on all 174 admissible pre-anthesis variables under LOYO, as an exploratory ceiling only — it will not replace the logistic model.

## 11. Deliverables and order

audit (done) → this plan → `code/03_models.py` (fits + validation) → `results.md` → `critical_assessment.md` → literature search → `comparison_with_literature.md` → `README.md`. All decisions and failures are logged in `analysis_log.md`.

---
## Amendments
* 2026-10-10 14:05 (implementation, no change of intent): the 7-day 24H mean RH and TRH90 count exist only under legacy names (`RH7`, `TRH907`); these were used for the 7-day window in M5 and the window sensitivity analysis.
* 2026-10-10 14:35 (after the literature search): additional checks in `code/05_post_literature.py` (wheat type × corn term, row-level vs LOYO CV, temperature-variability variable T.SD.1). They are outside this plan, do not alter the primary analysis or final model, and are reported only in `comparison_with_literature.md`.
