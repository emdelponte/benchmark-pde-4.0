# Results — parsimonious pre-anthesis weather model for FHB epidemic risk

All numbers are reproducible with `code/10_models.py` … `code/15_decision.py`.
Machine-readable outputs are in `outputs/*.csv` and `outputs/*.txt`; figures in
`outputs/figures/`.

> **Timing statement (applies to every model below).** Predictors are restricted to
> windows ending at anthesis (`window_end_day ≤ 0`). No post-anthesis variable is used
> anywhere. The anthesis-day weather itself is included in the exposure window — this is
> an end-of-anthesis-day assessment (see `critical_assessment.md` §2).

---

## 1. Analysis sample and outcome

| Quantity | Value |
|---|---|
| Plots | 999 |
| Binary outcome `EPI = 1{S ≥ 5%}` | **395 events** / 604 non-events (39.5%) |
| Distinct weather records | 545 (719 plots share a record with ≥1 other plot) |
| Trials (state × year × anthesis date) | 492 |
| Environments with ≥1 case | 221 |
| States / years | 17 / 32 |

The prevalence of 39.5% is the operating point for every result below; Brier scores are
therefore compared against the prevalence-only reference value 0.2391.

---

## 2. Primary model (M2): estimates

Logistic regression, maximum likelihood, **2 estimated non-intercept parameters** (both
weather; no interactions, no nonlinear terms). Standard errors are cluster-robust by
weather record (545 clusters).

| Term (unit) | β | robust SE | z | p | OR | 95% CI |
|---|---|---|---|---|---|---|
| Intercept | −0.820 | 0.162 | −5.06 | <0.001 | — | — |
| Hours with RH ≥ 90%, −7…0 d pre-anthesis (per +10 h) | 0.121 | 0.032 | 3.78 | 0.0002 | **1.129** | 1.060–1.202 |
| Hours with T > 30 °C, −7…0 d pre-anthesis (per +10 h) | −0.102 | 0.158 | −0.65 | 0.52 | 0.903 | 0.663–1.230 |

Log-likelihood −655.41, AIC 1316.8, McFadden pseudo-R² 0.022, n = 999.

**Interpretation of the primary model.** The wetness term behaves as predicted: each
additional 10 h of near-saturated air in the week before anthesis raises the odds of an
epidemic by ~13% (≈34% per full 24 h). The heat-stress term is **null** (OR 0.90, CI
0.66–1.23). The pre-specified temperature hypothesis is therefore **not supported** in the
binary model, and M2 is effectively a one-term model that happens to carry a second
nuisance parameter.

**Effect magnitudes are modest, not decisive.** Moving from 5 h to 80 h of RH ≥ 90% in the
window moves the predicted probability only from 0.32 to 0.54 (at zero heat hours); the
full model output range over the observed data is 0.19–0.73.

---

## 3. Alternative specifications

| ID | Specification | Weather params | Agronomic params | Apparent AUC | McFadden R² |
|---|---|---|---|---|---|
| M0 | prevalence only | 0 | 0 | 0.500 | 0 |
| M1 | RH ≥ 90 h only | 1 | 0 | 0.606 | 0.022 |
| **M2** | **RH ≥ 90 h + T > 30 h (primary)** | **2** | **0** | **0.608** | **0.022** |
| M3 | M2 + mean temperature | 3 | 0 | 0.619 | 0.027 |
| M4 | M2 + resistance class + corn residue | 2 | 2 | 0.690 | 0.085 |
| M5 | warm–wet hours (9–30 °C & RH ≥ 80%) + T > 30 h | 2 | 0 | 0.629 | 0.037 |
| M6 | M2 + quadratic in wetness | 3 | 0 | 0.606 | 0.025 |
| M7 | ridge logistic on M3 predictors | 3 | 0 | 0.620 | — |

Selected coefficients (full table in `outputs/model_estimates.csv`):

