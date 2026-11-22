# Model Estimates, Diagnostics, and Validation Results (`results.md`)

All results in this report were generated reproducibly from `data/FHBVer2.parquet` ($N = 999$ fungicide-untreated wheat plots; primary binary epidemic outcome $Y = \mathbb{I}(S \ge 10\%)$, `273` events [27.33%] and `726` nonevents [72.67%]) via [02_model_fitting_and_validation.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/02_model_fitting_and_validation.R), [03_sensitivity_and_figures.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/03_sensitivity_and_figures.R), and [04_posthoc_refinement_check.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/04_posthoc_refinement_check.R). Tabular outputs are saved in `output/` and diagnostic figures in `output/figures/`.

---

## 1. Summary of Pre-Specified Candidate Models and Complexity Budget

All primary models strictly satisfy the mandatory scientific constraints: logistic regression framework (`binomial(link = "logit")`), predictors available no later than anthesis (`analysis_period == "pre"`, `window_end_day <= 0`), and at most **3 weather predictor terms** (and $\le 3$ slope parameters $p$, counting interaction and polynomial terms explicitly):

| Model | Formula / Predictor Specification | Weather Terms | Slope Params ($p$) | Total Params ($p+1$) | Max VIF | AIC | BIC | Apparent AUC | Apparent Brier |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M0 (Baseline 7-d)** | `T.A.PRE7.24H + RH7` | 2 | 2 | 3 | 1.02 | 1107.15 | 1121.87 | 0.671 | 0.185 |
| **M1 (Additive 15-d)** | `T.A.PRE15.24H + RH.A.PRE15.24H` | 2 | 2 | 3 | 1.00 | 1112.83 | 1127.55 | 0.665 | 0.187 |
| **M2 (Two-Stage Hydro 3p)** | `TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2` | 3 | 3 | 4 | 1.45 | 1094.14 | 1113.77 | 0.691 | 0.182 |
| **M3 (Interaction 10-d)** | `cT10 + cRH10 + cT10:cRH10` | 3 | 3 | 4 | 1.06 | 1112.67 | 1132.30 | 0.671 | 0.186 |
| **M4 (Quadratic T 10-d)** | `cT10 + I(cT10^2) + cRH10` | 3 | 3 | 4 | 1.03 | 1115.70 | 1135.32 | 0.670 | 0.187 |
| **M5a (Nested L1-GLM)** | Full sample: `T.A.2 + T.MINMAXDIFF.1 + RH7` (re-selected per fold) | $\le 3$ | $\le 3$ | $\le 4$ | 1.28 | 1068.83 | 1088.46 | 0.716 | 0.177 |
| **M5b (Nested L1-Ridge)** | Same within-fold L1 active set ($\le 3$) + nested grouped L2 shrinkage | $\le 3$ | $\le 3$ | $\le 4$ | — | — | — | — | — |
| *Post-plan reductions:* | *(Evaluated transparently after observing non-significant 3rd/2nd terms)* | | | | | | | | |
| **M0r (1-p Reduction of M0)** | `RH7` (`[-7, 0]` 24h mean RH only) | 1 | 1 | 2 | 1.00 | 1106.11 | 1115.93 | 0.670 | 0.185 |
| **M2r (2-p Reduction of M2)** | `VPD.A.1 + T.A.2` (`[-10, 0]` VPD + `[-20, -10]` T) | **2** | **2** | **3** | **1.05** | **1092.61** | **1107.33** | **0.690** | **0.182** |

*Note on secondary exploratory benchmarks:* Two unconstrained benchmarks—`E1_LASSO174_1se` (`cv.glmnet` L1 path over all 174 pre-anthesis predictors, median `5` [IQR `0–10`] nonzero predictors per fold) and `E2_GAM15d` (bivariate penalized splines `s(T15) + s(RH15) + ti(T15, RH15)`)—were evaluated under identical validation folds solely to test whether relaxing parsimony/linearity improves generalization.

---

## 2. Parameter Estimates and Cluster-Robust Uncertainty

