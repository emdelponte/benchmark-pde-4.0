# Dataset Audit and Quality Assessment: Fusarium Head Blight (FHB) Matrix Version 2.1.0

**Author:** Autonomous Epidemiological Analyst  
**Date:** October 10, 2026  
**Dataset Source:** Zenodo Record [10.5281/zenodo.23189372](https://zenodo.org/records/23189372)  
**Primary Dataset File:** `FHBVer2.parquet`  
**Metadata Sources:** `FHBVer2DataDict.yaml`, `VariablesMetaData.csv`, `README.txt`, `FHBVer2Codebook.pdf`  

---

## 1. Executive Summary & Objective

This audit evaluates the structure, metadata consistency, epidemiological integrity, and predictive modeling readiness of the Fusarium head blight (FHB) dataset (Version 2.1.0) published by Denis A. Shah, Erick D. De Wolf, Pierce A. Paul, and Laurence V. Madden. 

The primary scientific objective of this project is to develop and critically evaluate a parsimonious, scientifically defensible predictive model for FHB epidemic risk using weather predictors available **strictly no later than wheat anthesis**. 

Before specifying or fitting any predictive models, this document establishes the empirical reality of the dataset: observational units, response characteristics, spatial-temporal structure, exposure timing, collinearity, clustering, and data quality limitations.

---

## 2. Dataset Provenance and Schema Integrity

### 2.1 Source Files and Documentation Cross-Check
The Zenodo record was accessed and all associated components were retrieved and verified:
- `FHBVer2.parquet` (1,025,846 bytes): Main data matrix containing 999 rows and 337 columns.
- `FHBVer2DataDict.yaml` (350,744 bytes): Comprehensive machine-readable data dictionary defining conventions, glossary, column definitions, units, types, and valid ranges.
- `VariablesMetaData.csv` (45,772 bytes): Structured tabular metadata detailing 329 weather-derived predictors, including origins, windows, time steps, and metrics.
- `README.txt` (6,022 bytes): Detailed provenance document describing version history, UTC conventions, and meteorological data acquisition.
- `FHBVer2Codebook.pdf` (1,666,701 bytes): Automated codebook generated via `dataMaid` detailing distributions.

### 2.2 Schema and Variable Cross-Verification
A programmatic cross-check between `FHBVer2.parquet`, `FHBVer2DataDict.yaml`, and `VariablesMetaData.csv` yielded the following findings:
1. **Column Dimension Match:** Exactly 337 columns in `FHBVer2.parquet` and exactly 337 column definitions in `FHBVer2DataDict.yaml`.
2. **Variable Partition:**
   - **8 Non-weather variables:** `id` (metadata identifier), `year` (calendar reference), `state` (spatial reference), `fdate` (temporal reference / anthesis date), `type` (wheat class), `resist` (cultivar resistance), `corn` (previous crop residue), and `S` (response variable).
   - **329 Weather-derived variables:** All 329 variables map 1:1 to rows in `VariablesMetaData.csv`.
3. **Canonical vs. Deprecated Aliases:**
   The YAML data dictionary documents 5 deprecated legacy variable aliases that were retained solely for backward compatibility with earlier literature (e.g., De Wolf et al., 2003):
   - `RH10` $\rightarrow$ canonical: `RH.A.2`
   - `RH9010` $\rightarrow$ canonical: `RH.G90.CHD.2`
   - `RH8010` $\rightarrow$ canonical: `RH.G80.CHD.2`
   - `TRH9010` $\rightarrow$ canonical: `TRH.15T30nRHG90.CHD.3`
   - `TRH8010` $\rightarrow$ canonical: `TRH.15T30nRHG80.CHD.3`
   Empirical verification confirmed that each deprecated variable is bitwise identical to its canonical counterpart ($r = 1.000$, difference $= 0.0$). None of these aliases will be utilized in new model specifications; furthermore, all 5 represent post-anthesis windows and are ineligible under our pre-anthesis constraint.
4. **Discrepancy and Ambiguity Reporting:**
   - **Absence of Pre-computed Binary Outcome:** While epidemiological literature and benchmark guidelines refer to predicting binary epidemic risk, `FHBVer2.parquet` contains only the continuous response variable `S` (FHB index / severity in %). No binary indicator is stored in the table. The binary epidemic outcome must be derived by thresholding `S` in accordance with established epidemiological standards.
   - **Time Step Terminology:** `README.txt` and `FHBVer2DataDict.yaml` clarify that the "overnight" (12H) period is defined as 20:00 UTC to 08:00 UTC the following morning (a fixed 12-hour period), *not* local astronomical sunset-to-sunrise. Because weather observations and flowering dates are recorded in UTC without adjustment to local solar time, diurnal phasing varies slightly by longitude across the 17 US states.

---

## 3. Observational Unit, Response Variable, and Epidemic Outcome

### 3.1 Observational Unit
The observational unit is a fungicide-untreated small field plot trial evaluated for Fusarium head blight severity, maintained by collaborators of the U.S. Wheat & Barley Scab Initiative (USWBSI). The dataset contains $N = 999$ complete plot-level observations spanning 1982 to 2015 across 17 US states.

### 3.2 Continuous Response Variable (`S`)
`S` represents the FHB index (disease severity on wheat heads, expressed as a percentage from 0.0 to 100.0%).
- **Sample Size ($N$):** 999
- **Missing Values:** 0 (0.0%)
- **Empirical Range:** 0.00% to 86.18%
- **Mean $\pm$ SD:** $8.81\% \pm 13.70\%$
- **Median (IQR):** $2.87\%$ ($0.20\%$ to $11.31\%$)
- **Distribution:** Heavily right-skewed with a substantial mass of near-zero values (25th percentile is 0.20%, and 10% of plots have $S = 0.00\%$).

### 3.3 Derivation of Binary Epidemic Outcome
In plant pathology and predictive modeling of FHB (specifically the foundational USWBSI framework established by De Wolf et al., 2003, and subsequent revisions), a **major epidemic** is defined as an FHB index of $S \ge 10.0\%$ (or $S > 10.0\%$). At this threshold, yield loss, test weight reduction, and deoxynivalenol (DON) mycotoxin contamination reach commercially unacceptable levels requiring proactive management decisions.

Evaluating threshold definitions on the empirical distribution:
- **$S \ge 10.0\%$:** 273 events (prevalence = 27.33%, 726 non-events).
- **$S > 10.0\%$:** 271 events (prevalence = 27.13%, 728 non-events). Exactly 2 observations have $S = 10.0\%$.
- **$S \ge 5.0\%$:** 395 events (prevalence = 39.54%, 604 non-events).
- **$S \ge 7.0\%$:** 343 events (prevalence = 34.33%, 656 non-events).
- **$S \ge 15.0\%$:** 202 events (prevalence = 20.22%, 797 non-events).

**Decision:** The standard primary threshold $S \ge 10.0\%$ is adopted as the documented binary epidemic response variable (`epidemic = 1` if $S \ge 10.0$, `0` otherwise). This provides 273 epidemic events and 726 non-events. Sensitivity to alternative thresholds ($S \ge 5\%$ and $S \ge 7\%$) will be assessed in robustness checks.

---

## 4. Geographic and Temporal Structure

### 4.1 Geographic Representation (17 States)
The dataset encompasses 17 states across the Great Plains, Midwest, and Mid-Atlantic wheat-growing regions of the conterminous United States:
- **North Dakota (ND):** 265 plots (26.5% of total data)
- **Illinois (IL):** 104 plots (10.4%)
- **Ohio (OH):** 99 plots (9.9%)
- **Maryland (MD):** 86 plots (8.6%)
- **Indiana (IN):** 81 plots (8.1%)
- **South Dakota (SD):** 75 plots (7.5%)
- **Kansas (KS):** 49 plots (4.9%)
- **Missouri (MO):** 49 plots (4.9%)
- **Pennsylvania (PA):** 46 plots (4.6%)
- **Minnesota (MN):** 33 plots (3.3%)
- **Wisconsin (WI):** 25 plots (2.5%)
- **Michigan (MI):** 25 plots (2.5%)
- **New York (NY):** 22 plots (2.2%)
- **Nebraska (NE):** 17 plots (1.7%)
- **Kentucky (KY):** 14 plots (1.4%)
- **Delaware (DE):** 5 plots (0.5%)
- **Arkansas (AR):** 4 plots (0.4%)

Epidemic prevalence varies substantially across states:
- Highest prevalence: Missouri (63.3%), Maryland (46.5%), Indiana (43.2%), South Dakota (36.0%), Ohio (30.3%), Illinois (28.8%), North Dakota (22.6%).
- States with zero recorded epidemics: Wisconsin ($N=25$, 0%), New York ($N=22$, 0%), Delaware ($N=5$, 0%), Arkansas ($N=4$, 0%).

### 4.2 Temporal Representation (1982–2015)
The dataset spans 34 calendar years (32 distinct years sampled):
- **Historical Era (1982–1999):** Only 61 observations total across 16 sampled years (average ~3.8 plots/year; ranging from 1 to 10 plots/year).
- **Modern USWBSI Coordinated Era (2000–2015):** 938 observations across 16 consecutive years (average ~58.6 plots/year).
  - Peak years: 2009 ($N=167$), 2014 ($N=88$), 2011 ($N=85$), 2012 ($N=85$), 2010 ($N=81$).
- Epidemic occurrence fluctuates sharply from year to year:
  - Severe epidemic years: 2001 (64.7% prevalence), 2003 (42.9%), 2009 (34.7%), 2011 (32.9%), 2004 (32.5%), 2015 (30.0%).
  - Disease-suppression years: 2007 (0.0% prevalence), 2012 (4.7% prevalence; coinciding with the historic North American Midwest drought), 2006 (6.3%).

---

## 5. Agronomic Covariates

The dataset contains three agronomic descriptors available at or before anthesis:
1. **Wheat Class (`type`):**
   - Winter wheat: 734 plots (73.5%), epidemic prevalence = 29.15% ($N_{\text{events}} = 214$).
   - Spring wheat: 265 plots (26.5%), epidemic prevalence = 22.26% ($N_{\text{events}} = 59$).
   - Confounding note: Spring wheat is completely restricted to northern states (170 in ND, 62 in SD, 33 in MN). All other 14 states grew exclusively winter wheat.
2. **Cultivar Resistance (`resist`):**
   - Susceptible (S): 412 plots (41.2%), prevalence = 32.04% ($N_{\text{events}} = 132$).
   - Moderately Resistant (MR): 239 plots (23.9%), prevalence = 12.97% ($N_{\text{events}} = 31$).
   - Moderately Susceptible (MS): 213 plots (21.3%), prevalence = 22.07% ($N_{\text{events}} = 47$).
   - Very Susceptible (VS): 135 plots (13.5%), prevalence = 46.67% ($N_{\text{events}} = 63$).
   - Note: Demonstrates strict monotonic decrease in epidemic risk from VS (46.7%) $\rightarrow$ S (32.0%) $\rightarrow$ MS (22.1%) $\rightarrow$ MR (13.0%).
3. **Corn Residue (`corn`):**
   - Absent (0): 647 plots (65.0%), prevalence = 25.04%.
   - Present (1): 348 plots (35.0%), prevalence = 31.61%.
   - Missing: 4 plots (0.40%).

---

## 6. Weather Variables and Temporal Exposure Windows

### 6.1 Breakdown of Weather Predictors
Of the 329 weather variables in `VariablesMetaData.csv`:
- **Pre-anthesis (`period == 'pre'`):** 174 variables.
- **Post-anthesis (`period == 'post'`):** 137 variables.
- **Pre-post spanning anthesis (`period == 'pre-post'`):** 18 variables.

Under the mandatory prediction constraint—predicting epidemic risk strictly **no later than wheat anthesis**—all 137 post-anthesis variables and all 18 pre-post variables must be **strictly excluded** from candidate predictor pools to prevent temporal information leakage.

### 6.2 Pre-Anthesis Weather Predictors ($N = 174$)
All 174 pre-anthesis predictors end at or prior to anthesis ($win\_end\_period \in \{\text{'anthesis'}, \text{'pre'}\}$):
- 151 variables end exactly at anthesis ($win\_end\_day = 0$).
- 23 variables end prior to anthesis ($win\_end\_day \in \{5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70\}$ days prior to day 0).

Categorization by meteorological variable type:
1. **TRH (Combined Temperature and Relative Humidity, $N=48$):** Duration of hours (over 24H or overnight 12H) satisfying joint thermal and moisture thresholds (e.g., $9 \le T \le 30^\circ\text{C}$ and $\text{RH} \ge 80\%$).
2. **T (Air Temperature, $N=41$):** Means, hours within thermal ranges, standard deviation (`T.SD.1`), and diurnal range (`T.MINMAXDIFF.1`).
3. **RH (Relative Humidity, $N=29$):** Daily mean RH, overnight mean RH, hours $\text{RH} \ge 80\%$ or $\ge 90\%$.
4. **VPD (Vapor Pressure Deficit, $N=26$):** Daily mean VPD, hours $\text{VPD} \le 0.635$ kPa or $\le 1.1$ kPa.
5. **TDD / DD (Dewpoint Depression, $N=16$):** Daily mean and overnight mean temperature minus dewpoint ($T - D$).
6. **D (Dewpoint Temperature, $N=7$):** Daily mean dewpoint and diurnal range.
7. **P (Barometric Pressure, $N=7$):** Daily mean barometric pressure over extended pre-anthesis windows (20 to 80 days).

---

## 7. Dependencies, Clustering, and Effective Sample Size

### 7.1 Environmental Clustering
An essential structural property of this field-plot dataset is that multiple plots were evaluated within the same research trial, location, year, and flowering date:
- **Total Rows:** $N = 999$.
- **Distinct Environments (`year`, `state`, `fdate`):** 492.
- **Identical Weather Profiles:** 454 rows share an identical weather profile with at least one other row in the dataset (differing only in cultivar resistance, corn residue, or plot replication).
- **Environment-Level Epidemic Occurrence:**
  - Environments with $\ge 1$ epidemic plot: 161 of 492 (32.7%).
  - Environments with mean severity $S \ge 10\%$: 131 of 492 (26.6%).
  - Environments where 100% of plots experienced an epidemic: 98 environments.
  - Environments with discordant plot outcomes (e.g., epidemic in susceptible cultivar, non-epidemic in resistant cultivar): 63 environments.
  - Environments with 0 epidemics across all plots: 331 environments.

### 7.2 Effective Sample Size and Events-per-Parameter Budget
If observations were independent, $N=999$ with 273 events would yield an Events-Per-Variable (EPV) ratio of $\sim 91$ for a 3-parameter model. However, because weather varies strictly at the environment level (492 distinct environments, 161 epidemic environments, 32 years), the **effective sample size for weather predictors is constrained by the number of independent weather realizations**, not the 999 plot rows.

At the environment level:
- Number of independent macro-environments: $\sim 492$.
- Number of epidemic environments: 161.
- Effective EPV for a 3-weather-parameter model: $161 / 3 \approx 53.7$, which comfortably exceeds standard rules of thumb (e.g., $\text{EPV} \ge 10-20$), confirming that a 2-to-3 parameter logistic regression model is well-supported without risk of gross parameter instability.

### 7.3 Information Leakage Risk in Validation
Because 454 plots share identical weather with other plots in the same trial, **standard random $k$-fold cross-validation or random observation-level train/test splitting will suffer from severe information leakage**. Random splitting would place plots with identical weather conditions and common unmeasured trial-specific factors into both training and validation sets, yielding artificially optimistic discrimination and calibration metrics.

**Validation Imperative:** Grouped validation that respects natural clustering boundaries is required:
1. **Leave-One-Year-Out Cross-Validation (LOYO-CV):** Validates the model's ability to forecast future years across unseen climatic conditions.
2. **Leave-One-Environment-Out / Grouped-CV:** Validates predictions across unseen spatial-temporal clusters.

---

## 8. Predictor Collinearity and Exposure Window Redundancy

Pairwise correlation analysis across candidate pre-anthesis weather predictors reveals extreme multicollinearity:
1. **Window-to-Window Redundancy:**
   - 14-day vs. 15-day pre-anthesis RH: $r = 0.993$.
   - 14-day vs. 15-day pre-anthesis TRH: $r = 0.991$.
   - 5-day vs. 7-day pre-anthesis RH: $r = 0.941$.
   - 7-day vs. 10-day pre-anthesis TRH: $r = 0.820$.
2. **Moisture Metric Redundancy:**
   - Mean overnight RH (`RH.A.PRE7.12H`) and overnight dewpoint depression (`DD.A.PRE7.12H`): $r = -0.965$.
   - Mean RH and Vapor Pressure Deficit (`VPD`): $|r| > 0.85$.
3. **Biological Implications:**
   Attempting automated stepwise selection across 174 candidate variables will merely identify arbitrary idiosyncratic noise differences between near-identical windows (e.g. 14-day vs 15-day). The selection of exposure windows must therefore be anchored in biological mechanisms of *Fusarium graminearum* perithecial maturation and infection, rather than uncorrected empirical optimization.

---

## 9. Data Quality Assessment and Identified Constraints

| Attribute | Finding | Assessment / Decision |
| :--- | :--- | :--- |
| **Completeness** | 0 missing values across all 329 weather variables and continuous response `S`. Only `corn` has 4 missing values (0.40%). | Outstanding completeness; no imputation needed for weather or response. |
| **Parquet Schema** | 337 columns, matching YAML and Metadata CSV. | Schema verified and consistent. |
| **Response Variable** | Continuous $S$ (0.0 to 86.18%); no binary column in file. | Derived binary indicator at $S \ge 10.0\%$ justified by USWBSI epidemiological criteria. |
| **Timing Constraint** | 137 post-anthesis and 18 pre-post variables. | Filtered out; modeling pool strictly limited to 174 pre-anthesis variables. |
| **Clustering** | 492 environments, 454 identical weather rows. | Requires grouped validation (e.g., LOYO-CV) and cluster-robust standard errors. |
| **Parsimony Budget** | Maximum 3 weather predictor terms. | Supported by effective sample size ($EPV_{\text{env}} \approx 54$). |
| **Collinearity** | Extreme ($r > 0.95$ across adjacent windows and moisture metrics). | Preclude automated multi-variable mining; select biologically distinct predictors. |

---

## 10. Audit Conclusion

The dataset is high quality, complete, and provides rich meteorological and epidemiological characterization. However, reliable predictive modeling requires strict adherence to three principles:
1. **Zero Information Leakage:** Restrict candidate predictors exclusively to pre-anthesis windows ($N=174$) and evaluate models exclusively via grouped/leave-one-year-out validation.
2. **Defensible Parsimony:** Limit models to $\le 3$ biologically motivated weather predictor terms (representing distinct atmospheric dimensions such as moisture duration and thermal favorability).
3. **Cluster-Aware Assessment:** Account for the multi-plot trial structure in calibration, inference, and performance assessment.

This audit is documented prior to model development. Next step: formalize the modeling strategy in `analysis_plan.md`.
