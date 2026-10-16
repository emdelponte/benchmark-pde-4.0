# Results — FHB epidemic risk from weather available at anthesis

All numbers come from `code/03_models.py` (tables in `outputs/models/`, console log in `outputs/models_stdout.txt`) unless marked *exploratory* (`code/04_exploratory.py`). Outcome: FHB index S ≥ 10% (273 events / 726 non-events, 999 plots, 545 weather environments, 32 years, 17 states). Plan: `analysis_plan.md` v1.0 (unchanged; one implementation fix is logged).

## 1. Headline

* **Weather-only logistic models discriminate weakly.** The pre-specified baseline M1 (mean RH and mean T over the 10 days up to anthesis) reaches a leave-one-year-out (LOYO) AUC of **0.645 (95% CI 0.554–0.727)** and improves the Brier score only from 0.201 (prevalence-only) to 0.192 (scaled Brier 4%). This is just below the 0.65 bar I set in the plan for a "useful" weather-only model, and the Brier improvement over prevalence-only has a bootstrap CI that includes zero.
* **Mean RH carries essentially all the weather signal; mean temperature adds nothing.** Odds of an epidemic rise about 2.2-fold per 10 percentage points of mean RH (cluster-robust 95% CI 1.5–3.3).
* **That RH signal is a season-and-region signal.** *Exploratory:* it operates entirely between state-years; within a state-year RH has no association with epidemics.
* **Adding cultivar resistance and corn residue (M4)**, both known at anthesis, raises LOYO AUC to **0.702 (0.641–0.760)**, ΔAUC +0.059 (0.009–0.117) over M1 on the same rows, with Brier 0.180.
* Tuning the exposure window, using a "favourable-hours" duration variable, adding an RH×T interaction, splines, or a random forest on all 174 pre-anthesis variables did **not** improve on M1.

## 2. Models and parameter counts

| Model | Weather terms | Estimated predictor parameters (excl. intercept) |
|---|---|---|
| M0 | — | 0 |
| M1 baseline | RH.A.PRE10.24H, T.A.PRE10.24H | 2 |
| M2 duration | √TRH.15T30nRHG90.PRE10.24H, T.A.PRE10.24H | 2 |
| M3 interaction | RH, T, RH×T | 3 |
| M4 host context | RH, T + resist (3 dummies) + corn | 6 (2 weather) |
| M5 tuned window | RH, T with windows chosen by AIC in each training fold (25 window pairs) | 2 + 1 tuning choice |
| M6 strict timing | VPD.L11.CHD.1 (h VPD ≤ 1.1 kPa, d −15…−5), T.A.2 (mean T, d −20…−10) | 2 |

Collinearity is negligible within every model (all weather VIFs ≤ 1.04; environment-level Spearman ρ(RH10, T10) = −0.12, ρ(VPD.L11.CHD.1, T.A.2) = −0.37).

## 3. Validation performance

Pooled out-of-fold predictions. CIs for LOYO from 1,000 bootstrap resamples of years.

### Leave-one-year-out (primary, 32 folds)

| Model | AUC (95% CI) | Brier | Scaled Brier | Log loss | Cal. intercept | Cal. slope |
|---|---|---|---|---|---|---|
| M0 intercept | 0.353* | 0.201 | 0 | 0.591 | 0.01 | — |
| **M1 RH+T** | **0.645 (0.554–0.727)** | 0.192 | 0.042 | 0.567 | 0.00 | 0.80 |
| M2 √TRH90+T | 0.561 (0.471–0.650) | 0.199 | 0.005 | 0.588 | 0.01 | 0.46 |
| M3 RH×T | 0.643 (0.549–0.732) | 0.192 | 0.044 | 0.567 | 0.00 | 0.79 |
| M4 RH+T+host† | 0.702 (0.641–0.760) | 0.180 | 0.104 | 0.537 | 0.00 | 0.83 |
| M5 tuned window | 0.610 (0.533–0.682) | 0.195 | 0.028 | 0.577 | −0.01 | 0.63 |
| M6 strict ≥5-d lead | 0.645 (0.556–0.729) | 0.189 | 0.059 | 0.564 | 0.00 | 0.84 |

\* An AUC below 0.5 for the prevalence-only model is a known artefact of leave-one-group-out: the prediction for a held-out year is the prevalence of the *other* years, which is lower when the held-out year itself has many events, so predictions anti-correlate with outcomes across folds.
† M4 uses the 995 rows with known corn residue.

Paired differences vs M1 (LOYO, year bootstrap): M2 ΔAUC −0.082 (−0.141 to −0.030); M3 −0.002 (−0.022 to 0.013); M5 −0.033 (−0.064 to −0.005); M6 +0.002 (−0.048 to 0.057); M0 ΔBrier +0.008 (−0.007 to 0.023); M4 vs M1 (same 995 rows) ΔAUC +0.059 (0.009–0.117), ΔBrier −0.012 (−0.020 to −0.004).