Because `719` of `999` plots share identical weather vectors (`545` unique weather environments) and cluster strongly within `142` `state × year` groups ($\text{ICC} = 0.717$), **naive GLM standard errors underestimate true parameter uncertainty by a factor of $1.6\times$ to $2.2\times$**. All inference below uses Liang–Zeger / Cameron–Gelbach–Miller sandwich standard errors clustered by `state × year` (`142` clusters):

| Model | Term | Estimate ($\hat{\beta}$) | Naive SE | Env-Clustered SE (545) | State:Year SE (142) | $Z_{\text{SY}}$ | $p_{\text{SY}}$ | 95% Cluster-Robust CI |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| **M0** | `(Intercept)` | $-5.8696$ | $0.9226$ | $1.2293$ | $1.7444$ | $-3.36$ | $0.0008$ | $[-9.289, -2.451]$ |
| | `T.A.PRE7.24H` (°C) | $-0.0266$ | $0.0271$ | $0.0344$ | $0.0528$ | $-0.50$ | $0.6138$ | $[-0.130, +0.077]$ |
| | `RH7` (%) | $+0.0757$ | $0.0098$ | $0.0129$ | $0.0175$ | $+4.33$ | $<0.0001$ | $[+0.042, +0.110]$ |
| **M1** | `(Intercept)` | $-7.6088$ | $1.0571$ | $1.2788$ | $2.0132$ | $-3.78$ | $0.0002$ | $[-11.555, -3.663]$ |
| | `T.A.PRE15.24H` (°C) | $+0.0056$ | $0.0301$ | $0.0365$ | $0.0575$ | $+0.10$ | $0.9224$ | $[-0.107, +0.118]$ |
| | `RH.A.PRE15.24H` (%) | $+0.0926$ | $0.0123$ | $0.0154$ | $0.0257$ | $+3.61$ | $0.0003$ | $[+0.042, +0.143]$ |
| **M2** | `(Intercept)` | $-1.4412$ | $0.4990$ | $0.6508$ | $1.0098$ | $-1.43$ | $0.1535$ | $[-3.420, +0.538]$ |
| | `TRH.15T30nRHG80.PRE15.24H` (h) | $+0.0014$ | $0.0020$ | $0.0027$ | $0.0040$ | $+0.34$ | $0.7323$ | $[-0.006, +0.009]$ |
| | `VPD.A.1` (kPa, `[-10, 0]`) | $-2.7376$ | $0.3901$ | $0.5387$ | $0.7919$ | $-3.46$ | $0.0005$ | $[-4.290, -1.186]$ |
| | `T.A.2` (°C, `[-20, -10]`) | $+0.1386$ | $0.0338$ | $0.0468$ | $0.0611$ | $+2.27$ | $0.0234$ | $[+0.019, +0.258]$ |
| **M3** | `(Intercept)` (at $\bar{T}_{10}=17.99$, $\bar{\text{RH}}_{10}=69.91$) | $-1.0772$ | $0.0772$ | $0.1081$ | $0.1597$ | $-6.74$ | $<0.0001$ | $[-1.390, -0.764]$ |
| | `cT10` (°C) | $-0.0065$ | $0.0289$ | $0.0345$ | $0.0495$ | $-0.13$ | $0.8954$ | $[-0.103, +0.090]$ |
| | `cRH10` (%) | $+0.0779$ | $0.0107$ | $0.0132$ | $0.0201$ | $+3.87$ | $0.0001$ | $[+0.038, +0.117]$ |
| | `cT10:cRH10` | $-0.0084$ | $0.0045$ | $0.0055$ | $0.0083$ | $-1.02$ | $0.3085$ | $[-0.025, +0.008]$ |
| **M4** | `(Intercept)` | $-1.0171$ | $0.0929$ | $0.1345$ | $0.1956$ | $-5.20$ | $<0.0001$ | $[-1.401, -0.634]$ |
| | `cT10` (°C) | $-0.0170$ | $0.0290$ | $0.0367$ | $0.0540$ | $-0.32$ | $0.7523$ | $[-0.123, +0.089]$ |
| | `I(cT10^2)` ($\text{°C}^2$) | $-0.0054$ | $0.0080$ | $0.0100$ | $0.0136$ | $-0.40$ | $0.6911$ | $[-0.032, +0.021]$ |
| | `cRH10` (%) | $+0.0789$ | $0.0107$ | $0.0135$ | $0.0211$ | $+3.74$ | $0.0002$ | $[+0.038, +0.120]$ |
| **M2r** | `(Intercept)` | $-1.4696$ | $0.4973$ | $0.6511$ | $1.0194$ | $-1.44$ | $0.1494$ | $[-3.468, +0.528]$ |
| *(Final)* | **`VPD.A.1` (kPa, `[-10, 0]`)** | **$-2.8338$** | **$0.3641$** | **$0.4766$** | **$0.7184$** | **$-3.94$** | **$0.0001$** | **$[-4.242, -1.426]$** |
| | **`T.A.2` (°C, `[-20, -10]`)** | **$+0.1507$** | **$0.0289$** | **$0.0393$** | **$0.0548$** | **$+2.75$** | **$0.0060$** | **$[+0.043, +0.258]$** |

