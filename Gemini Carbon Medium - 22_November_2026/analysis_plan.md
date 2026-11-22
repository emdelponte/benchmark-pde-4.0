# Independent Pre-Modeling Analysis Plan (`analysis_plan.md`)

*Status: Written and locked **prior** to fitting any predictive models or examining any weather–outcome associations (`2026-11-22`). Subsequent additions or modifications, if any, will be recorded in `analysis_log.md` and appended as dated addenda rather than overwriting this plan.*

---

## 1. Prediction Target and Intended Epidemiological Use

* **Primary response variable:** Binary FHB epidemic indicator $Y_i = \mathbb{I}(S_i \ge 10\%)$, where $S_i$ is plot-level FHB spike severity index (%) in fungicide-untreated wheat (`273` events [27.33%] and `726` nonevents [72.67%] across $N = 999$ plots in `FHBVer2.parquet`).
  * *Justification:* Continuous `S` is the sole response column in `FHBVer2.parquet` and `FHBVer2DataDict.yaml`. In U.S. wheat pathology (USWBSI), $S \ge 10\%$ in untreated plots defines an economically damaging FHB outbreak warranting triazole fungicide intervention.
* **Intended operational context:** Decision support **at wheat anthesis (Feekes 10.5.1)**—the critical biological infection window and last standard timing for effective fungicide application—using weather information observed no later than the flowering date (`window_end_day <= 0`, `analysis_period == "pre"`).
* **Prediction vs. causal explanation:** Fitted coefficients measure predictive risk associations across environments, **not** isolated causal effects of single meteorological variables, because synoptic weather variables co-vary with regional climate, cropping systems, inoculum reservoir density, and cultivar deployment.

---

## 2. Candidate Weather Variables, Exposure Windows, and Epidemiological Reasoning

### 2.1 Strict Exclusion Rules (Pre-Outcome Screening)
Before examining any associations with $Y$:
1. **Temporal leakage exclusion (Mandatory Constraint 1):** Exclude all `137` `post` variables (`window_end_day > 0`) and all `18` `pre-post` variables (including `INT3`), leaving `174` pre-anthesis (`analysis_period == "pre"`) variables.
2. **Timezone-artifact exclusion (`12H` variables):** Exclude the `60` `12H` ("overnight" `20:00–08:00 UTC`) pre-anthesis variables from primary models because our audit demonstrated that unadjusted UTC bounds capture mid-afternoon (`15:00–03:00 CDT` / `16:00–04:00 EDT`) rather than local night, inverting physical humidity/VPD relationships and introducing longitudinal bias between Eastern and Plains states. (Evaluated only in a targeted sensitivity check.)
3. **Biologically implausible ultra-early window exclusion:** Exclude variables ending $\ge 25$ days pre-anthesis or spanning 50–100 days pre-anthesis (such as barometric pressure `P.A.1`–`P.A.5`, `P.MINMAXDIFF.1`, `P.SD.1`, `T.14T22.CD.1`, `T.14T22.CD.2`, `T.G30.CHD.2`, `TRH.*.CHD.2`, `T.A.3`, `D.A.3`), which in winter/spring wheat correspond to vegetative/dormancy-break stages or act as macro-geographic proxies rather than proximal FHB drivers.

### 2.2 Biologically Grounded Pre-Anthesis Exposure Windows and Candidate Mechanisms
*Fusarium graminearum* epidemics depend on two sequential pre-anthesis processes on surface crop residue:
1. **Perithecial initiation and ascospore maturation (~10–20 d pre-anthesis; windows `[-15, 0]` and `[-20, 0]`):** Requires sustained moisture (`RH`, `RH >= 80%` / `90%`, or low `VPD`) paired with moderate-to-warm temperatures ($15\text{–}30^\circ\text{C}$). Cold temperatures ($<9\text{–}15^\circ\text{C}$) arrest perithecial maturation, whereas excessive heat ($>30^\circ\text{C}$) and large diurnal drying swings (`T.MINMAXDIFF`, high `VPD`) desiccate surface residue and suppress sporulation.
2. **Final spore maturation, ascospore discharge readiness, and boundary-layer moisture entering flowering (~5–10 d pre-anthesis; windows `[-7, 0]` and `[-10, 0]`):** Hydration and high relative humidity (`RH7`, `RH.A.PRE10.24H`, `RH907`) or low vapor pressure deficit (`VPD.A.1`) immediately preceding anthesis sustain active ascospore release and signal persistent wet synoptic regimes as anthers extrude.

