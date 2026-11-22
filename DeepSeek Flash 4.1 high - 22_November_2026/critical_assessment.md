# Critical assessment

*Written after the independent analysis was complete and before the literature search
(see `comparison_with_literature.md` for what changed afterwards).*

---

## 1. Strengths of the workflow

1. **The audit was allowed to change the analysis.** Three findings from `data_audit.md`
   directly shaped the models: (i) there is no documented binary outcome, so the outcome had
   to be defined a priori; (ii) the "overnight" 12-h block is misaligned with local night by
   ~6 h, so 24-h moisture variables were preferred; (iii) effective sample size is ~545
   weather records, not 999 plots, so the parameter budget was set by weather-record
   diversity, not by the events-per-variable rule.
2. **Nothing was tuned on the validation folds.** The eight specifications were fixed in
   `analysis_plan.md` before fitting; all centring, standardisation and the ridge penalty
   were fitted inside training folds; the primary model was not swapped for a better-scoring
   one (see `analysis_plan.md` R4).
3. **Validation respects the dependence structure**: leave-one-year-out, leave-one-state-out
   and chronological 5-fold blocks, with cluster-bootstrap intervals that resample whole
   weather records. The optimism gap is reported for every model.
4. **The negative result is reported as a negative result.** The pre-specified heat-stress
   term is null; the pre-specified primary model is beaten by a pre-specified alternative;
   the weather-only model is nearly useless at a decision threshold. All three are stated
   rather than buried.
5. **The analysis distinguishes *where* the signal is** (between years, not within years),
   which changes what the model can honestly be used for.

## 2. Weaknesses and threats to validity

### 2.1 The outcome is my construction, not the dataset's
The release documents only continuous FHB index `S`. My `S ≥ 5%` cut-point is defensible
but not canonical, and it materially affects performance (AUC 0.56 at 5%, 0.64 at 20%).
A different analyst with a 10% or 1% rule would report a different model "quality" from the
same data. This is the single largest source of analyst discretion in the whole exercise,
and it is a documentation failure of the release rather than of the analysis.

### 2.2 The timing constraint is only *approximately* satisfied
Windows ending at day 0 include the weather of the anthesis day itself (00–23 UTC), and the
release contains no day-0-free moisture aggregate. So the model is an *end-of-anthesis-day*
assessment, not a strict "before anthesis" one. For a decision taken on the anthesis date
this is borderline acceptable, but it is a real relaxation of the stated constraint and it
cannot be tested with these data. A truly pre-anthesis model would have had to use only the
distal windows (ending ≤ −10 d), where the moisture concepts are largely unavailable in this
release.

### 2.3 Weather is station-level and temporally unadjusted
* One weather record per trial (up to 8 plots share it) and no station ID, no coordinates,
  no distance-to-station. The measurement error of a station 5–50 km from the plot is
  unknown and is not modelled; this attenuates associations toward the null, so the true
  weather effect could be larger than estimated — but the *predictive* performance reported
  is what a user would actually get.
* `fdate` is a local calendar date labelled UTC; all "overnight" variables are shifted by
  ~6 h. Any biological interpretation of the 12-h block is unsafe (S4 confirms it performs
  no better, and slightly worse, than the 24-h version).

### 2.4 Sample size and clustering
Although there are 395 events, they are not 395 independent events: 76% of the variance in
`S` is between environments, the crude ICC is 0.53, and there are only 221 environments with
any case and 545 distinct weather records. The **effective** number of independent weather
observations is ~545 (and for between-year inference, 32). A two-parameter model uses little
of that, which is why overfitting is modest (optimism 0.03–0.05 AUC) rather than severe. The
limitation is the opposite of usual: the model is not too complex, it is too weak.

### 2.5 Overfitting and optimism
* Apparent − LOYO optimism is 0.048 AUC for M2 and 0.031 for M5/M4, i.e. **~8–9% of the
  apparent AUC**. Reporting apparent performance would have overstated discrimination by
  roughly a tenth.
* Calibration is the bigger problem: OOF calibration slope 0.52 (M2) and 0.74 (M5) mean the
  predicted probabilities are over-dispersed. Prediction ranges are narrow (0.19–0.73 for
  M2), so the model *cannot* say "high risk" even in a very wet season. Any operational use
  would require recalibration on new data.
