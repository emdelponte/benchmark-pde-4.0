# Critical assessment

Written after `results.md` and **before** any literature search. Robust findings are separated from exploratory ones at the end.

## 1. Is the answer "weather predicts FHB epidemics at anthesis"?

Only weakly. The best pre-specified weather-only model (M1: mean RH and mean T over the 10 days before anthesis) has a leave-one-year-out AUC of 0.645 (95% CI 0.55–0.73), a scaled Brier of 4%, and the plan's usefulness bar (AUC ≥ 0.65 with a clear Brier gain) is narrowly missed. I take this as a legitimate, partly negative result: with station-derived weather summaries ending at anthesis, these data support ranking *seasons/regions* by risk, but not a reliable plot-level forecast. Host resistance and corn residue add as much discrimination as weather does (host-only AUC 0.649), and the combination (M4, AUC 0.70) is the first model that would be worth piloting.

Why the weather signal is limited, in order of my judgement of importance:
1. **Post-anthesis weather is excluded by design.** Infection happens at and after flowering; pre-anthesis weather can only capture inoculum build-up and the persistence of wet regimes. An upper bound on what pre-anthesis weather can achieve is not knowable from this analysis, but the result is consistent with the biology.
2. **Exposure misclassification.** Weather comes from the nearest station (possibly a citizen station), at unknown distance, with UTC day boundaries rather than local ones; the "overnight" (12H) window is ≈ 15:00–03:00 local time. Measurement error biases coefficients towards zero and lowers AUC.
3. **Outcome heterogeneity.** S is described as "FHB index, or severity", collected by many collaborators, on cultivars of different resistance, with or without corn residue and presumably with differing inoculation practices (not documented). Much variation in S is unrelated to weather.
4. **Clustering.** 82% of the variance in the epidemic indicator is between weather environments. The information about weather effects is in ~545 environments and, more realistically, in ~142 state-years.

## 2. Epidemiological plausibility of the selected predictors

* **Mean RH in the 10 days before anthesis (positive association)**: plausible. Moist conditions favour perithecium maturation and ascospore release on residue and indicate a wet regime that tends to persist into flowering. The association was positive in 100% of year-bootstrap resamples, robust to window length (5–15 d), to 12H vs 24H averaging, to the epidemic threshold (5/10/15%), to environment weighting, and present in the strict ≥5-day-lead variable (hours VPD ≤ 1.1 kPa).
* **Mean temperature (no association in M1)**: in the range observed (≈ 10–25 °C 10-day means) temperature is probably rarely limiting before flowering, and temperature differences between sites are confounded with crop type and anthesis date (spring wheat flowers ~5 weeks later than winter wheat in a different region). In M6 an earlier window (−20…−10 d) gave a positive T effect. I do not interpret either sign causally; the T coefficient's sign is unstable across bootstrap resamples (39% positive in M1).
* **Duration of warm-humid hours (M2), the most "mechanistic" variable I specified, performed worst** (AUC 0.56, calibration slope 0.46). Possible reasons: the 15–30 °C lower bound removes many humid hours in cool springs (so the count conflates temperature and moisture), hourly RH ≥ 90% from distant stations is noisy, and the count is zero-heavy. A mechanistically appealing variable is not automatically a better predictor; I report this rather than replace M2.

## 3. Sample size versus complexity

Two to three weather parameters against ~273 events (~155–170 event environments; ~140 state-years) is a comfortable ratio, and the out-of-fold calibration slopes (0.80 for M1, 0.79 for M3) show only modest overfitting. Complexity that went beyond this budget or added data-driven choices hurt: the spline version of M1 (4 parameters) had slope 0.62 and lower AUC; window tuning (M5) lost 0.035 AUC; the 3-parameter interaction model added nothing. M4's 6 parameters are supported (slope 0.83) because resistance and residue have strong, well-identified effects. So the parameter budget was not the binding constraint; the signal was.

The meaningful "effective" sample size for the weather part is the number of independent seasons × regions. With only ~23 years containing events and several states contributing a single season, statements about transportability rest on few independent units.

## 4. Overfitting and optimism

* Apparent AUC (resubstitution) exceeded LOYO AUC by 0.02 (M1) to 0.05 (M2).
* Random row-level CV would have overstated M1's AUC by ~0.016 and, more importantly, its calibration slope (0.94 vs 0.80).
* **Optimism I cannot remove:** the 329 weather variables in the dictionary were designed and retained by the data authors partly because they predicted FHB in earlier versions of this dataset (README: uninformative variables were removed). Any analysis choosing among them — including mine, although I chose by mechanism and a single a-priori window — inherits some of that selection. My use of the simplest, most generic summaries (mean RH and T) limits but does not remove this.
* My own analysis also involved some researcher degrees of freedom after seeing results: the 7-day variable-name fix, the exploratory within/between decomposition and the observation that an RH-only model is as good as M1. These are labelled as such and none changed the final model.

## 5. Sensitivity to exposure-window definitions