* **M3:** mean temperature OR **1.072 per °C** (95% CI 0.999–1.149, p = 0.052); wetness
  OR 1.139 per 10 h (p = 0.0001); heat OR 0.765 (p = 0.13). Adding mean T raises the
  apparent AUC by 0.011 only.
* **M4 (agronomic):** resistance **OR 0.594 per class step** toward more resistant
  cultivars (0.510–0.692, p < 0.001); corn residue **OR 2.47** (1.81–3.36, p < 0.001);
  wetness OR 1.095 per 10 h (1.021–1.174, p = 0.011); heat again null. Agronomy is by far
  the strongest signal in the dataset.
* **M5:** warm–wet hours **OR 1.146 per 10 h** (1.087–1.208, p < 0.001); heat null.
* **M6:** quadratic wetness term −0.012 (SE 0.008, p = 0.16) → **no evidence of
  nonlinearity**; the linear-in-logit form is adequate.
* Collinearity of the primary terms is mild (VIF 1.11 and 1.42 in M3; Pearson r = 0.85
  between the two moisture metrics used in different models, which is why they are never
  in the same model).
* **Likelihood comparison:** AIC prefers the one-term model M1 over the pre-specified M2
  (1315.5 vs 1316.8). The likelihood-ratio test for adding the heat term is
  χ²₁ = 0.70, p = 0.40. The second parameter of the primary model is therefore not earning
  its place, which is stated here rather than fixed by dropping it after the fact.

---

## 4. Validation (grouped; all estimation inside training folds)

Three schemes: **LOYO** = leave-one-year-out (32 folds, temporal transportability,
primary); **LOSO** = leave-one-state-out (17 folds, spatial); **K5** = five chronological
blocks of years. Intervals are 95% cluster bootstrap percentile intervals resampling whole
weather records (1000 replicates) — not naive binomial intervals.

| Model | Params | LOYO AUC [95% CI] | LOSO AUC | K5 AUC | LOYO Brier | Calib. intercept | Calib. slope |
|---|---|---|---|---|---|---|---|
| M0 prevalence | 0 | 0.355 [0.312, 0.401]¹ | 0.368 | 0.460 | 0.242 | — | — |
| M1 | 1 | 0.569 [0.522, 0.614] | 0.577 | 0.593 | 0.237 | −0.13 | 0.68 |
| **M2 (primary)** | **2** | **0.560 [0.514, 0.605]** | **0.577** | **0.584** | **0.238** | **−0.20** | **0.52** |
| M3 | 3 | 0.563 [0.516, 0.610] | 0.591 | 0.583 | 0.240 | −0.24 | 0.42 |
| M4 | 4 (2+2) | 0.659 [0.624, 0.696] | 0.661 | 0.670 | 0.220 | −0.06 | 0.84 |
| M5 | 2 | 0.598 [0.550, 0.646] | 0.605 | 0.615 | 0.233 | −0.11 | 0.74 |
| M6 | 3 | 0.557 [0.512, 0.603] | 0.560 | 0.582 | 0.240 | −0.23 | 0.44 |
| M7 ridge | 3 | 0.576 [0.529, 0.621] | 0.589 | 0.589 | 0.238 | −0.18 | 0.57 |

¹ The M0 LOYO "AUC" of 0.355 is **not** a model failure: leave-one-year-out forces the
constant prediction for a held-out year to be the mean of the *other* years, which
anti-correlates with a high-prevalence year (a high-prevalence year is partly removed from
its own training mean). It illustrates how much of the pooled AUC is driven by
between-year prevalence differences. On the equivalent Brier scale M0 = 0.242.

**Optimism (apparent − LOYO AUC):** M2 0.048, M5 0.031, M4 0.031, M1 0.038, M7 0.044.
The 4-parameter agronomic model is the *least* optimistic, because its signal is plot-level
and does not depend on between-year extrapolation.