### Key Epidemiological Insights from Parameter Estimates
1. **Dominance of proximal atmospheric moisture over proximal air temperature:** In `M0`, `M1`, `M3`, and `M4`, relative humidity over `[-7, 0]`, `[-10, 0]`, or `[-15, 0]` is strongly associated with epidemic risk ($\text{OR} = 2.13$ per $+10\%$ in `RH7`; $p < 0.0001$), whereas proximal air temperature (`T.A.PRE7.24H`, `T.A.PRE10.24H`, `T.A.PRE15.24H`), its quadratic curvature (`cT10^2`, $p = 0.691$), and its multiplicative interaction with RH (`cT10:cRH10`, $p = 0.309$) are completely indistinguishable from zero! Because wheat reaches anthesis only when ambient temperatures enter the ~15–21°C developmental band (`96%` of hours in `PRE7` already lie within `9–30°C`), proximal temperature is rarely limiting at flowering; moisture is the limiting physical factor.
2. **Two-stage pre-anthesis mechanism (`M2` and `M2r`):** In contrast to proximal temperature, **earlier pre-heading air temperature (`T.A.2`, 20 to 10 d pre-anthesis)** has a clear positive association ($\hat{\beta} = +0.1507$, $\text{OR} = 1.35$ [95% CI: $1.09\text{–}1.68$] per $+2^\circ\text{C}$, $p = 0.0060$) when paired with **proximal 10-d vapor pressure deficit (`VPD.A.1`, 10 to 0 d pre-anthesis)** ($\hat{\beta} = -2.8338$, $\text{OR} = 1.76$ [95% CI: $1.33\text{–}2.34$] per $-0.20\text{ kPa}$ decrease toward saturation, $p = 0.0001$). Once `VPD.A.1` and `T.A.2` are accounted for, 15-d joint threshold hours (`TRH.15T30nRHG80.PRE15.24H`) add zero explanatory value ($\text{LRT } p = 0.4955$).

---

## 3. Out-of-Sample Validation Across Temporal, Spatial, and Grouped Designs

### 3.1 Pooled Cross-Validation Performance ($N = 999$)