Low for mean RH (AUC 0.637–0.649 across 5–15 d windows; 12H vs 24H nearly identical), moderate for the duration variable (0.552–0.577, best with the shortest window). Strict timing (only information ≥ 5 days before anthesis) loses nothing in LOYO. This matters for the day-0 issue raised in the audit: the borderline inclusion of the flowering day (up to 24–32 h after the 00 UTC reference) does not drive the result, so the timing constraint is satisfied in substance.

## 6. Redundancy and instability

* Within each model the terms are nearly uncorrelated (VIF ≤ 1.04), so instability is not collinearity among the chosen terms.
* Across the candidate pool, however, many variables measure nearly the same thing (174 pre-anthesis variables, 4% of pairs |ρ| > 0.8, 14 principal components for 90% of variance). Different moisture variables (mean RH, VPD ≤ 1.1 kPa hours, RH ≥ 90% hours) are interchangeable carriers of the same "wet season" signal; which one "wins" would vary with the sample.
* The temperature effect is unstable in sign across windows and resamples.

## 7. Variation across environments; calibration and transportability

* **Years:** within-year AUC varies widely (0.35–0.89 among 15 evaluable years). Year-level predicted prevalence tracks observed prevalence in order (r = 0.83) but in a compressed range (0.20–0.35 predicted vs 0.05–0.43 observed). The model cannot predict a very bad or very good year with confidence.
* **States:** leave-one-state-out AUC is similar overall (0.64), but state-level prevalence is poorly reproduced (r = 0.27): MO's epidemic rate (63%) is grossly underpredicted and PA, NY, WI overpredicted. Something state-specific — inoculum, residue management, cultivar mix, inoculation/misting in trials, assessment practice — is not captured by weather. Transport to a new state requires local recalibration of at least the intercept.
* **Time:** training on 1982–2008 and testing on 2009–2015 gave the best numbers for M1 (AUC 0.663, slope 0.98) but M4 underpredicted the later period (calibration intercept +0.40), consistent with a shift in the trial population (more states, more resistant cultivars in the later trials, or changed protocols).
* **Within vs between (exploratory):** the RH association exists only between state-years. Within a state-year, plots at stations with higher RH were not more likely to have epidemics. So the model is best understood as a regional season-level risk indicator. Using it to discriminate between nearby fields in the same season is not supported by these data.

## 8. Prediction versus explanation

All effects are predictive associations. RH is a proxy for a set of correlated conditions (rain, leaf wetness, residue moisture, persistence into flowering), and is confounded with region, crop type, anthesis timing, trial management and possibly inoculation practices. The ORs are not causal effects of humidity, and the null temperature effect does not show temperature is irrelevant to FHB biology.

## 9. Limitations of the retrospective observational data

* Convenience sample of cooperative variety/fungicide trials; not representative of commercial fields. Fungicide-untreated plots, possibly artificially inoculated or misted (undocumented), which would weaken the link between natural weather and disease.
* No site identifier or coordinates; weather environments had to be reconstructed by hashing identical weather vectors, which assumes identical vectors mean the same station-date (true by construction here, as none spanned years/states/dates).
* Unbalanced in time (63% of rows 2009–2015) and space (ND 27%).
* The binary outcome is my derivation; there is no documented epidemic variable.
* Weather timing in UTC with a 00 UTC anthesis reference; anthesis date itself is a field estimate.
* Files were supplied by the user; I could not verify them against Zenodo checksums.

## 10. What would be needed for prospective validation

1. A truly independent set of seasons (e.g. 2016 onward) and new locations, with predictions issued before outcomes are known, and the same outcome protocol.
2. Site coordinates and station distance (or gridded/reanalysis weather at the plot) to reduce exposure error, with local-time day boundaries.
3. Documentation of inoculation/misting, residue level (not just presence), cultivar identity, and assessment method (index vs severity, growth stage).
4. Weather forecasts for the days after anthesis (if the tool is to be used at anthesis, forecast skill for the infection window becomes the key uncertainty).
5. Enough independent seasons per region to estimate region-specific intercepts or random effects, and a decision analysis (costs of spraying vs losses) to choose a probability threshold.

## 11. Robust findings vs exploratory observations

**Robust (pre-specified, consistent across validation schemes and sensitivity analyses):**
* Pre-anthesis weather-only logistic models give weak discrimination (AUC ≈ 0.64–0.66) and small Brier gains.
* Moisture (mean RH before anthesis) carries the weather signal; it is stable in sign and insensitive to window length and averaging period.
* Clustering matters: naive SEs are ~half the cluster-robust ones; row-level CV is optimistic.
* Window tuning, splines, interactions and a random forest on all pre-anthesis variables do not improve validated performance.
* Cultivar resistance and corn residue add substantial, well-identified risk information (M4 AUC ≈ 0.70).

**Exploratory (post hoc or single analysis; treat as hypotheses):**
* The RH association is between state-years only.
* Temperature has a positive association in an earlier window (−20…−10 d) but none in the last 10 days.
* An RH-only model is as good as RH+T.
* The 2009–2015 period has a higher epidemic rate for a given predicted risk under M4.
