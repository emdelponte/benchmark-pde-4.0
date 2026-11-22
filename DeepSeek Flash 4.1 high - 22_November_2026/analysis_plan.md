# Analysis plan — parsimonious pre-anthesis weather model for FHB epidemic risk

**Status: written before any model fitting.** Model estimates were produced only after this
file was committed (`git`-less workspace; the file mtime precedes every run in
`outputs/`). Any later deviation is recorded in §12 "Revisions" and in `analysis_log.md`,
not by editing the original plan.

---

## 1. Prediction target and intended use

* **Target.** A binary indicator of an FHB epidemic in a fungicide-untreated wheat plot:

  > `EPI = 1` if the plot's FHB index `S ≥ 5.0%` (on the documented 0–100% severity scale),
  > else `EPI = 0`.

* **Why 5%.** (i) The release documents **no** binary outcome and **no** cut-point
  (`data_audit.md` §3), so the definition is mine and is stated here, before fitting.
  (ii) 5% is the smallest FHB index at which USWBSI trial reports and extension guidance
  treat losses as agronomically meaningful, and it sits above the zero-inflated 0–1%
  region (18.6% of plots are exactly 0 and 63% are ≤ 1%), so it distinguishes *epidemic*
  from *trace* disease rather than splitting noise. (iii) It yields 393 events / 606
  non-events (39.3% prevalence), which supports 3–5 estimated parameters without relying
  on a universal events-per-variable rule; 10% (271 events) and 1% (633 events) are used
  as sensitivity cut-points.
* **Intended use.** A pre-season-to-anthesis risk *triage*: at (or at the end of) anthesis,
  flag plots/environments with high probability of a damaging epidemic, to inform
  post-anthesis scouting intensity, fungicide decisions on later-flowering tillers, and
  harvest/grain-quality planning. It is **not** a within-season spray-timing model and
  **not** a field-level decision tool for growers: the weather source is a weather station
  up to several km away and cultivar/site effects are only partly captured.
* **Unit of prediction.** The plot. Predictions are made from weather that is common to
  all plots of a trial, plus plot-level cultivar resistance and corn-residue history.

## 2. Response definition and timing constraints

* Primary response: `EPI` as defined above.
* **Only predictors with `window_end_day ≤ 0`** (information available by the end of the
  anthesis day) enter any model. All 155 post-anthesis / `pre-post` variables are excluded,
  as are `T.A.4`, `T.A.5`, `RH.A.2`, every `POST*` column, and `INT3`.
* Residual caveat accepted and reported: a window ending at day 0 includes the anthesis
  day's own weather, and the release contains no day-0-free moisture aggregation. The model
  is therefore an *end-of-anthesis-day* assessment. This is stated in every results table
  header and in `critical_assessment.md`.
* I use the **24-h** rather than the "overnight" 12-h variables for moisture, because the
  release's UTC timestamps are unadjusted local dates and the "overnight" 20–08 UTC block
  is actually ~14:00–02:00 local time (`data_audit.md` §4.2). A 12-h sensitivity model is
  fitted to document this.

## 3. Candidate weather variables and exposure windows