| Model ($p$ slope params) | Validation Scheme | ROC AUC [Cluster-Boot 95% CI] | PR-AUC | Brier Score | Brier Skill (BSS) | Cal. Intercept ($\hat{\alpha}$) | Cal. Slope ($\hat{\gamma}$) | ICI |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M0: 7-d T + RH** (2p) | LOYO (32 yr) | 0.649 [0.572, 0.712] | 0.379 | 0.189 | +5.6% | $+0.003$ | 0.847 | 0.022 |
| | LOSO (17 st) | 0.648 [0.581, 0.721] | 0.397 | 0.189 | +6.3% | $-0.001$ | 0.857 | 0.021 |
| | GroupSY (5×10f) | 0.645 [0.588, 0.701] | 0.377 | 0.190 | +5.6% | $-0.004$ | 0.824 | 0.022 |
| **M0r: 7-d RH only** (1p)* | LOYO (32 yr) | 0.658 [0.583, 0.720] | 0.388 | 0.188 | +6.2% | $-0.001$ | **0.897** | 0.020 |
| | LOSO (17 st) | 0.652 [0.568, 0.713] | 0.396 | 0.188 | +6.7% | $-0.001$ | **0.893** | **0.017** |
| | GroupSY (5×10f) | 0.653 [0.573, 0.713] | 0.386 | 0.189 | +6.2% | $-0.003$ | **0.868** | **0.017** |
| **M1: 15-d T + RH** (2p) | LOYO (32 yr) | 0.637 [0.545, 0.725] | 0.344 | 0.193 | +3.9% | $-0.001$ | 0.784 | 0.025 |
| | LOSO (17 st) | 0.637 [0.554, 0.716] | 0.344 | 0.192 | +4.6% | $-0.009$ | 0.793 | 0.027 |
| | GroupSY (5×10f) | 0.638 [0.559, 0.717] | 0.339 | 0.193 | +4.2% | $-0.009$ | 0.781 | 0.030 |
| **M2: Two-Stage Hydro** (3p) | LOYO (32 yr) | 0.666 [0.581, 0.747] | 0.389 | 0.187 | +6.8% | $+0.007$ | 0.827 | 0.023 |
| | LOSO (17 st) | 0.655 [0.575, 0.726] | 0.375 | 0.189 | +6.3% | $-0.034$ | 0.755 | 0.021 |
| | GroupSY (5×10f) | 0.656 [0.578, 0.728] | 0.379 | 0.188 | +6.5% | $-0.015$ | 0.785 | 0.022 |
| **M2r: VPD10 + T20_10** (2p)* | **LOYO (32 yr)** | **0.671 [0.587, 0.743]** | **0.395** | **0.185** | **+7.8%** | **$+0.008$** | **0.894** | **0.025** |
| *(Recommended Final)* | **LOSO (17 st)** | **0.660 [0.569, 0.727]** | **0.381** | **0.187** | **+7.2%** | **$-0.030$** | **0.807** | **0.019** |
| | **GroupSY (5×10f)** | **0.661 [0.571, 0.732]** | **0.385** | **0.187** | **+7.2%** | **$-0.011$** | **0.826** | **0.021** |
| **M3: 10-d T × RH** (3p) | LOYO (32 yr) | 0.643 [0.565, 0.724] | 0.378 | 0.192 | +4.4% | $-0.001$ | 0.794 | 0.037 |
| | LOSO (17 st) | 0.632 [0.549, 0.709] | 0.360 | 0.193 | +4.2% | $-0.006$ | 0.750 | 0.031 |
| **M4: 10-d Quad T + RH** (3p) | LOYO (32 yr) | 0.638 [0.557, 0.704] | 0.348 | 0.193 | +3.6% | $+0.005$ | 0.758 | 0.036 |
| | LOSO (17 st) | 0.637 [0.554, 0.708] | 0.358 | 0.193 | +4.4% | $+0.010$ | 0.778 | 0.037 |
| **M5a: Nested L1-GLM** ($\le 3$p) | LOYO (32 yr) | 0.651 [0.558, 0.736] | 0.374 | 0.191 | +4.6% | $+0.010$ | **0.660** | 0.028 |
| | LOSO (17 st) | 0.652 [0.575, 0.737] | 0.372 | 0.194 | +3.8% | $-0.124$ | **0.608** | 0.041 |
| **M5b: Nested L1-Ridge** ($\le 3$p) | LOYO (32 yr) | 0.648 [0.555, 0.742] | 0.372 | 0.190 | +5.1% | $+0.017$ | 0.826 | 0.023 |
| | LOSO (17 st) | 0.650 [0.558, 0.729] | 0.370 | 0.191 | +5.1% | $-0.086$ | 0.731 | 0.022 |
| *Exploratory Secondary:* | | | | | | | | |
| **E1: LASSO-174 (`1se`)** | LOYO / LOSO | 0.447 / 0.575 | 0.248 / 0.306 | 0.204 / 0.197 | $-1.6\%$ / $+2.1\%$ | $-0.006$ / $+0.033$ | $-0.808$ / $0.864$ | 0.073 / 0.036 |
| **E2: Bivariate GAM 15-d** | LOYO / LOSO | 0.613 / 0.608 | 0.324 / 0.339 | 0.198 / 0.200 | $+1.4\%$ / $+0.9\%$ | $+0.048$ / $+0.026$ | **0.445 / 0.370** | 0.045 / 0.056 |