**Per-fold fragility.** Only 23 of 32 LOYO folds have both outcome classes; 17 of 32 folds
contain <5 events, so per-fold AUC ranges from 0.00 to 1.00 for reasons that are mostly
binomial noise. Fold medians: M2 0.527, M5 0.577, M4 0.650 (figure 4).
**Headline conclusion from validation: the weather-only models reach AUC ≈ 0.56–0.62, i.e.
better than chance but far from a usable triage tool; adding cultivar resistance and corn
residue raises it to ≈ 0.66.**

### Calibration (LOYO OOF, deciles of predicted risk — figure 3)
* M2: intercept −0.20, slope 0.52 → predictions are **too extreme** (over-dispersed) and
  cover only 0.19–0.73; the model cannot express "high risk".
* M5: intercept −0.11, slope 0.74.
* M4: intercept −0.06, slope 0.84 → nearly acceptable calibration.
* Brier scores fall from 0.242 (prevalence) to 0.238 (M2), 0.233 (M5), 0.220 (M4), i.e.
  a Brier skill score of only 0.005 (M2), 0.026 (M5) and 0.08 (M4) relative to always
  predicting the base rate.

---

## 5. Where the weather signal lives: between years or within years?

This analysis was added after the plan (documented in `analysis_log.md`), because
year-to-year contrast and plot-to-plot contrast answer different questions.

| Model | Pooled AUC | Median AUC **within** held-out year | AUC across the 32 **year means** |
|---|---|---|---|
| M1 | 0.569 | 0.538 | 0.679 |
| M2 | 0.560 | 0.527 | 0.641 |
| M5 | 0.598 | 0.577 | **0.718** |
| M4 | 0.659 | **0.650** | 0.654 |

* Weather-only models discriminate **years** (0.64–0.72) much better than **plots within a
  year** (0.53–0.58). Pre-anthesis weather mostly indexes whether a season was an "FHB
  year"; conditional on the year, it adds little.
* The agronomic model is the mirror image: it works within years (resistance and residue
  vary among plots), and roughly equally between years.
* This is **the** central result for interpretation: a weather-based risk model of this
  dataset is essentially a *season-level* risk index, not a *plot-level* classifier.
* Within-year AUCs are not merely noisy, they sometimes **reverse**: M4 scores 0.00 within
  the 4-plot 1994 and 6-plot 1995 years, and M5 scores 0.00 in 1999 and 0.16 in 2008. In
  small years the ordering is actively misleading, which is one more reason not to use the
  model at trial scale without local recalibration.

---

## 6. Sensitivity analyses (all OOF, LOYO unless stated; intervals from 600 cluster-bootstrap
replicates, so they differ in the third decimal from the 1000-replicate intervals in §4)

| Analysis | n | Events | OOF AUC [95% CI] | Brier |
|---|---|---|---|---|
| **Reference: M2, EPI = S ≥ 5%** | 999 | 395 | 0.560 [0.514, 0.608] | 0.238 |
| S1 cut-point S ≥ 1% | 999 | 635 | 0.575 [0.526, 0.623] | 0.230 |
| S1 cut-point S ≥ 10% | 999 | 273 | 0.616 [0.567, 0.664] | 0.194 |
| S1 cut-point S ≥ 20% | 999 | 156 | 0.638 [0.583, 0.694] | 0.129 |
| S2 window −5…0 d (6 d), M5 concepts | 999 | 395 | 0.609 [0.565, 0.654] | — |
| S2 window −7…0 d (8 d), M5 concepts | 999 | 395 | 0.598 [0.553, 0.648] | — |
| S2 window −10…0 d (11 d) | 999 | 395 | 0.588 [0.540, 0.636] | — |
| S2 window −14…0 d (15 d) | 999 | 395 | 0.602 [0.551, 0.653] | — |
| S2 window −15…0 d (16 d) | 999 | 395 | 0.609 [0.556, 0.662] | — |
| S2 window −20…0 d (21 d), RH ≥ 90 h concept | 999 | 395 | 0.551 [0.505, 0.595] | — |
| S2c single moisture metric: RH ≥ 90 h | 999 | 395 | 0.569 [0.523, 0.614] | 0.237 |
| S2c single moisture metric: mean RH | 999 | 395 | **0.635 [0.585, 0.685]** | 0.228 (slope 0.86) |
| S2c single moisture metric: warm–wet hours | 999 | 395 | 0.607 [0.562, 0.657] | 0.232 |
| S4 12-h "overnight" RH ≥ 90 h | 999 | 395 | 0.559 [0.515, 0.606] | 0.237 |
| S5 drop all-zero (disease-free) years | 989 | 395 | 0.560 [0.512, 0.599] | 0.239 |
| S6 exclude 2009 | 832 | 322 | **0.498 [0.453, 0.550]** | 0.241 |