The 174 pre-anthesis variables are not 174 independent hypotheses; they are ~49 condition
families × 5–8 nested windows, with within-family correlations of 0.9–0.99. I therefore
pre-specify **concepts**, one representative variable per concept, in a **−7…0 d window**
(8 calendar days, 192 h; the release's "7 d" label):

| Concept | Variable (as released) | Biological rationale |
|---|---|---|
| **Wetness duration** (primary moisture axis) | `RH907` — No. h with RH ≥ 90%, −7…0 d, 24-h | Free moisture / near-saturation drives *Fusarium graminearum* conidial germination, perithecial maturation on residue and ascospore release; the 7–10 d before anthesis determines the inoculum load available when spikes are susceptible. |
| **Heat stress** (primary temperature axis) | `T.G30.PRE7.24H` — No. h with T > 30 °C, −7…0 d, 24-h | FHB infection and sporulation are suppressed above ~30 °C; heat/drought in the pre-anthesis week should reduce, not increase, risk. This is the only temperature family with a non-null marginal signal. |
| Mean temperature (linear) | `T.A.PRE7.24H` — mean daily T, −7…0 d | Standard thermal covariate; expected weak because the whole dataset spans a narrow warm-season range. |
| Mean RH | `RH7` — mean daily RH, −7…0 d | Alternative moisture metric (smoother, less threshold-dependent). |
| Combined warm–wet hours | `TRH.9T30nRHG80.PRE7.24H` — No. h with 9 ≤ T ≤ 30 °C and RH ≥ 80%, −7…0 d | Single term that encodes "conducive hour" = warm enough *and* humid enough; reduces a 2-term model to 1 parameter. |
| Mean VPD | `VPD.A.1` — mean daily VPD, −10…0 d (closest available; no −7…0 24-h version) | Continuous atmospheric drying demand; inverse of RH. |

Agronomic covariates available at anthesis and considered as *optional* terms:
`resist` (ordinal VS < S < MS < MR, scored 0–3) and `corn` (0/1 corn residue).

**Explicitly excluded a priori:** all pressure variables (no plausible mechanism at these
windows), all `MINMAXDIFF` and `SD` variables (diurnal range/variability — a weaker,
second-order proxy for wetness, and highly collinear with the mean), all `T < 9 / T < 15 /
T ≥ 15` counts (complements of each other; r = −1.00), and every variable whose window ends
before −20 d (too distal to anthesis to matter mechanistically and likely to be confounded
with macro-climate).

## 4. Transformations and aggregations

* No new weather summaries are constructed; the released aggregates are used as-is so the
  analysis stays reproducible from the published columns.
* Hour-count variables are used **per day** (`hours / 8` for the −7…0 window) in the
  window-sensitivity analysis, so that 5-, 7-, 10-, 20-day windows are comparable; in the
  primary model they are used as raw counts (equivalent up to a scale factor).
* No standardisation for unpenalised MLE (coefficients are reported per 10 h for counts and
  per 1 °C for temperatures). For the ridge sensitivity, predictors are standardised
  **inside each training fold**.
* No nonlinear terms in the primary model. One pre-specified nonlinearity check (quadratic
  in wetness hours) is run as an alternative specification with its parameter count reported.

## 5. Collinearity control

* One variable per *concept*, and one concept per *moisture axis*: never two of
  {`RH907`, `RH7`, `TRH.9T30nRHG80.PRE7.24H`, `VPD.A.1`} in the same model.
* Before fitting, the environment-level Spearman correlation matrix of the chosen terms is
  reported (`outputs/model_correlations.csv`); any pair with |r| > 0.8 is disallowed.
  Expected: `RH907` vs `RH7` ≈ 0.85 (so they are alternative, never joint, terms);
  `RH907` vs `T.G30` ≈ −0.32; `T.A.PRE7.24H` vs `T.G30` ≈ 0.57.
* Variance inflation factors are reported for the 3-term model as a diagnostic, not as an
  automatic deletion rule.
* `resist` and `corn` are retained jointly in the agronomic model (they are unrelated to
  each other at |r| < 0.3).

## 6. Model-building and complexity control

All models are logistic regressions with a logit link, fitted by maximum likelihood
(statsmodels `Logit`). **Model set is fixed in advance; no stepwise, no
AIC-driven search over the 174 candidates, no automated exposure-window search.**

| ID | Specification | Estimated non-intercept parameters (weather / agronomic) |
|---|---|---|
| **M0** | intercept only (prevalence baseline) | 0 / 0 |
| **M1** | wetness only: `RH907` | 1 / 0 |
| **M2 (PRIMARY)** | `RH907` + `T.G30.PRE7.24H` | 2 / 0 |
| **M3** | M2 + `T.A.PRE7.24H` | 3 / 0 |
| **M4** | M2 + `resist` + `corn` | 2 / 2 |
| **M5** | alternative moisture concept: `TRH.9T30nRHG80.PRE7.24H` + `T.G30.PRE7.24H` | 2 / 0 |
| **M6** | M2 + quadratic `RH907²` (centred) | 3 / 0 |
| **M7** | ridge (L2) logistic on the M3 predictors, penalty chosen by inner 5-fold CV grouped by year | 3 / 0 |

**Why M2 is primary.** It is the smallest model that represents the two mechanistically
distinct drivers of pre-anthesis epidemic potential — inoculum/weather-driven wetness
(`RH907`) and heat limitation (`T.G30`) — while keeping the parameter count at 2 for
393 events / 221 case-environments. It is fixed *before* seeing any validation result and
will not be replaced by whichever model happens to score best (see §9).

**Events-per-parameter reasoning.** 393 events / 606 non-events gives ≈200 events per
parameter for M2 at the plot level — meaningless as a guarantee because plots are not
independent. Using the effectively independent units: 545 distinct weather records and
221 environments containing ≥1 case. Two weather parameters use ≈1% of the informative
environment count. The agronomic model M4 adds 2 parameters that describe plot-level
(cultivar/residue) variation, which is genuinely plot-level information, so it is not
double-counted. A universal 10-EPV rule is *not* invoked: it would license ~39 parameters,
which the collinearity and clustering structure plainly cannot support, and it is
irrelevant in the other direction because the limiting factor here is *weather-record*
diversity (~545), not raw event count.

## 7. Validation design

Grouping structure, not rows, defines the folds. All preprocessing (standardisation,
penalty selection) is fitted inside training folds only.

1. **Primary: leave-one-year-out (LOYO), 32 folds.** Tests transportability to unseen
   epidemic years — the operational scenario (next season). All plots of a year are held
   out together, so shared weather and shared epidemic conditions cannot leak.
   Caveat: 15 years have <10 plots and 6 years have a single plot, so per-fold AUC is
   undefined or extremely noisy in those folds. Per-fold metrics are therefore reported
   with their denominators and are *not* pooled as if equal.
2. **Secondary: leave-one-state-out (LOSO), 17 folds.** Tests spatial transportability.
   Caveat: states are confounded with year (OH is mostly 1982–2014, IL only 2009–2015,
   ND 1993–2015), and AR/DE/MN/WI have ≤33 plots, so LOSO mixes "new geography" with
   "different period".
3. **Tertiary: 5-fold grouped CV with years as groups** (years allocated to folds in
   chronological blocks) — a lower-variance check that the LOYO result is not an artefact
   of fold fragmentation. Not used for selection.
4. **Apparent (in-sample) performance** is reported alongside, purely to quantify optimism.

No random plot-level split is used anywhere.

## 8. Metrics and estimands

* **Discrimination:** ROC AUC on pooled out-of-fold (OOF) predictions; per-fold AUC
  distribution where estimable. 95% CI by **cluster bootstrap resampling weather groups**
  (545 groups), 2000 replicates — not the naive binomial CI, which would be too narrow.
* **Overall accuracy / loss:** Brier score (pooled OOF) with the prevalence-only Brier
  (0.393 × 0.607 = 0.2386) as the reference; Brier skill score.
* **Calibration:** calibration intercept (calibration-in-the-large) and slope from
  regressing `EPI` on the OOF linear predictor; decile calibration plot (observed vs
  predicted) with 95% Wilson intervals; a smoothed calibration curve.
* **Effects and uncertainty (for explanation, not prediction):** odds ratios per 10 h (or
  per 1 °C) with 95% CIs from **cluster-robust (by weather group) sandwich variances**, plus
  a delete-one-environment jackknife for stability. Wald p-values are reported but treated
  as descriptive given the observational design.
* **Complexity comparison:** AUC and Brier as a function of estimated parameter count,
  with the optimism gap (apparent − OOF) for each model.

## 9. Decision rules fixed in advance

* The **primary model is M2**, whatever its rank in AUC. If another specification beats it
  by >0.02 OOF AUC, that is reported as an exploratory finding, not adopted.
* The final claim will be about *predictive performance and effect direction*, not about
  causation.
* If the OOF AUC of M2 is within ~0.03 of 0.5 (the prevalence baseline) or its cluster-bootstrap
  CI includes 0.5, the conclusion will be that pre-anthesis weather alone does not support
  a reliable predictive model — stated explicitly rather than hidden.

## 10. Sensitivity analyses (planned)

| # | Perturbation | Purpose |
|---|---|---|
| S1 | Outcome cut-points 1%, 10%, 20% (refit M2, LOYO) | Threshold dependence of the "epidemic" definition |
| S2 | Exposure window −5…0, −10…0, −15…0, −20…0 (refit M2 analog) | Window-definition sensitivity |
| S3 | Hour counts expressed per day | Removes the 8-day-vs-7-day labelling artefact |
| S4 | 12-h "overnight" moisture instead of 24-h | Documents the UTC/local misalignment effect |
| S5 | Drop the all-zero-year cohort (1982–1989, 2007) | Influence of long disease-free period |
| S6 | Exclude 2009 (167 plots, 17% of data) | Influence of the single largest year |
| S7 | Delete-one-environment jackknife on M2 coefficients | Stability under clustering |
| S8 | Continuous-outcome check: fractional logit / linear model on logit(S/100) for M2 predictors | Confirms the binary story is not an artefact of binning |
| S9 | Ridge-penalised M3 (M7) vs MLE M3 | Overfitting check on the 3-parameter model |
| S10 | Corn-complete subset (n = 995) for M4 | Missingness check on `corn` |

## 11. What would change my mind

* OOF AUC ≈ 0.5 with a bootstrap CI covering 0.5 → weather-only model is not usable.
* Calibration slope far from 1 on OOF predictions → the fitted probabilities are not
  transportable even if ranking is acceptable.
* A sign reversal of `RH907` or `T.G30` between plot-level and environment-level fits →
  the effect is confounded by environment and should not be interpreted biologically.

## 12. Revisions

*None at the time of the first model fit. The entries below were appended afterwards, in
order, and nothing above was rewritten.*

**R1 (numeric clarification, after the first fit).** The plan defines
`EPI = 1` if `S ≥ 5.0%`. The audit's threshold table (§3 of `data_audit.md`) was computed
with a strict `S > x`, which gives 393 events at 5%; the plan's `≥` gives **395 events /
604 non-events (39.5%)**. All model results use 395 events. No analysis changed; the
discrepancy is a convention mismatch between two tables.

**R2 (exposure-window ladder, during S2).** The 24-h `RH ≥ 90%` hour count exists only for
the −7…0 d and −20…0 d windows in this release, not for −5, −10, −14 or −15 d. The window
ladder (S2) was therefore run on the *warm–wet hours* concept, which exists for every
window from −5 to −15 d, and the −20…0 d point uses the RH ≥ 90 h concept (flagged in the
results table). This is a forced substitution, not a choice.

**R3 (added analyses, after the planned ones).** Three analyses were added after the
pre-specified set, and are labelled as exploratory wherever reported:
(i) within-year vs between-year discrimination (§5 of `results.md`);
(ii) explanatory models with year and/or state fixed effects to test whether the weather
coefficient is confounded (`code/13_confounding.py`);
(iii) the single-metric moisture comparison (`S2c`: RH ≥ 90 h vs mean RH vs warm–wet
hours).
None of them was used to change the primary model.

**R4 (decision-rule consequence).** The pre-specified rule in §9 was: if another
specification beats M2 by > 0.02 OOF AUC, report it as exploratory but do not adopt it.
**M5 (warm–wet hours + heat hours) beats M2 in all three validation schemes**
(LOYO 0.598 vs 0.560; LOSO 0.605 vs 0.577; K5 0.615 vs 0.584). Per the rule, M2 remains the
primary model and M5 is reported as the better-performing pre-specified alternative.
The heat-stress term in M2 turned out to be null (OR 0.90, p = 0.52), so M2 is in practice
a one-informative-term model. This is reported as a negative result, not silently patched.

**R5 (post hoc observation, explicitly not adopted).** In S2c, a *single* mean-RH term
achieved the highest weather-only LOYO AUC of the whole analysis (0.635, 95% CI
0.585–0.685) with the best weather-only calibration slope (0.86). Because it was compared
after the primary model was fixed, and because its CI overlaps those of M5 and M2, it is
reported only as an exploratory finding and a hypothesis for future data.