*\*`M0r` and `M2r` are post-plan parsimony reductions documented in `analysis_log.md`.*

### 3.2 Complexity vs. Generalization and Proof of Leakage under Random Splitting
* **More complex models systematically overfit across environments:** `M5a` (L1-screened 3-term GLM) achieved the highest *in-sample* AUC (`0.716`), yet its out-of-sample calibration slopes fell to `0.660` (LOYO) and `0.608` (LOSO), and its third selected variable rotated unstably across folds (`RH7` and `T.MINMAXDIFF.1` selected in 100% of folds, whereas the 3rd slot split across `T.A.2` [9/32 LOYO, 4/17 LOSO], `RH.MINMAXDIFF.1` [6/32, 6/17], `TRH.9T30nRHG80.PRE14.24H`, `VPD.A.1`, `D.MINMAXDIFF.1`, `D.A.2`, and `RH.A.1`). Unconstrained 174-variable LASSO (`E1`) and spline GAM (`E2`) performed even worse (`LOYO AUC = 0.447` and `0.613`).
* **Optimism of prohibited random observation-level splitting:** Under naive 10-fold random row splitting (`output/cv_performance_summary.csv`), `E2_GAM15d` jumped artificially from `LOYO AUC = 0.613` (`Cal_Slope = 0.445`) to **`AUC = 0.696` (`Cal_Slope = 0.919`)**, `E1_LASSO174` jumped from `0.447` to **`0.658`**, and `M5a` jumped from `0.651` to **`0.695`**—direct empirical proof that random plot-level CV leaks shared trial weather and inflates complex models by `+0.04` to `+0.21` AUC units!

### 3.3 Calibration Diagnostics and Environmental Heterogeneity
* **Calibration plots** ([fig1_calibration_curves.png](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/figures/fig1_calibration_curves.png)): `M0`, `M0r`, `M2`, and `M2r` track the 45° identity line closely across predicted probabilities from `0.08` to `0.55` (`ICI = 0.017–0.025`, `Cal_Slope = 0.81–0.90`), whereas `M5a` over-predicts risk in the top octile (`predicted ~ 0.60` vs. `observed ~ 0.40` in LOSO). Notice also that pure pre-anthesis weather predictions rarely exceed `0.60–0.65`, reflecting irreducible uncertainty before post-anthesis weather and cultivar susceptibility are realized.
* **High variability across individual years and states** ([loyo_by_year.csv](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/loyo_by_year.csv), [loso_by_state.csv](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/loso_by_state.csv), [fig3_loso_state_transportability.png](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/figures/fig3_loso_state_transportability.png)):
  * Across the 50 grouped `state × year` folds, `M2` fold-level AUC has `median = 0.677` with wide `IQR = 0.196` (`range 0.206–0.967`), and `Brier median = 0.183` (`IQR = 0.048`).
  * Across well-sampled LOYO years ($n \ge 15$, 14 years), `M2` discriminates strongly in major contrast years (`2012`: `AUC = 0.949`; `2001`: `0.879`; `2003`: `0.789`; `2009`: `0.761`; `2014`: `0.718`; `2000`: `0.711`), but fails in `2002` (`AUC = 0.218`, extreme July Northern Plains heatwave where Carrington ND had `S = 15.6%` despite high `VPD`) and `2013` (`AUC = 0.285`).
  * Across LOSO states ([fig3_loso_state_transportability.png](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/figures/fig3_loso_state_transportability.png)), `M2` discriminates well within `SD` (`0.793`), `NE` (`0.788`), `PA` (`0.750`), `OH` (`0.737`), and `IN` (`0.702`), but **systematically under-predicts prevalence in high-incidence Corn Belt states** (`MO`: observed `63.3%` vs. predicted `24.7%`; `IN`: `43.2%` vs. `24.5%`) and **over-predicts risk (~17–38%) in the 4 zero-event states** (`WI, NY, DE, AR`) and low-event states (`PA = 8.7%`, `MN = 6.1%`, `MI = 4.0%`).