* Ridge penalisation (M7) did not help (0.576 vs 0.560 for M2), confirming that variance
  inflation is not the binding constraint.

### 2.6 Window and metric sensitivity are confounded with each other
Windows overlap almost completely (they are nested), so the "−5 d vs −15 d" comparison
cannot isolate a critical exposure period: all give AUC 0.59–0.61 with overlapping CIs.
Worse, the *metric* matters more than the window (mean RH 0.635 > warm–wet hours 0.607 >
RH ≥ 90 h 0.569), which means that "which week matters" is partly a question about which
thresholds were used to build the variable. **No claim about a critical period is
supportable from this release.**

### 2.7 Predictor redundancy and instability
* Within a window, moisture families correlate 0.85–0.94 (environment level), so the
  choice among them is not identifiable; I fixed one per model by design.
* Delete-one-trial jackknife shows coefficient ranges of roughly ±10% around the point
  estimate and no sign flips — the *direction* is stable, the *magnitude* is not precisely
  determined.
* The heat term flips sign depending on model (M2: −0.10, ns; M4: +0.02, ns; continuous
  model: −0.36, p = 0.015). This is a genuine instability: the binary model has no power for
  it, and the sign is only interpretable in the continuous model.

### 2.8 Variation across environments is the dominant story
Per-year AUCs range from 0.16 to 1.00 for weather-only models, and the within-year median
is only 0.53–0.58 while the between-year AUC is 0.64–0.72. Excluding the single largest year
(2009) drops LOYO AUC to 0.498. **The honest summary is that pre-anthesis weather sorts
seasons, not fields.** That is not nothing — a season-level risk index is a real product —
but it is not the plot-level classifier that the framing "predict the probability of an FHB
epidemic" invites.

### 2.9 Calibration and transportability
* Calibration slopes < 1 everywhere except M4 (0.84) mean the model is not transportable to
  new years without recalibration; the intercept shift (−0.20 for M2) shows a small
  systematic over-prediction.
* LOSO ≈ LOYO for every model (e.g. M5 0.605 vs 0.598), which is reassuring about spatial
  transport within the sampled states — but the sampled states are a *convenience sample of
  USWBSI trials*, not a probability sample of US wheat fields, and the states enter the
  record in different eras (IL only 2009–2015; OH from 1982). Geographic and temporal
  transportability are therefore entangled and neither is demonstrated beyond 2015.

### 2.10 Retrospective observational data
Everything here is observational and unbalanced: trials differ in cultivar, sowing date,
rotation, tillage and inoculum simultaneously; `corn` is a coarse binary and `resist` is a
4-level ordinal that hides within-class variation. The weather coefficient is a
*conditional association* under this design, not a causal effect, and it remains vulnerable
to unmeasured confounding by management (e.g. rotation, tillage, planting date) that
covaries with site and year.

### 2.11 Small validation groups
Only 23/32 LOYO folds and 15/17 LOSO folds have both classes; 17/32 LOYO folds have <5
events. Per-fold AUCs are therefore not estimates of anything stable, and I deliberately do
not average them as if they were. The pooled OOF AUC is the only reasonably stable summary,
and even it has a CI width of ~0.09.

The instability is not only sampling noise: within-year AUCs occasionally **reverse**
completely (M4: 0.00 in 1994 and 1995; M5: 0.00 in 1999, 0.16 in 2008). A reversal means the
model ordered the plots of that year exactly backwards. In a year with 2–10 plots this is
compatible with chance, but it is a warning that any operational use at trial scale would
need local (re)calibration and would sometimes be actively misleading.

---

## 3. Which findings are robust?

**Robust (survive every sensitivity check):**
1. Atmospheric moisture in the pre-anthesis window is positively associated with epidemic
   risk: OR ≈ 1.10–1.15 per +10 h of high-RH hours, OR ≈ 1.6–1.7 per SD of mean RH,
   p < 10⁻⁵ in every specification, robust to clustering, year/state fixed effects,
   outcome threshold, exposure window and the choice of moisture metric.
2. Agronomic covariates dominate: resistance class OR 0.59 per step, corn residue OR 2.47 —
   larger effects, better calibration and better transportability than any weather term.
3. More weather complexity does not buy performance: quadratic term, mean-temperature term
   and ridge all change LOYO AUC by ≤ 0.02.
