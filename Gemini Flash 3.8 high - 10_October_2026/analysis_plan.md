# Analysis Plan: Parsimonious Pre-Anthesis Predictive Modeling of Fusarium Head Blight Risk

**Author:** Autonomous Epidemiological Analyst  
**Date:** October 10, 2026  
**Document Status:** Pre-Modeling Protocol (Formulated Prior to Fitting Predictive Models)  
**Dataset Reference:** Zenodo Record [10.5281/zenodo.23189372](https://zenodo.org/records/23189372) (`FHBVer2.parquet`)  

---

## 1. Prediction Objective and Intended Operational Use

### 1.1 Objective
The primary epidemiological objective is to develop, critically evaluate, and validate a parsimonious, scientifically defensible statistical model for predicting the probability of a Fusarium head blight (FHB) epidemic in wheat, relying **strictly and exclusively on weather and agronomic information available no later than wheat anthesis** (flowering, Zadoks GS 60–65).

### 1.2 Intended Operational Use
In commercial wheat production, chemical control of FHB (primarily using demethylation inhibitor [DMI] triazole or succinate dehydrogenase inhibitor [SDHI] fungicides) must be applied during early flowering to protect vulnerable extruded anthers from *Fusarium graminearum* infection. Once visible head blight symptoms appear (2–3 weeks post-flowering), fungicides are ineffective. 

Consequently, an operational disease warning tool must issue risk assessments at or just before anthesis. The model developed here is intended to function as an early-warning risk advisory tool that informs growers whether prophylactic fungicide application is economically warranted.

---

## 2. Response Variable Formulation

### 2.1 Primary Prediction Target
The primary response is a binary epidemic indicator derived from the continuous FHB severity/index variable `S` (symptomatic spikelets as a percentage):
$$Y = \begin{cases} 1, & \text{if } S \ge 10.0\% \quad \text{(Epidemic event)} \\ 0, & \text{if } S < 10.0\% \quad \text{(Non-epidemic)} \end{cases}$$

### 2.2 Epidemiological Justification
A field severity threshold of $10\%$ represents the recognized standard in wheat pathology and the US Wheat & Barley Scab Initiative (USWBSI; De Wolf et al., 2003). At and above $10\%$ severity:
- Significant grain yield reductions occur.
- Test weights drop below market standards.
- Deoxynivalenol (DON / vomitoxin) accumulation frequently exceeds advisory thresholds (e.g., 1–2 ppm in commercial grain milling).
In the audited dataset, $S \ge 10.0\%$ yields 273 epidemic events ($27.33\%$ prevalence) and 726 non-events across $N=999$ plots, providing an effective event rate suitable for stable parameter estimation.

---

## 3. Epidemiological Reasoning for Candidate Predictors

### 3.1 Biological Mechanisms of *Fusarium graminearum*
Predictor selection must be anchored in the biology of the disease cycle rather than automated data dredging:
1. **Perithecial Maturation & Inoculum Dynamics:** Overwintered *F. graminearum* perithecia on crop residue require moisture and warmth over a 1-to-2 week period preceding heading to mature and develop viable ascospores.
2. **Spore Release & Atmospheric Dispersal:** Ascospore discharge is actively triggered by rain events and elevated relative humidity, especially during overnight and early morning hours.
3. **Inoculum Deposition & Infection:** For infection to occur at flowering, extruded anthers must remain wet or in saturated relative humidity ($\text{RH} \ge 80-90\%$) for at least 12–24 hours under favorable temperatures ($15-30^\circ\text{C}$).

### 3.2 Candidate Weather Predictor Pool (Strict Pre-Anthesis Restriction)
To prevent temporal information leakage, all candidate weather predictors are strictly selected from the 174 variables where $win\_end\_period \in \{\text{'anthesis'}, \text{'pre'}\}$. All post-anthesis ($N=137$) and spanning pre-post ($N=18$) variables are excluded.

The candidate weather predictors represent two complementary atmospheric dimensions:
- **Atmospheric Moisture Dimension:**
  - `RH.A.PRE7.12H`: Mean overnight (20:00–08:00 UTC) relative humidity over the 7 days immediately preceding anthesis. Overnight humidity is the primary driver of dew formation, ascospore discharge, and vegetative fungal survival.
  - `RH7` (`RH.A.PRE7.24H`): Mean 24-hour daily relative humidity over the 7 days pre-anthesis.
  - `DD.A.PRE7.12H`: Mean overnight dewpoint depression ($T - D$) over the 7 days pre-anthesis (inversely related to saturation).
- **Thermal and Joint Conduciveness Dimension:**
  - `T.9T30.PRE7.24H`: Number of hours with air temperature between $9^\circ\text{C}$ and $30^\circ\text{C}$ in the 7 days pre-anthesis (representing non-limiting thermal conditions for *Fusarium* development).
  - `TRH.9T30nRHG80.PRE7.24H`: Number of hours satisfying joint conducive conditions ($9 \le T \le 30^\circ\text{C}$ and $\text{RH} \ge 80\%$) in the 7 days pre-anthesis.
  - `T.MINMAXDIFF.1`: Diurnal temperature range ($T_{\text{max}} - T_{\text{min}}$) over the 20 days pre-anthesis (narrow diurnal ranges indicate overcast, humid, precipitation-prone weather).

### 3.3 Collinearity Management
As established in `data_audit.md`, adjacent window lengths (e.g. 5d vs 7d vs 10d vs 14d) exhibit pairwise correlations exceeding $r = 0.90-0.99$. To prevent severe variance inflation:
- Never include multiple window lengths of the same weather metric in a single model.
- Select a biologically focused reference window (7 days pre-anthesis, reflecting immediate pre-flowering inoculum build-up) and assess 10-day and 14-day windows via sensitivity analyses.
- Ensure any multi-variable specification combines distinct physical dimensions (e.g., moisture duration + thermal range), with variance inflation factors (VIF) explicitly monitored.

---

## 4. Model-Building Strategy and Complexity Control

### 4.1 Primary Framework
Standard multivariable **binary logistic regression** is the principal modeling framework:
$$\log\left(\frac{P(Y=1 \mid \mathbf{x})}{1 - P(Y=1 \mid \mathbf{x})}\right) = \beta_0 + \sum_{j=1}^p \beta_j x_j$$

### 4.2 Parameter Budget and Parsimony
- **Mandatory Constraint:** At most **three weather predictor terms** in the final model.
- **Degrees of Freedom / EPV:** With 273 events (and 161 independent epidemic environments), a budget of 1 to 3 predictor parameters yields an effective EPV $> 50$, well above the threshold where overfitting or parameter instability typically occurs.

### 4.3 Planned Model Specifications
1. **Model 1 (Baseline Parsimonious Model - 1 Weather Term):**
   A minimal, transparent logistic regression model driven by pre-anthesis overnight moisture:
   $$\text{logit}(P(Y=1)) = \beta_0 + \beta_1 \cdot \text{RH.A.PRE7.12H}$$
   - Number of weather parameters: 1.
2. **Model 2 (Bivariable Weather Model - 2 Weather Terms):**
   Incorporating both moisture saturation and thermal favorability:
   $$\text{logit}(P(Y=1)) = \beta_0 + \beta_1 \cdot \text{RH.A.PRE7.12H} + \beta_2 \cdot \text{T.9T30.PRE7.24H}$$
   - Number of weather parameters: 2.
3. **Model 3 (Joint Interaction Specification - 3 Weather Terms):**
   Evaluating non-linear synergy between moisture and thermal favorability:
   $$\text{logit}(P(Y=1)) = \beta_0 + \beta_1 \cdot \text{RH.A.PRE7.12H} + \beta_2 \cdot \text{T.9T30.PRE7.24H} + \beta_3 \cdot (\text{RH.A.PRE7.12H} \times \text{T.9T30.PRE7.24H})$$
   - Number of weather parameters: 3 (strictly within budget).
4. **Model 4 (Host Resistance-Augmented Model - Epidemiological Alternative):**
   In plant pathology, disease expression requires host susceptibility. We evaluate how weather predictions interface with cultivar resistance:
   $$\text{logit}(P(Y=1)) = \beta_0 + \beta_1 \cdot \text{RH.A.PRE7.12H} + \beta_2 \cdot \text{T.9T30.PRE7.24H} + \sum_{k=1}^3 \gamma_k \mathbb{I}(\text{resist} = k)$$
   - Weather parameters: 2; Host parameters: 3.
5. **Supplementary Exploratory Benchmark:**
   - Firth penalized logistic regression (to evaluate small-sample shrinkage).
   - Random Forest classifier (to test whether substantial non-linear interactions remain uncaptured by logistic regression).

---

## 5. Validation Design

### 5.1 Primary Validation Strategy: Leave-One-Year-Out Cross-Validation (LOYO-CV)
- **Design:** The dataset spans 32 distinct years (1982–2015). For each year $t \in \{1, \dots, 32\}$, the model is trained on all observations where $\text{year} \ne t$ and evaluated out-of-sample on observations from year $t$.
- **Rationale:** 
  - Resolves environmental clustering leakage: all plots in a given site-year remain together in the validation fold.
  - Replicates prospective operational forecasting: models trained on historical data are applied to an unseen future growing season.
  - Directly exposes temporal transferability and performance during extreme climatic anomalies (e.g., severe regional drought in 2012).

### 5.2 Secondary Validation Strategy: Grouped Cross-Validation by Environment
- Grouped 5-fold cross-validation clustering on `(year, state)` to assess stability under spatial-temporal cross-validation.

---

## 6. Performance Evaluation Metrics

Models will be compared out-of-sample on:
1. **Discrimination:**
   - Area Under the Receiver Operating Characteristic Curve (ROC AUC).
   - Operational classification metrics at probability cutoff $p = 0.30$ (reflecting the empirical baseline prevalence of ~27%): Sensitivity, Specificity, Positive Predictive Value (PPV), and Negative Predictive Value (NPV).
2. **Calibration:**
   - Brier Score: $BS = \frac{1}{N}\sum_{i=1}^N (\hat{p}_i - y_i)^2$.
   - Brier Skill Score relative to climatological prevalence: $BSS = 1 - BS / BS_{\text{ref}}$.
   - Calibration Intercept (target: 0.0) and Calibration Slope (target: 1.0) via logistic recalibration.
   - Decile calibration plots comparing mean predicted probability against observed event fraction.
3. **Inter-Annual Performance Variability:**
   - Distribution and IQR of annual out-of-fold AUC and Brier scores across validation years with sufficient event numbers ($N_{\text{events}} \ge 3$ and $N_{\text{nonevents}} \ge 3$).

---

## 7. Sensitivity Analyses

To evaluate robustness against arbitrary analytical choices, the following sensitivity checks are planned:
1. **Exposure Window Sensitivity:** Contrast 7-day vs. 10-day vs. 14-day pre-anthesis windows.
2. **Threshold Sensitivity:** Re-evaluate models under alternative epidemic thresholds ($S \ge 5.0\%$ and $S \ge 7.0\%$).
3. **Wheat Class Stratification:** Assess whether performance differs between winter wheat ($N=734$) and spring wheat ($N=265$).
4. **Influence of Severe Outlier Years:** Re-fit excluding extreme years (e.g., 2009 with $N=167$ plots or 2012 with 4% prevalence).

---

## 8. Summary of Pre-Specified Modeling Decisions

| Decision Area | Chosen Strategy | Scientific Rationale |
| :--- | :--- | :--- |
| **Response** | Binary $S \ge 10.0\%$ | Standard USWBSI economic threshold; 273 events, 726 non-events. |
| **Candidate Predictors** | Strictly pre-anthesis ($N=174$) | Zero temporal leakage; decisions must be made by flowering. |
| **Model Complexity** | 1 to 3 weather parameters | Defensible within effective environmental sample size ($EPV_{\text{env}} \approx 54$). |
| **Validation** | Leave-One-Year-Out (LOYO-CV) | Prevents clustering leakage; evaluates inter-annual transferability. |
| **Primary Framework** | Multivariable Logistic Regression | Transparent, interpretable, directly yields calibrated probabilities. |

*This protocol is formally frozen prior to model fitting.*