### Other validation schemes

| Model | LOSO AUC / Brier / slope | Temporal (≤2008 → 2009–15) AUC / Brier / intercept / slope | 10-fold by environment AUC | 10-fold by row AUC |
|---|---|---|---|---|
| M1 | 0.642 / 0.191 / 0.83 | 0.663 / 0.181 / −0.07 / 0.98 | 0.657 | 0.661 |
| M2 | 0.569 / 0.197 / 0.66 | 0.635 / 0.187 / −0.16 / 1.91 | 0.592 | 0.602 |
| M3 | 0.632 / 0.193 / 0.75 | 0.651 / 0.182 / −0.09 / 0.89 | — | — |
| M4 | 0.691 / 0.181 / 0.79 | 0.713 / 0.173 / 0.40 / 1.07 | — | — |
| M5 | 0.634 / 0.191 / 0.76 | 0.662 / 0.179 / −0.05 / 1.03 (chose RH7/T5) | — | — |
| M6 | 0.639 / 0.191 / 0.74 | 0.643 / 0.190 / −0.29 / 0.59 | — | — |

Ignoring clustering (row-level 10-fold) inflates M1's AUC by ~0.016 over LOYO and its calibration slope from 0.80 to 0.94, so random splitting would overstate performance and especially calibration.

### Heterogeneity across validation groups (M1)

* LOYO, years with ≥ 3 events and ≥ 3 non-events (15 years): median AUC 0.60, IQR 0.51–0.78, range 0.35–0.89. In 2013 (69 plots) and 2004 (77) the within-year AUC was below 0.5.
* Year-level calibration (`year_level_calibration_M1.png`): predicted year means span only 0.20–0.35 whereas observed prevalence spans 0.05–0.43 (years with ≥ 20 plots); the ordering is right (r = 0.83) but the range is compressed (e.g. 2012: predicted 0.20, observed 0.05; 2003: 0.31 vs 0.43).
* LOSO (11 states with enough of both classes): median AUC 0.64, range 0.54–0.83. State-level prevalence is poorly reproduced (r = 0.27): MO observed 0.63 vs predicted 0.26; PA 0.09 vs 0.35; NY and WI 0 events vs predicted ~0.22.
* M4 is more uniform: LOYO median year AUC 0.72 (IQR 0.63–0.78); LOSO median 0.73.

Calibration plots: `outputs/models/calibration_plots.png`. M1's predictions span roughly 0.1–0.5; deciles lie near the diagonal except the top decile (predicted ~0.50, observed ~0.36), i.e. the highest-risk predictions are too high, consistent with slope 0.80. M4 is the best calibrated across schemes, but in the temporal hold-out it underpredicts overall (intercept +0.40): 2009–2015 had more epidemics per unit of predicted risk than 1982–2008.

## 4. Predictor effects (full data, cluster-robust SEs by state-year)

| Model | Term | OR (95% CI, cluster-robust) | per | Naive SE / cluster SE |
|---|---|---|---|---|
| M1 | mean RH, d −10…0 | 2.21 (1.48–3.31) | +10 % RH | 0.011 / 0.021 |
| M1 | mean T, d −10…0 | 0.98 (0.89–1.09) | +1 °C | 0.028 / 0.053 |
| M2 | √hours 15–30 °C & RH ≥ 90%, d −10…0 | 1.18 (1.05–1.32) | +1 √h | 0.031 / 0.058 |
| M2 | mean T, d −10…0 | 0.93 (0.82–1.04) | +1 °C | |
| M3 | RH×T (centred) | 0.99 (0.98–1.01) | per %·°C | |
| M4 | mean RH | 2.07 (1.34–3.21) | +10 % RH | |
| M4 | mean T | 1.02 (0.92–1.14) | +1 °C | |
| M4 | resist S vs VS | 0.52 (0.34–0.81) | | |
| M4 | resist MS vs VS | 0.29 (0.16–0.55) | | |
| M4 | resist MR vs VS | 0.16 (0.08–0.31) | | |
| M4 | corn residue present | 2.08 (1.37–3.17) | | |
| M6 | h VPD ≤ 1.1 kPa, d −15…−5 | 1.21 (1.08–1.38) | +10 h | |
| M6 | mean T, d −20…−10 | 1.20 (1.08–1.35) | +1 °C | |