---

## 4. Pre-Specified Sensitivity Analyses (`S1`–`S5`)

1. **Exposure-window sensitivity (`S1`, [fig2_window_sensitivity.png](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/figures/fig2_window_sensitivity.png)):**
   * For additive `T + RH`, predictive skill peaks sharply in the **7-day window `[-7, 0]`** (`LOYO AUC = 0.649, BSS = 5.6%`; `LOSO AUC = 0.648, BSS = 6.3%`) and declines gradually as the window widens to `10 d`, `14 d`, and `15 d` (`LOYO AUC = 0.637, BSS = 3.9%`), showing that **proximal moisture right before anthesis** carries more information than 2-week mean RH.
   * Conversely, single-variable joint threshold counts (`TRH: 15 <= T <= 30 & RH >= 80%`) perform poorly across all windows (`LOYO AUC = 0.555–0.584`, `BSS = 0.9–1.4%`), peaking mildly at `14–15 d` (`0.584`) before degrading at `30 d` (`0.569`, `LOSO BSS = -0.7%`)—confirming that hard binary temperature/RH step cutoffs discard substantial continuous psychrometric information!
2. **Outcome threshold sensitivity (`S2`, `output/sens_s2_thresholds.csv`):** Model ranking (`M2 > M3 ~ M1`) and relative probability skill are stable across `S >= 5%` (`M2 LOYO/LOSO BSS = 4.7% / 6.3%`), `S >= 10%` (`6.8% / 6.3%`), `S > 10%` (`6.6% / 5.9%`), and `S >= 15%` (`5.6% / 5.5%`; `LOYO AUC = 0.652`).
3. **UTC `12H` ("overnight") artifact, strict pre-flowering lead time, and post-anthesis benchmark (`S3`):**
   * Replacing `24H` predictors with `12H` UTC-shifted `"overnight"` predictors consistently **degrades** temporal validation (`PRE10` LOYO AUC drops from `0.645` to `0.637`; `PRE15 TRH80` drops from `0.584` to `0.571`), corroborating our audit finding of UTC timezone distortion.
   * Forecasting **5 days prior to anthesis** (`window_end_day <= -5`: `VPD.L635.CHD.1 [-15,-5] + T.A.2 [-20,-10]`) drops `LOYO AUC` from `0.671` (`M2r`) to `0.616` (`LOSO AUC = 0.604, BSS = 2.5%`), and forecasting **10 days prior** (`<= -10 d`) drops `LOYO AUC` to `0.593` (`LOSO BSS = -0.3%`), proving that weather during the final 5–10 days before flowering is indispensable.
   * Ultra-early barometric pressure (`P.A.3 [-60,-50] + P.A.4 [-80,-70]`) has near-random discrimination (`LOYO AUC = 0.564`).
   * **Post-anthesis weather comparison (`[0, +10 d]`):** Even a 2-term post-anthesis weather model (`T.A.4 + RH.A.2`: `LOYO AUC = 0.637, BSS = 5.5%`; `LOSO AUC = 0.639, BSS = 6.5%`) or combined pre+post 3-term model (`LOYO AUC = 0.644`) achieves **similar modest discrimination (`~0.64–0.67`)** when host factors are omitted!