Accordingly, we focus primary candidate evaluation on three well-defined `24h` pre-anthesis windows—**7-day** (`[-7, 0]`, 8 d closed), **10-day** (`[-10, 0]`, 11 d closed), and **15-day** (`[-15, 0]`, 16 d closed; plus `[-20, -10]`/`[-20, 0]` for pre-heading vs. proximal contrast)—across three physical axes:
* **Thermal regime:** `T.A.PRE7.24H`, `T.A.PRE10.24H`, `T.A.PRE15.24H`, `T.A.2` (`[-20, -10]`), and thermal suitability duration `T15307` / `T.15T30.PRE10.24H`.
* **Atmospheric moisture / drying power:** `RH7`, `RH.A.PRE10.24H`, `RH.A.PRE15.24H`, `VPD.A.1` (`[-10, 0]`), and high-humidity duration `RH.G80.CHD.1` / `RH907`.
* **Joint hydrothermal suitability:** `TRH807`, `TRH.15T30nRHG80.PRE10.24H`, `TRH.15T30nRHG80.PRE15.24H`, and `TRH.9T30nRHG90.PRE15.24H` (hours simultaneously satisfying favorable temperature and high RH).

---

## 3. Predictor Transformations and Collinearity Control

* **Centering and scaling:** Continuous predictors in interaction (`M3`), polynomial (`M4`), and penalized (`M5`) models will be centered (and standardized by training-fold mean and SD inside every cross-validation fold) so main effects are interpretable at mean conditions and numerical conditioning is preserved. Original-unit coefficients and odds ratios per biologically meaningful increment (e.g., $+2^\circ\text{C}$ in $T$, $+10\%$ in $\text{RH}$, $-0.2\text{ kPa}$ in $\text{VPD}$, $+24\text{ h}$ of hydrothermal duration) will be reported alongside standardized log-odds.
* **Skewed count variables:** Audit results showed mild skewness for `RH >= 80%` and `15 <= T <= 30 & RH >= 80%` counts, vs. extreme zero-inflated skew ($|z| > 7$) for `T > 30°C` (`T.G30.*`). We avoid using raw extreme-tail counts (`T.G30.*`) as unregularized linear terms and check functional form / leverage diagnostics (`Cook's D`, hat values, restricted cubic spline / quadratic checks) on selected continuous predictors.
* **Collinearity rule:** Because moisture metrics over the same window are strongly collinear ($|r| = 0.78\text{–}0.91$ among `RH.A`, `VPD.A`, `TDD.A`, and `RH.G80`), **no candidate multi-predictor model may include two pure moisture variables from overlapping windows**, and variance inflation factors ($\text{VIF}$) will be required to satisfy $\text{VIF} < 3.0$ across all main-effect terms (`T` and `RH` correlate at only $r = -0.13$, guaranteeing near-orthogonality when paired).

---

## 4. Model-Building Strategy and Complexity Budget

To prevent selection bias ("data dredging" across 174 correlated predictors) while respecting our effective sample size ($E_{\text{eff,sy}} \approx 22$ state-year events; $E_{\text{eff,env}} \approx 121$ weather-environment events) and **Mandatory Constraint 4** ($\le 3$ weather predictor terms, with every nonlinear basis or interaction counted explicitly), we pre-specify **six compact logistic regression models** (`family = binomial(link = "logit")`):