4. The 12-h "overnight" variables do not outperform the 24-h versions, consistent with
   their documented UTC misalignment.

**Fragile / exploratory (reported but not to be relied on):**
1. The heat-stress (T > 30 °C) effect: null in the binary models, protective in the
   continuous model, sign-instable.
2. The superiority of any particular window (−5, −7, −10, −14, −15 d) — statistically
   indistinguishable.
3. Mean RH as the single best weather metric (0.635) — post hoc relative to the primary
   model, CI overlapping M5's.
4. Anything about 2009, which carries ~17% of the data and appears to supply much of the
   pooled discrimination.
5. The LOSO result for MO (AUC 0.44 for M4, the only state where the agronomic model
   failed) — a single-state anomaly not investigated further.

---

## 4. What would change the conclusion

* A dataset with **plot-level or farm-level weather** (on-site logger or gridded reanalysis
  at ~1 km) and **coordinates**, so that exposure error is reduced and spatial validation is
  possible.
* **Multiple plots per trial sharing weather but differing in cultivar** are already present
  (492 trials, median 2 plots) — a proper multi-level model with plot nested in trial nested
  in state-year would separate weather from site effects better than the fixed-effects
  models used here.
* **Pre-anthesis-and-anthesis-only weather plus inoculum measurements** (ascospore counts,
  residue density/type, tillage) would test whether the moisture signal is really about
  inoculum production or about infection conditions.
* **A defined and documented binary outcome** (with a stated cut-point used in extension or
  breeding) would remove the largest piece of analyst discretion.
* **Prospective seasons after 2015** for genuine external validation; LOYO on 1982–2015 is
  the best available proxy, not the same thing.

## 5. What additional data would be needed for prospective validation

1. New seasons (≥3–5 years) recorded with the same protocol and with weather that is
   independent of the training station set.
2. Station distance and coordinates, or on-farm weather, to quantify exposure error.
3. A pre-registered decision rule (cut-point, action) and a cost structure, so that the
   value of the model can be assessed as net benefit rather than AUC.
4. Enough events in each new environment (≥10 plots, both classes) to estimate calibration
   slope per environment.

## 6. Did I revise the analysis? What changed and why

Yes, three times, all documented in `analysis_log.md` and `analysis_plan.md` §12:

1. The audit forced the outcome to be **defined** rather than taken from documentation.
2. Full model estimation showed the heat term to be null, and validation showed a
   pre-specified alternative (M5) to be better; per the pre-registered rule I kept M2 as
   primary and report M5 as the preferred alternative. I did **not** silently replace M2.
3. Two analyses not in the original plan (within- vs between-year discrimination; fixed
   effects confounding check) were added *because the S6 result (excluding 2009 destroyed
   the signal) demanded an explanation*. They are labelled exploratory.

**I did not** drop any model, any sensitivity analysis or any negative result from the
write-up. The failed attempts (pip installation, variable-name resolution failures, the
window-ladder substitution) are recorded in `analysis_log.md`.

---

## 7. Addendum after the literature search

One point above needs qualification, and it is appended rather than edited into §2.1.
The literature does have a documented binary outcome: **FHB index ≥ 10%** (Shah et al. 2013,
2019a), which reproduces exactly 273/999 events as reported in Shah et al. (2019b). So the
"outcome is my construction" criticism should be read as "the release omits the definition
that the field uses; I defined a different, defensible one (5%) before knowing the
convention". The post hoc 10% comparison (`comparison_with_literature.md` §2) shows the same
substantive conclusions at the conventional threshold (AUC 0.62–0.72, calibration slope
0.78–0.91), so the choice of cut-point does not drive the headline.

The literature also strengthens one limitation and weakens another:
* **Strengthened:** my a-priori exclusion of temperature-variability (`SD`, `MINMAXDIFF`)
  variables looks wrong in hindsight — the random-forest paper finds a temperature-stability
  variable to be its top pre-anthesis predictor. That is a genuine gap in my candidate set.
* **Weakened:** the concern that a 2-parameter logistic model is "too simple" is not
  supported by the literature either — published work needs 4–14 predictors and post-anthesis
  windows to reach AUC 0.8–0.9, i.e. the extra skill comes from information I was not allowed
  to use, not from model form.