Key readings:

1. **Threshold dependence is real but bounded.** Discrimination improves as the epidemic
   definition becomes stricter (0.56 at 5% → 0.64 at 20%); the pragmatic "any disease"
   cut-point (1%) is the worst. Weather describes *severe* seasons best.
2. **Window choice is not identifiable.** All windows between −5 and −15 d give
   AUC 0.59–0.61 with overlapping intervals; the 21-day window is worse (0.55). No
   sharp "critical period" can be established from these data.
3. **The moisture metric matters more than the window.** Mean RH (0.635) and warm–wet
   hours (0.607) outperform the RH ≥ 90 h count (0.569). This ranking was *not* used to
   choose the primary model (the plan fixed M2 in advance) but it is consistent across
   schemes and is the clearest candidate for a better-specified model in future data.
4. **The 12-h "overnight" moisture variable is no better and slightly worse than the 24-h
   version** (0.559 vs 0.569), consistent with the audit's finding that the "overnight"
   window is misaligned with local night-time by ~6 h.
5. **The result is fragile to one year.** Excluding 2009 (167 plots, 17% of the data)
   destroys out-of-fold discrimination (0.498). The epidemic contrast in 2009, when many
   wet plots were observed, carries much of the pooled signal.
6. **Continuous-outcome check (S8)**: fractional logit on S/100 gives wetness OR **1.115
   per 10 h** (p = 1.1 × 10⁻⁶) and heat-hours OR **0.70 per 10 h** (p = 0.015). In the
   continuous model the heat term *is* negative and significant — heat/drought suppresses
   severity, but not enough to move plots across a 5% binary boundary. The binary result is
   therefore not an artefact of binning; it is a power issue.
7. **Stability.** Delete-one-trial jackknife: M2 coefficients range 0.115–0.131
   (wetness) and −0.167 to −0.070 (heat) with **no sign flips**; M5 similar. Cluster-level
   (545 weather-group) fractional logit: wetness +0.113 (p = 0.0009), heat −0.125
   (p = 0.43) — signs preserved.
8. **M4 missingness:** coding the 4 missing `corn` values as 0 changes coefficients by
   <0.03; results are not missingness-driven.

---

## 7. Confounding: does the weather effect survive year and state effects?

Explanatory models with nuisance fixed effects (GLM binomial, cluster-robust SE). These are
**not** prediction models — they exceed the parameter budget on purpose, to test whether the
weather coefficient is an artefact of year or state.

| Exposure | Unadjusted | + year FE | + state FE | + both |
|---|---|---|---|---|
| warm–wet hours (per 10 h) | +0.139 (p = 5×10⁻⁸) | +0.099 (p = 0.0005) | +0.151 (p = 1×10⁻⁶) | +0.106 (p = 0.001) |
| mean RH (per %) | +0.067 (p = 3×10⁻⁹) | +0.050 (p = 4×10⁻⁵) | +0.073 (p = 1×10⁻⁷) | +0.054 (p = 0.0001) |
| RH ≥ 90 h (per 10 h) | +0.121 (p = 0.0002) | +0.087 (p = 0.013) | +0.157 (p = 0.0001) | +0.110 (p = 0.009) |

