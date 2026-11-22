# Dataset Description, Metadata Cross-Check, and Structural Audit (`FHBVer2` v2.1.0)

## 1. Data Acquisition and File Inventory

Files were retrieved directly from Zenodo record **23189372** (*Field-plot dataset of Fusarium head blight (FHB) severity in wheat: fungicide-untreated small plots across the United States*, Version 2.1.0, DOI: `10.5281/zenodo.23189372`, published 2026-10-06):

| File | Size (bytes) | Role in Audit | Dimensions / Structure |
| :--- | ---: | :--- | :--- |
| `data/FHBVer2.parquet` | 1,025,846 | Primary analysis dataset | 999 rows × 337 columns |
| `data/FHBVer2DataDict.yaml` | 350,744 | Primary machine-readable data dictionary | Glossary, 6 conventions, 337 column specs |
| `data/README.txt` | 6,022 | Release notes, UTC conventions, nomenclature | Version 2.1.0 & 2.0.0 documentation |
| `data/VariablesMetaData.csv` | 45,772 | Weather predictor metadata table | 329 weather rows × 14 metadata attributes |
| `data/FHBVer2Codebook.pdf` | 1,666,701 | `dataMaid` summary codebook | 242 pages; variable summaries for 337 cols |
| `data/FHBVer2.rds` & `.csv` | 656,580 / 2,734,991 | Companion formats cross-checked for consistency | **999 rows × 338 columns** (discrepancy below) |