* Cluster-robust SEs are about twice the naive ones: the 999 rows carry much less independent information than their number suggests.
* Year-bootstrap (500 resamples): the RH coefficient in M1 was positive in 100% of resamples (2.5–97.5%: 0.033–0.135 per %RH); the T coefficient was positive in 39% (sign unstable). In M2 the duration term was positive in 98%.
* Estimation sensitivity (`coef_stability.csv`): weighting each environment equally leaves M1's RH coefficient unchanged (0.080 vs 0.079); a GEE with exchangeable correlation within state-years (working ρ ≈ 0.29) shrinks it to 0.023 (SE 0.019).
* *Exploratory* within/between decomposition (`exploratory_within_between.json`): log-OR per % RH between state-years 0.136 (SE 0.033); within state-years −0.019 (SE 0.026). Temperature: neither component distinguishable from 0.
* Temperature sign differs between models: null in M1 (days −10…0), positive in M6 (days −20…−10). With ρ(RH, T) small, this is not a collinearity artefact; it suggests either a genuine window-dependent effect or instability. It was not pre-specified as a hypothesis and is not interpreted causally.

Apparent (resubstitution) AUCs on the full data: M1 0.668, M2 0.611, M4 0.727, i.e. optimism relative to LOYO of 0.02–0.05.

## 5. Sensitivity analyses (LOYO)

| Analysis | AUC | Brier | Cal. slope |
|---|---|---|---|
| Threshold 5% (395 events): M1 / M2 | 0.623 / 0.555 | 0.233 / 0.241 | 0.72 / 0.35 |
| Threshold 15% (202 events): M1 / M2 | 0.634 / 0.562 | 0.157 / 0.163 | 0.77 / 0.41 |
| M1 window 5 / 7 / 10 / 14 / 15 d | 0.643 / 0.649 / 0.645 / 0.640 / 0.637 | 0.190–0.193 | 0.78–0.85 |
| M2 window 5 / 7 / 10 / 14 / 15 d | 0.577 / 0.570 / 0.561 / 0.554 / 0.552 | 0.198–0.200 | 0.37–0.58 |
| 12H (UTC "overnight") mean RH instead of 24H | 0.637 | 0.193 | 0.78 |
| M1 with restricted cubic splines (4 params) | 0.619 | 0.194 | 0.62 |
| M1 weighted 1/environment size | 0.647 | 0.192 | 0.82 |
| M1 / M2, years ≥ 1995 | 0.645 / 0.563 | 0.192 / 0.200 | 0.80 / 0.47 |
| RH only (1 term) | 0.653 | 0.191 | 0.87 |
| T only (1 term) | 0.452 | 0.202 | <0 |
| √TRH90 only (1 term) | 0.564 | 0.199 | 0.49 |
| Host only (resist + corn, no weather) | 0.649 | 0.185 | 0.88 |
| M2 + host | 0.665 | 0.187 | 0.76 |
| Random forest, all 174 pre-anthesis variables (supplementary) | 0.658 (0.571–0.746) | 0.189 | 0.66 |

* M1 is insensitive to window length (AUC 0.637–0.649), so the choice of a 10-day window does not matter much, and selecting the best-looking window would gain ≤ 0.004 apparent AUC while costing 0.035 when selection is validated honestly (M5).
* M5 picked RH 7 d / T 5 d in 26 of 32 folds, so the selection was fairly stable, yet it still validated worse than the fixed choice.
* Results are similar at the 5% and 15% thresholds; discrimination is somewhat lower at 5%.
* RF vs M1: ΔAUC +0.015 (−0.032 to 0.057); RF calibration slope 0.66 (overconfident). Its top impurity-importance variables are listed in `outputs/models/rf_top25_importance.csv`.

## 6. Final model under the pre-specified rule

Weather-only models within 0.02 AUC of the best (0.645): M1, M3, M6. Fewest parameters: M1 and M6 (2 each). Both have Brier within 0.005 of the best. Calibration slope in 0.8–1.2: M1 0.80 (at the boundary), M6 0.84. I keep **M1** as the primary weather-only model: it uses the exposure period closest to infection, and it held up better in the temporal hold-out (AUC 0.663, slope 0.98 vs 0.643 / 0.59 for M6). M6 is reported as the strict-timing equivalent; its LOYO performance shows that nothing is lost by using only information available ≥ 5 days before anthesis.

Final M1, fitted on all 999 plots:

  logit P(S ≥ 10%) = −6.32 + 0.0794 × RH̄(d −10…0, %) − 0.0155 × T̄(d −10…0, °C)

Against the plan's own criterion (AUC ≥ 0.65 and a clear Brier gain over prevalence), **M1 does not qualify as a reliable stand-alone predictor.** The weather information in this dataset supports only weak, season-level risk ranking. The more useful applied model is M4 (weather + resistance + residue), which also exceeds the bar under every validation scheme:

  logit P = −5.94 + 0.0729 × RH̄ + 0.0224 × T̄ − 0.645 [S] − 1.224 [MS] − 1.852 [MR] + 0.733 × corn

(reference: very susceptible cultivar, no corn residue).