The association is **attenuated by ~25–30% but remains** after absorbing year and state
effects: it is not purely a between-year artefact. Dropping 2009 attenuates but does not
remove it (warm–wet OR per SD 1.59 → 1.45; mean RH 1.73 → 1.59). Variance decomposition
shows only 14–15% of weather variance is between years and 14–24% between states, so the
signal is mostly within-year/within-state — yet the *pooled ranking* still depends heavily
on the largest year (S6). Both statements are true and are reconciled by §5: the model ranks
years well and plots within years poorly.

Ecological correlations are modest: year-level r = 0.19 (warm–wet), 0.22 (mean RH); trial
level r = 0.24–0.27.

---

## 8. What the model would do in use (LOYO OOF, decision thresholds)

| Model | Cut-off | % flagged | Sensitivity | Specificity | PPV | NPV |
|---|---|---|---|---|---|---|
| M2 | 0.50 | 10.3% | 0.12 | 0.91 | 0.47 | 0.61 |
| M5 | 0.50 | 16.5% | 0.21 | 0.86 | 0.50 | 0.63 |
| M4 | 0.50 | 24.7% | 0.37 | 0.83 | 0.58 | 0.67 |
| M4 | 0.60 | 12.6% | 0.22 | 0.93 | 0.67 | 0.65 |

To capture ≈47% of epidemics with M2 one must flag ~39% of all plots (cut-off 0.40), at
which point the positive predictive value is 0.48 — barely above the 39.5% base rate. **In
decision terms the weather-only model is close to useless as a plot-level screener.**

---

## 9. Answer to the scientific question

1. **Pre-anthesis weather carries real but weak information about FHB epidemic risk in
   this dataset.** The most consistent predictor is atmospheric moisture in the week(s)
   before anthesis (RH-based, positive, OR ≈ 1.1–1.15 per 10 h of high-RH hours, or
   OR ≈ 1.7 per SD of mean RH), robust to clustering, year/state fixed effects and the
   choice of outcome threshold. Heat hours (>30 °C) are negative but only detectable with
   the continuous outcome.
2. **A two-parameter pre-anthesis weather model is not a reliable predictive tool**
   (LOYO AUC 0.56 [0.51, 0.61]; Brier skill 0.005; calibration slope 0.52; sensitivity 0.12
   at a 0.5 cut-off). The data support a *season-level risk index*, not plot-level triage.
3. **Adding two agronomic terms available at anthesis (cultivar resistance class, corn
   residue) improves discrimination to AUC 0.66 [0.62, 0.70] and gives acceptable
   calibration (slope 0.84), while keeping the weather parameter count at two.** This is the
   most defensible predictive specification in the data, and it shows that most of the
   *predictable* plot-level variation is agronomic, not weather.
4. **No evidence supports more complexity**: a third weather term (mean T), a quadratic
   term or ridge penalisation changes LOYO AUC by ≤ 0.02 and worsens calibration. The
   parsimonious choice is vindicated, but the reason is that there is little signal to
   capture, not that the model is optimal.
5. **The "overnight" 12-h block should not be used** for inference; the UTC labelling makes
   it biologically misaligned.

Figures: `fig1_outcome.png` (outcome distribution), `fig2_roc.png` (LOYO ROC),
`fig3_calibration.png` (calibration), `fig4_fold_auc.png` (year-to-year instability),
`fig5_complexity.png` (AUC vs parameter count).

---

*Post hoc note added after the literature search (not part of the independent analysis).*
The associated publications define the binary outcome as **FHB index ≥ 10%**, and that rule
reproduces exactly 273 events / 726 non-events of the 999 plots — see
`comparison_with_literature.md` §2. At that threshold the same models score LOYO AUC 0.616
(M2), 0.639 (M5), 0.689 (M4) and 0.719 (mean RH + resistance + corn). Nothing above is
changed: the pre-registered outcome was 5% and remains so, and the 10% figures are an
explicitly post-hoc alignment for comparison with published work.