4. **Environment deduplication ($N = 545$) and agronomic covariates (`S4`):**
   * Deduplicating to the `545` unique weather environments (`any_epid10`, `171` events) yields nearly identical slopes (`M1`: `+0.0225` vs `+0.0056` for `T`, `+0.0862` vs `+0.0926` for `RH`) and slightly higher environment-level discrimination (`M2 LOYO AUC = 0.672, BSS = 7.9%`; `LOSO AUC = 0.677, BSS = 7.3%`).
   * **Crucial finding on unmodeled host/residue variance:** Agronomic factors known at planting (`resist + corn` alone, zero weather!) achieve `LOYO AUC = 0.649, BSS = 7.7%`—comparable to weather alone! Combining `M2` weather with `resist + corn` (`N = 995`) boosts **`LOYO AUC` from `0.666` to `0.723` (`BSS` nearly doubles from `6.8%` to `13.6%`)** and **`LOSO AUC` from `0.655` to `0.712` (`BSS` from `6.3%` to `13.3%`)**!
5. **Subpopulation failure mode — Winter vs. Spring Wheat (`S5`):**
   * In **winter wheat** (`n = 734`, 16 states), `M2` maintains solid skill (`LOYO AUC = 0.662, BSS = 7.6%`; `LOSO AUC = 0.659, BSS = 7.9%`).
   * In **spring wheat** (`n = 265`, restricted to `ND, SD, MN`), pre-anthesis weather models collapse (`LOYO AUC = 0.568–0.572, BSS = -2.6%`; `LOSO AUC = 0.575–0.598, BSS = -1.3% to -5.3%`). Cluster influence (`DFBETAs` across all 142 state-years) is well-behaved (`max |DFBETA| = 0.98` on `M2` for `OH_2003`; excluding dominant state `ND` [265 rows] slightly *increases* `M2` `LOYO AUC` to `0.679`).

---

## 5. Final Recommended Model

Balancing epidemiological plausibility, strict parsimony, cluster-robust parameter stability, out-of-year and out-of-state calibration, and Brier skill—rather than apparent in-sample AUC—we recommend **Model `M2r`** (the 2-parameter parsimonious reduction of pre-specified `M2`, visualized in [fig5_final_m2r_risk_surface.png](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/output/figures/fig5_final_m2r_risk_surface.png)), with **Model `M2`** (`3` parameters) as the top unreduced pre-specified model and **Model `M0`/`M0r`** (`RH7`) as a nearly equivalent 1-variable operational fallback:

$$\text{logit}\big(\Pr(S_i \ge 10\%)\big) = -1.4696 - 2.8338\,\text{VPD.A.1}_i + 0.1507\,\text{T.A.2}_i$$

* **Complexity:** **2 weather predictor terms** (`2` estimated slope parameters + `1` intercept = `3` total parameters; $\text{VIF} = 1.05$).
* **Out-of-sample performance:** `LOYO AUC = 0.671` (`Brier = 0.185`, `BSS = +7.8%`, `Cal_Slope = 0.894`, `Cal_Int = +0.008`), `LOSO AUC = 0.660` (`Brier = 0.187`, `BSS = +7.2%`, `Cal_Slope = 0.807`, `ICI = 0.019`), and `5×10 Grouped CV AUC = 0.661` (`BSS = +7.2%`).
* **Honest epidemiological interpretation:** Pre-anthesis weather alone provides **modest, statistically real, well-calibrated baseline risk stratification** (`AUC ~ 0.66–0.67`, ~7–8% Brier error reduction over base rate) in U.S. winter wheat, driven by warm pre-heading temperatures (`20–10 d` pre-anthesis) followed by humid/low-VPD conditions (`10–0 d` pre-anthesis), **but is insufficient as a standalone high-precision classifier** without incorporating cultivar resistance, local inoculum/residue context, and spring-wheat-specific or post-anthesis infection conditions.