| Model ID | Specification (Weather Predictor Terms) | Weather Terms | Slope Params ($p$) | Epidemiological Hypothesis Tested |
| :--- | :--- | :---: | :---: | :--- |
| **M0 (Baseline)** | `T.A.PRE7.24H + RH7` | 2 | 2 | Minimal 1-week pre-anthesis additive thermal + moisture baseline (`[-7, 0]`). |
| **M1 (15-d Additive)** | `T.A.PRE15.24H + RH.A.PRE15.24H` | 2 | 2 | Extended 15-d window (`[-15, 0]`) capturing perithecial maturation + spore buildup. |
| **M2 (Two-Stage Hydrothermal)** | `TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2` | 3 | 3 | 15-d joint hydrothermal sporulation hours + 10-d pre-anthesis evaporative demand (`VPD`) + 20–10 d pre-heading temperature. |
| **M3 (Hydrothermal Interaction)** | `cT10 + cRH10 + cT10:cRH10` (`T.A.PRE10.24H`, `RH.A.PRE10.24H`) | 3 | 3 | Continuous Disease-Triangle synergy: moisture effect amplified under warm vs. cool 10-d pre-anthesis temperatures. |
| **M4 (Nonlinear Thermal Curve)** | `cT10 + I(cT10^2) + cRH10` (`T.A.PRE10.24H`, `RH.A.PRE10.24H`) | 3 | 3 | Unimodal/concave thermal response curve (optimal $T$ vs. cool/hot suppression) + 10-d relative humidity. |
| **M5 (Nested L1-Screened Ridge/GLM)** | Top $\le 3$ predictors selected *inside each training fold* via grouped L1-penalized logistic regression (`glmnet`, restricted to valid `24h` pre-anthesis pool `window_start_day >= -30` with pairwise $|r| < 0.85$ pruning), refit via ridge-shrunk / unpenalized logistic regression | $\le 3$ | $\le 3$ | Tests whether leakage-free, penalized data-driven selection within the $\le 3$-term budget outperforms fixed mechanistic models or suffers cross-environment selection instability. |

* **Complexity and inference controls:**
  * Every primary model has $p \in \{2, 3\}$ estimated slope parameters (+ 1 intercept = 3–4 total parameters), strictly satisfying Constraint 4 under both term-count and parameter-count definitions.
  * For parameter uncertainty on full-sample fits, we will report **both** naive GLM standard errors and **cluster-robust sandwich standard errors** clustered on `state × year` (`142` clusters) and `env_pre_id` (`545` clusters) so confidence intervals reflect plot pseudoreplication.
  * **Model selection rule (Section 5):** Final model recommendation will balance out-of-year and out-of-state calibration, Brier score, ROC AUC, parameter stability, VIF, and epidemiological interpretability—**not** simply picking the highest observed AUC.
* **Supplementary exploratory benchmark (strictly secondary, Section 4):** An unconstrained pre-anthesis LASSO logistic regression (`cv.glmnet` across all 174 pre-anthesis variables) and a shallow Random Forest (`ranger` / bagged trees if available, or GAM/spline check) will be evaluated under the *exact same* grouped CV splits solely to quantify how much—or how little—predictive signal is sacrificed by enforcing the 3-term linear/logistic parsimony constraint.

---

## 5. Validation Design and Performance Metrics

Random observation-level splitting is **prohibited** because 719 of 999 plots share identical weather vectors with co-located plots and $\text{ICC}_{\text{state:year}} = 0.717$. All preprocessing, centering/scaling, and `M5` variable/penalty tuning will occur strictly inside training folds across **three complementary grouped validation schemes**:

1. **Leave-One-Year-Out Cross-Validation (LOYO-CV, 32 year folds — Primary Prospective Temporal Validation):**
   * Holds out all observations from year $t$ ($t \in \{1982, \dots, 2015\}$) simultaneously; trains on the remaining 31 years.
   * Evaluates forecasting into an unseen growing season free of synoptic year leakage.