All programmatic audit checks are reproducible via [01_data_audit.R](file:///c:/Users/edelp/OneDrive/Documentos/GitHub/benchmark-pde-4.0/Gemini%20Carbon%20Medium%20-%2022_November_2026/code/01_data_audit.R).

---

## 2. Documentation Cross-Check: Inconsistencies, Ambiguities, and Missing Metadata

Cross-checking `FHBVer2.parquet` against `FHBVer2DataDict.yaml`, `README.txt`, `VariablesMetaData.csv`, `FHBVer2Codebook.pdf`, and the companion `.rds`/`.csv` files revealed **six substantive discrepancies and ambiguities** that must be documented rather than silently resolved:

### 2.1 Omission of Sub-State `location` in Parquet, YAML, and PDF Codebook vs. RDS/CSV
* `README.txt` (lines 8 and 113) states that in Version 2.1.0 *"Unchanged: data values, variable names, types, csv/rds files"* and describes `FHBVer2.csv` as having *"999 observation rows and 337 columns."*
* **Actual schema discrepancy:** `FHBVer2.parquet`, `FHBVer2DataDict.yaml`, and `FHBVer2Codebook.pdf` contain **337 columns**, whereas `FHBVer2.rds` and `FHBVer2.csv` contain **338 columns**—the extra column is `location` (a character vector naming 80 unique sub-state trial locations such as `"Wooster"`, `"Fargo"`, `"Brookings"`). All 337 shared columns have identical values (maximum numeric difference = `0`) and identical factor levels across `.parquet` and `.rds`.
* **Analytical consequence:** Because `FHBVer2.parquet` is the mandated primary dataset, `location` is unavailable in the primary schema. However, cross-checking in the audit shows that unique pre-anthesis weather vectors (`545` distinct profiles) map almost one-to-one to `(state, location, year, fdate)` combinations (`548` distinct combinations in `.rds`; only 3 weather profiles are shared across nearby locations on the same `fdate`, and 0 span multiple states or flowering dates).

### 2.2 Absence of an Explicit Binary Epidemic Column in the Dataset and YAML Dictionary
* The benchmark problem requires predicting *"the documented binary epidemic outcome."*
* **Actual schema finding:** Neither `FHBVer2.parquet` (nor `.rds`/`.csv`) nor `FHBVer2DataDict.yaml` contains a binary outcome variable. Only one response variable exists (`category: response`): continuous **`S`**, defined as *"FHB index, or severity of FHB symptoms on the spike"* (`unit: percent`, range `0.00` to `86.18`, valid range `0.0` to `100.0`). Neither `README.txt` nor `FHBVer2DataDict.yaml` specifies a numeric epidemic threshold.
* **Resolution for modeling:** In U.S. wheat FHB epidemiology and USWBSI risk-modeling studies (the source program documented in `README.txt`), **`S >= 10`%** (10% mean spike severity in fungicide-untreated plots) is the canonical operational threshold distinguishing an economically damaging FHB epidemic from background/low disease. We adopt $Y = \mathbb{I}(S \ge 10\%)$ as the primary binary outcome and pre-specify sensitivity analyses at $S \ge 5\%$ and $S \ge 15\%$ (as well as noting $S > 10\%$, which differs by only 2 exact `S == 10.0` observations).

### 2.3 Off-by-One Window Length (`win_length`) Across All 329 Weather Variables
* In `VariablesMetaData.csv`, `win_length` is recorded as $|\text{win\_end\_day} - \text{win\_start\_day}|$ (e.g., `5` for `PRE5` `[-5, 0]`, `7` for `PRE7` `[-7, 0]`, `10` for `T.A.1` `[-25, -15]`).
* However, `FHBVer2DataDict.yaml` (`conventions: window_day_bounds`) documents that windows are **closed intervals** `[window_start_day, window_end_day]` including both endpoints, so actual window duration is $n_{\text{days}} = \text{window\_end\_day} - \text{window\_start\_day} + 1$.
* **Empirical verification:** For all **329** weather variables, `closed_n_days - win_length == 1`. In `FHBVer2.parquet`, **39 of 218** bounded count variables empirically exceed the naive bound `win_length × (1, 12, or 24)` while respecting the YAML closed-interval bound `valid_range.max` (e.g., `T157` and `T15307` over `[-7, 0]` reach `192 = 8 × 24` hours > `168`; `T.9T30.PRE5.24H` reaches `144 = 6 × 24` hours > `120`; `RH.G70.CD.2` reaches `11` days > `10`).

### 2.4 Physically Inverted "Overnight" (`12H`) Weather Variables Due to Unadjusted UTC Timestamps
* `README.txt` (lines 16, 29–30) notes that all weather timestamps and `fdate` are in **UTC, not adjusted to local time zone**, defining a 24 h day as `00 UTC to 23 UTC` and a 12 h daily period as `"from 20 UTC to 07 UTC"` (described in `FHBVer2DataDict.yaml` as `"20:00 to 08:00 the next day"`—i.e., 12 hourly stamps from 20:00 through 07:00 UTC).
* **Physical/meteorological distortion:** Across the 17 conterminous U.S. states during May–July (`UTC-4` EDT and `UTC-5` CDT), `20:00–08:00 UTC` corresponds to **15:00–03:00 CDT (3:00 PM to 3:00 AM)** and **16:00–04:00 EDT (4:00 PM to 4:00 AM)**. Thus, variables labeled `"overnight"` in `FHBVer2DataDict.yaml` actually include peak late-afternoon heat and evaporative demand while excluding the coolest, most humid pre-dawn dew hours (`03:00–07:00` local time)!
* **Empirical proof in `FHBVer2.parquet`:** Across the dataset, `"overnight" (12H)` relative humidity is systematically **lower (drier)** than full 24-hour relative humidity in **79.1% to 86.2%** of observations (e.g., `RH.A.PRE10.12H` mean = `68.15%` vs. `RH.A.PRE10.24H` mean = `69.91%`), and `"overnight"` VPD (`VPD.A.PRE10.12H` mean = `0.801 kPa`) is **higher** than 24-hour VPD (`VPD.A.1` mean = `0.741 kPa`) in **79.7%** of observations—the exact opposite of true local nighttime meteorology. Moreover, because the fixed UTC window shifts local solar phase between Eastern (`DE, MD, PA, NY, OH`) and Central/Plains (`ND, SD, NE, KS`) states, `12H` variables introduce longitudinal measurement artifact.

### 2.5 Anthesis Day (`day 0`) Prediction-Timing Boundary Ambiguity
* `README.txt` defines the anthesis reference point as `00 UTC` on `fdate` (`19:00 CDT` / `20:00 EDT` on the evening *before* `fdate`). Any `analysis_period == "pre"` variable with `window_end_day == 0` includes `00:00–23:00 UTC` on `fdate` (`19:00 CDT` on `fdate - 1` through `18:00 CDT` on `fdate`) for `24H` variables, and up to `07:00 UTC` on `fdate + 1` (`02:00 CDT` the morning after `fdate`) for `12H` variables.
* Consequently, `window_end_day == 0` variables are operationally available at the end of the flowering date (for next-morning fungicide application decisions at Feekes 10.5.1), whereas early-morning decisions on `fdate` itself would require truncating weather ~12 hours earlier (or using forecasted day-0 weather). By contrast, `pre-post` (`18` variables, `window_end_day` 5 to 10 d post-anthesis) and `post` (`137` variables, `window_end_day` 5 to 20 d post-anthesis) incorporate future weather unavailable at anthesis and must be strictly excluded.

### 2.6 Deprecated Duplicate Columns, Unflagged Exact Complements, and Minor YAML Omissions
* **Deprecated aliases:** Five post-anthesis legacy columns (`RH10`, `RH9010`, `RH8010`, `TRH9010`, `TRH8010`) are exact numerical duplicates (`max |diff| = 0`, `r = 1.0`) of canonical columns (`RH.A.2`, `RH.G90.CHD.2`, `RH.G80.CHD.2`, `TRH.15T30nRHG90.CHD.3`, `TRH.15T30nRHG80.CHD.3`), properly flagged `deprecated: true` in `FHBVer2DataDict.yaml` (all 5 are post-anthesis).
* **Unflagged exact linear dependencies (`r = -1.0` and exact partitions):**
  * `T157 + T.L15.PRE7.24H == 192` identically in all 999 rows (`r = -1.0`), and `T1510 + T.L15.POST10.24H == 264` identically (`r = -1.0`).
  * `T157 - T15307 - T.G30.PRE7.24H == 0` in all 999 rows (exact three-variable collinearity).
  * `T.L15.PREk.24H + T.15T30.PREk.24H + T.G30.PREk.24H == 24 × (k + 1)` identically (`144, 264, 360, 384`) for `k = 5, 10, 14, 15`.
* **Minor YAML metadata omissions:** `INT3` lacks a `condition` field in `FHBVer2DataDict.yaml` (it has `derivation: T15307 * TRH9010`), and `FHBVer2Codebook.pdf` (page 1) misreports `corn` as having `3` unique values because `dataMaid` counted `NA` alongside `0` and `1` (corrected to `2` unique values on page 21).

---

## 3. Structural and Exploratory Dataset Audit

### 3.1 Observational Unit, Sample Size, and Hierarchical Clustering
* **Observational unit:** A single fungicide-untreated small research plot of wheat assessed for FHB severity (`N = 999` plots, `id` 1 to 999).
* **Environmental / weather unit:** Across the 999 plots, there are only **545 unique weather profiles** (identical across both all 329 weather variables and the 174 pre-anthesis weather variables). Multiple plots within the same trial/anthesis date—typically cultivars differing in resistance (`resist`) or residue management (`corn`)—were linked to the exact same nearest weather station and `fdate`:
  * `280` weather profiles appear once (`1` plot);
  * `265` weather profiles are replicated across `2` to `8` plots (`149` with 2 plots, `69` with 3, `36` with 4, `9` with 6, `2` with 8 plots, totaling `719` plots).
* **Higher-level grouping:** Observations span **17 U.S. states**, **32 calendar years** (1982–2015; note `1983` and `1985` have no data), **142 `state × year` combinations**, and **492 `(state, year, fdate)` combinations** in Parquet (`80` sub-state locations and `253` location-years in `.rds`).

### 3.2 Distribution of Continuous Severity (`S`) and Binary Epidemic Outcome
* **Continuous `S` (% FHB index):** Highly right-skewed (`skewness = 2.44`), with `mean = 8.81%`, `SD = 13.70%`, `min = 0.00%` (`186` exact zeros, `18.62%`; `364` plots `< 1%`, `36.44%`), `25th pct = 0.20%`, `median = 2.87%`, `75th pct = 11.31%`, `90th pct = 26.62%`, and `max = 86.18%`.
* **Prevalence across candidate binary epidemic definitions ($N = 999$ plots):**

| Epidemic Definition | Events ($Y=1$) | Nonevents ($Y=0$) | Plot Prevalence (%) | Unique Weather Envs with $\ge 1$ Event (of 545) |
| :--- | ---: | ---: | ---: | ---: |
| `S >= 5%` (moderate + severe) | 395 | 604 | 39.54% | 246 (45.14%) |
| **`S >= 10%` (primary epidemic)** | **273** | **726** | **27.33%** | **171 (31.38%)** |
| `S > 10%` (strict inequality) | 271 | 728 | 27.13% | 170 (31.19%) |
| `S >= 15%` (severe outbreak) | 202 | 797 | 20.22% | 126 (23.12%) |
| `S >= 20%` (extreme outbreak) | 156 | 843 | 15.62% | 96 (17.61%) |

### 3.3 Within-Environment Discordance and Non-Weather (Agronomic) Drivers
* Among the **265 multi-plot weather environments** (`719` plots sharing identical weather vectors within each environment), **53 environments (20.0%) have discordant `S >= 10%` binary outcomes**—i.e., one plot in the environment experienced an epidemic while another plot under the *exact same weather* did not!
* This discordance is driven strongly by agronomic factors recorded at/before planting:
  * **Cultivar resistance (`resist`, ordinal 4 levels, 0% missing):** Epidemic (`S >= 10%`) prevalence drops monotonically from **`46.7%`** in `VS` (`63/135`, median `S = 8.84%`) to **`32.0%`** in `S` (`132/412`, median `3.38%`), **`22.1%`** in `MS` (`47/213`, median `2.67%`), and **`13.0%`** in `MR` (`31/239`, median `1.27%`).
  * **Corn residue (`corn`, binary, 4 missing values [0.40%]):** Epidemic prevalence is **`37.1%`** when corn residue is present (`129/348`, median `S = 5.69%`) versus **`22.1%`** when absent (`143/647`, median `S = 1.38%`).
  * **Wheat market type (`type`, 0% missing):** Winter wheat (`734` plots across 16 states) has `29.2%` epidemic prevalence (`214` events), whereas spring wheat (`265` plots restricted exclusively to `ND` [170], `SD` [62], and `MN` [33]) has `22.3%` prevalence (`59` events). Notice `type` is heavily confounded with geography (`MN` is 100% spring; `SD` 82.7% spring; `ND` 64.2% spring; all other 14 states are 100% winter wheat) and `corn` residue (`0%` corn residue in `KS, MN, MI` vs `70–100%` in `IL, MD, KY, DE`).
* **Theoretical performance ceiling for pure pre-anthesis weather models:** Even an "oracle" model knowing the exact conditional mean $\Pr(Y=1 \mid \mathbf{w}_i)$ for every unique pre-anthesis weather vector achieves `AUC = 0.9800` and minimum possible `Brier = 0.0495` on the 719 multi-plot observations (`0.9894` / `0.0357` across all 999 plots) because of irreducible within-environment host/agronomic variance.

### 3.4 Geographic and Temporal Representation (Severe Imbalance)
* **Geographic concentration:** Five states (`ND = 265`, `IL = 104`, `OH = 99`, `MD = 86`, `IN = 81`) contribute **63.6%** (`635/999`) of all observations and **71.4%** (`195/273`) of all `S >= 10%` events. Conversely, four states (`WI = 25`, `NY = 22`, `DE = 5`, `AR = 4`) have **zero** `S >= 10%` events, and three others (`MI = 1/25`, `MN = 2/33`, `KY = 3/14`) have $\le 3$ events.
* **Temporal skew and secular prevalence shift:** Only **7.7%** (`77/999`) of observations were collected during the first 19 years (`1982–2000`, with 1–10 plots/year across 1–4 states), whereas **92.3%** (`922/999`) come from `2001–2015` (peaking at `167` plots in `2009`). Furthermore, observed epidemic prevalence declined across eras (`37.5%` in `1982–1995`, `32.4%` in `2001–2005`, `28.3%` in `2006–2010`, `21.5%` in `2011–2015`), alongside expanded enrollment of `MR`/`MS` cultivars and drier years (`2012`: `4/85` events = `4.7%`; `2007`: `0/11` events = `0.0%`).

### 3.5 Missing Data and Weather Completeness
* **Missing tabular values:** Zero missing values (`0.0%`) in `id`, `year`, `state`, `fdate`, `type`, `resist`, `S`, and all **329** weather variables. Exactly **4 rows (0.40%)** have `NA` for `corn` (`id` 967–970: 2015 Minnesota spring wheat trials at Crookston and St. Paul). Because our primary models use weather predictors only, all **999** rows are complete for primary modeling!
* **Underlying hourly weather completeness:** Checking the exact temperature partition `T.L15 + T.15T30 + T.G30` across `PRE5`, `PRE10`, `PRE14`, and `PRE15` (`144`, `264`, `360`, `384` hours respectively) and `T.L9 + T.9T30 + T.G30` on `PRE7` (`192` hours) confirmed **zero missing hours across all 999 rows** (`min == max == 24 × n_days`).

### 3.6 Weather Predictor Taxonomy, Multicollinearity, and Extreme Observations
* **Pre-anthesis pool (`analysis_period == "pre"`, `window_end_day <= 0`):** **174 canonical variables** (`0` deprecated), spanning 7 physical families (`TRH = 48`, `T = 41`, `RH = 29`, `VPD = 26`, `TDD = 16`, `D = 7`, `P = 7`), 2 daily scopes (`114` full-day `24h` variables; `60` UTC-shifted `12h` variables), and 23 closed day windows ranging from `[-100, -60]` to `[-5, 0]`.
* **Severe multicollinearity:** Across the 545 unique weather environments (`15,051` pre-anthesis pairs), `1,278` pairs (`8.5%`) have $|r| \ge 0.80$, `390` (`2.6%`) have $|r| \ge 0.90$, and `119` (`0.8%`) have $|r| \ge 0.95$. Principal components analysis shows that **3 PCs explain 68.8%** of total standardized variance across all 174 pre-anthesis predictors (`5 PCs: 76.5%`, `10 PCs: 86.8%`; only 18 eigenvalues $> 1$). Strong collinearity arises from:
  1. Nested overlapping windows (`PRE5`, `PRE7`, `PRE10`, `PRE14`, `PRE15`, `[-20, 0]`, `[-30, 0]`), where adjacent windows correlate at $r = 0.92\text{–}0.98$;
  2. Psychrometric equivalence among moisture metrics over the same window (`RH.A.PRE10.24H` correlates at $r = -0.85$ with `VPD.A.1`, $r = -0.84$ with `TDD.A.1`, and $r = +0.83$ with `RH.G80.CHD.1`, whereas air temperature `T.A.PRE10.24H` and `RH.A.PRE10.24H` are nearly orthogonal at $r = -0.13$!).
* **Extreme / high-leverage weather observations:** Twenty pre-anthesis count/threshold variables exhibit $|z| > 5.0$ (up to $z = 8.36$ on `T.G30.CHD.1`), driven by zero-inflated right tails for extreme heat (`T > 30°C`, median `0–2` hours, max `89` hours in July 2002 Brookings, SD spring wheat) and cold snaps (`T < 9°C`, max `116` hours in `PRE10`). Multivariate 5-PC Mahalanobis distance flags two distinct legitimate meteorological extremes (not data errors): (i) hot, very dry May 2014 Kansas winter wheat (`RH ~ 44%`, `VPD ~ 1.55–1.63 kPa`, `S = 0%`) and (ii) unusually hot early-July 2002 Northern Plains spring wheat (`T.A.PRE10.24H = 24.4–26.4°C`, `T.G30.CHD.1 = 44–89` hours). Count predictors with extreme skew can create high leverage in logistic regression if entered untransformed or without checking influential observations.

### 3.7 Effective Sample Size and Suitability for Predictive Modeling
* **Intraclass correlation and design effects (`nAGQ = 20` binomial GLMMs on `S >= 10%`):**
  * Clustering by identical weather environment (`545` clusters): logit variance $\hat{\sigma}^2_{\text{env}} = 15.37$ ($\text{ICC} = 0.824$), Kish design effect $\text{DEFF} = 2.26 \Rightarrow N_{\text{eff,env}} \approx 442$, **$E_{\text{eff,env}} \approx 121$ effective events**.
  * Clustering by `state × year` (`142` clusters): logit variance $\hat{\sigma}^2_{\text{sy}} = 8.35$ ($\text{ICC} = 0.717$), Kish design effect $\text{DEFF} = 12.39 \Rightarrow N_{\text{eff,sy}} \approx 81$, **$E_{\text{eff,sy}} \approx 22$ effective state-year events** (across `32` years, $\hat{\sigma}^2_{\text{year}} = 0.87$, $\hat{\sigma}^2_{\text{state}} = 1.95$).
* **Audit conclusion on modeling feasibility:** The dataset **does support** fitting a parsimonious ($\le 3$ parameter) pre-anthesis logistic regression model, **provided** that:
  1. Model complexity is strictly capped at 2–3 biologically grounded parameters (respecting $E_{\text{eff,sy}} \approx 22$) without high-dimensional data dredging;
  2. `12H` UTC-distorted variables and ultra-long (`50–100 d`) pressure proxies are excluded from primary candidates;
  3. Collinear moisture metrics are never combined in the same model without orthogonalization/selection; and
  4. Validation strictly groups by `year`, `state`, and `state × year` (never random plot splitting), accounting for cluster-correlated uncertainty and unmodeled cultivar resistance heterogeneity.