2. **Leave-One-State-Out Cross-Validation (LOSO-CV, 17 state folds — Primary Spatial Transportability Validation):**
   * Holds out all observations from state $s$ simultaneously; trains on the remaining 16 states.
   * Evaluates geographic transportability to an unmonitored state/wheat production region.
3. **Grouped `state × year` 10-Fold Cross-Validation (5 repeats × 10 folds over the 142 `state × year` clusters):**
   * Keeps every plot, location, cultivar, and flowering date within a `state × year` in the same fold while ensuring every test fold contains ~100 plots and ~25–30 events so fold-level discrimination and calibration metrics are stably estimable in 100% of folds.

### Performance Metrics
* **Discrimination:** Out-of-fold ROC AUC (with DeLong / cluster-bootstrap 95% CIs on pooled out-of-fold predictions) and Precision–Recall AUC (PR-AUC).
* **Overall accuracy & probability skill:** Brier score $\frac{1}{N}\sum (y_i - \hat{p}_i)^2$ and **Brier Skill Score (BSS)** relative to a null model predicting the training-fold prevalence $\bar{y}_{\text{train}}$.
* **Calibration:**
  * **Calibration-in-the-large (intercept $\alpha$):** Estimated from $\text{logit}(y_i) = \alpha + \text{offset}(\text{logit}(\hat{p}_i))$.
  * **Calibration slope ($\gamma$):** Estimated from $\text{logit}(y_i) = \alpha_0 + \gamma\,\text{logit}(\hat{p}_i)$.
  * **Calibration curves / decile reliability plots** (`output/figures/`), plus Integrated Calibration Index (ICI / mean absolute calibration error via LOESS smooth).
* **Inter-environment heterogeneity:** Distribution (median, IQR, min–max) of fold-specific AUC, Brier score, and mean predicted vs. observed risk across well-sampled years ($n \ge 20$, $\ge 1$ event/nonevent: 14 years) and states ($n \ge 25$, $\ge 1$ event/nonevent: 10 states), plus explicit false-alarm assessment in the 4 zero-event states (`WI, NY, DE, AR`).

---

## 6. Pre-Specified Sensitivity Analyses

1. **Exposure-window sensitivity:** Systematic comparison of identical additive `T + RH` and joint `TRH` models across `[-5, 0]`, `[-7, 0]`, `[-10, 0]`, `[-14, 0]`, `[-15, 0]`, `[-20, 0]`, and `[-30, 0]` to test whether predictive skill is sharply localized near anthesis or diffuse across pre-anthesis windows.
2. **Outcome threshold sensitivity:** Refit and validate the primary model(s) at $S \ge 5\%$ (`395` events), $S > 10\%$ (`271` events), and $S \ge 15\%$ (`202` events).
3. **UTC `12H` ("overnight") vs. `24H` comparison and strictly pre-flowering cutoff (`window_end_day <= -5`):** Quantify the empirical effect of the `12H` UTC-shift artifact vs. `24H` summaries, and evaluate prediction skill when day `-4` to `0` weather is unavailable (`[-15, -5]` / `[-20, -10]` lead-time forecast 5–10 days *before* anthesis!).
4. **Environment-level deduplicated analysis ($N = 545$ unique weather environments) & agronomic-adjusted sensitivity:**
   * Fit binomial/quasibinomial logistic regression aggregated to the `545` unique weather environments ($k_e / n_e$ events per trial environment) so multi-plot trials do not receive $2\times\text{–}8\times$ observation weight;
   * Quantify the incremental discrimination and calibration gain when known pre-anthesis host resistance (`resist`) and residue (`corn`) are added as offset/adjustment covariates alongside the $\le 3$ weather predictors (strictly separated from the primary weather-only model).
5. **Post-anthesis weather upper-bound benchmark (strictly diagnostic, non-deployable):** Compare pre-anthesis skill against a post-anthesis model (`0` to `+10 d`) solely to quantify the fundamental physical information gap caused by unobserved post-flowering infection weather.
