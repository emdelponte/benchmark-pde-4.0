# Data audit — FHB prediction benchmark

Written 2026-10-10, before any model fitting and before looking at any outcome–weather association.
Scripts: `code/01_audit.py` (generic schema/YAML cross-check) and `code/02_audit_detailed.py` (everything else).
Machine-readable outputs: `outputs/audit/` (`audit_report.json`, `audit_detailed.json`, `by_year.csv`, `by_state.csv`, `environments.csv`, `weather_windows.csv`, `pre_anthesis_spearman_env_level.csv`).

> History: an earlier version of this file recorded that the data could not be downloaded (zenodo.org was blocked by the session's network policy). The files were then uploaded by the user to the project thread. That blocked status is preserved in `analysis_log.md`.

## 1. Files and provenance

| File | Size | MD5 (prefix) | Used for |
|---|---|---|---|
| FHBVer2.parquet | 1,025,846 B | ba455c96 | **primary data** |
| FHBVer2DataDict.yaml | 350,744 B | 6365e99e | **primary dictionary** |
| README.txt | 6,022 B | e964800d | design notes (version 2.1.0) |
| FHBVer2.csv / .rds | — | — | csv used only for a consistency check |
| VariablesMetaData.csv / .rds | — | — | cross-check of windows |
| FHBVer2Codebook.html / .pdf.txt | — | — | cross-check of descriptions |

The files were not downloaded from Zenodo by me (network denial, see log); they were supplied by the user as the content of record 23189372. I could not verify them against Zenodo checksums. README identifies them as "FUSARIUM HEAD BLIGHT DATA MATRIX, VERSION 2.1.0" (contacts: Shah, De Wolf, Paul, Madden; funding USWBSI).

Read with pyarrow 26.0.0 / pandas 3.0.5 and PyYAML 6.0.1.

## 2. Structure

* **Observational unit:** one row = one fungicide-untreated wheat plot (a cultivar in a trial) assessed for FHB in a given year (README: "Fusarium head blight severity was evaluated in fungicide-untreated plots"). `id` is a unique row id (1–999).
* **Sample size:** 999 rows × 337 columns; 0 duplicate rows. The csv copy is identical to the parquet (max |diff| 2e-13; csv has one extra unnamed index column).
* **Columns by YAML category:** 1 metadata (`id`), 1 calendar (`year`), 1 spatial (`state`), 1 temporal (`fdate`), 3 agronomic (`type`, `resist`, `corn`), 1 response (`S`), 329 weather-derived.
* **Weather variables by period (YAML `analysis_period`):** pre-anthesis 174, post-anthesis 137, spanning anthesis ("pre-post") 18.
* Every parquet column has a YAML entry and vice versa. All 329 weather variables in YAML also appear in VariablesMetaData.csv with matching windows and periods.

### Non-weather variables

| Variable | YAML definition | Observed |
|---|---|---|
| year | year plot assessed | 1982–2015, 32 distinct (1983 and 1985 absent) |
| state | US state | 17 states, conterminous US |
| fdate | anthesis date-time in UTC | all at 00:00 UTC; 426 distinct dates; year(fdate) = year in all rows |
| type | spring / winter wheat | 265 spring (MN, ND, SD only), 734 winter |
| resist | cultivar resistance VS / S / MS / MR | 135 / 412 / 213 / 239 |
| corn | corn residue present (1) / absent (0) | 348 / 647, 4 missing |
| S | "FHB index, or severity of FHB symptoms on the spike", percent | 0–86.18 |

## 3. Response variable

**There is no binary epidemic variable in the dataset.** The only response is the continuous `S` (FHB index, %). Neither the YAML, the README nor the codebooks define an "epidemic" or give a threshold. The task requires "the documented binary epidemic outcome"; since none is documented, the binary outcome must be derived and that choice has to be justified (done in `analysis_plan.md`, with sensitivity to the threshold).

Distribution of S: median 2.87%, mean 8.81%, 186 rows (18.6%) exactly 0, 90th percentile 25.9%, max 86.2%. Strongly right-skewed.

| Threshold (S ≥ t) | Events | Non-events | Prevalence |
|---|---|---|---|
| 5% | 395 | 604 | 0.395 |
| **10%** | **273** | **726** | **0.273** |
| 15% | 202 | 797 | 0.202 |
| 20% | 156 | 843 | 0.156 |

Ambiguity: the description says "FHB index, *or* severity of FHB symptoms on the spike". FHB index (incidence × spike severity) and spike severity are different quantities. Whether all collaborators reported the same measure is not documented. I treat S as the FHB index but flag this as a possible source of heterogeneity across trials.

## 4. Geographic and temporal coverage

* Strongly unbalanced in time: 1982–1999 contribute only 46 rows; 2009–2015 contribute 625 rows (2009 alone: 167). See `outputs/audit/by_year.csv`.
* Unbalanced in space: ND 265, IL 104, OH 99, MD 86, IN 81, SD 75 … AR 4, DE 5. OH has 26 years of data; most states have ≤ 7 years.
* 9 of 32 years have no event (S ≥ 10%) at all (mostly early years with 1–2 rows, plus 2007); no year has only events. 13 of 17 states have both classes (AR, DE, NY, WI have no events).
* There is **no location/site/station identifier and no coordinates**: `state` is the finest spatial unit. Leave-one-location-out validation is therefore impossible as such.

## 5. Dependence and clustering (the most important finding)

Weather values are attached per weather station × anthesis date, so several plots share an identical weather vector. Hashing the 329 weather columns gives **545 distinct weather "environments"** (sizes: 280 singletons, 149 pairs, 69 triples, 36 quads, 9 of 6 and 2 of 8). No environment spans more than one state, year or anthesis date, so environments are nested in state × year (142 state-years, median 3 environments each, max 30).

* Within multi-row environments, rows differ in cultivar resistance (211 of 265) and/or corn residue (96 of 265); type never varies.
* **82% of the variance in the 10% epidemic indicator lies between environments** (50% between state-years). Within an environment, weather cannot discriminate anything; only resistance/residue can.
* At environment level: 171 environments contain at least one event, 154 have a majority of events, 53 have mixed outcomes.

Consequences:
1. The effective sample size for learning weather effects is ≈545 environments (≈155–170 "event environments"), not 999 rows. Row-level standard errors from ordinary logistic regression will be too small.
2. Any random row-level train/test split would put plots from the same environment on both sides and inflate performance. Validation must group at least by environment, and preferably by year (all environments in a year share regional weather patterns and inoculum conditions).

## 6. Weather variables and timing relative to anthesis

* Anthesis reference = 00 UTC on the flowering date (README). Day windows are closed intervals [start, end] in days relative to anthesis (YAML `window_day_bounds`); "24H" days are 00–23 UTC; "12H"/"overnight" periods are 20:00–08:00 UTC.
* Weather was taken from the nearest standard (or citizen) weather station via Mathematica's `WeatherData`, not on-site; no distance-to-station is given. Exposure measurement error is therefore unknown and possibly large.
* **Timing caveat 1 (day 0).** 151 of the 174 pre-anthesis variables have windows ending at day 0 (e.g. "7 d pre-anthesis to anthesis" = days −7…0, 8 days; YAML valid max for T15307 = 192 h = 8 × 24). Day 0 runs 00–23 UTC on the flowering date, i.e. up to 24 h *after* the anthesis reference point. Overnight windows ending at day 0 may extend to 08 UTC of day +1 (≈32 h after the reference; which night is attached to "day 0" is not documented). These are labelled "pre" in the dictionary. Only 23 pre-anthesis variables end before day 0 (all at day −5 or earlier).
* **Timing caveat 2 (UTC "overnight").** README states times were *not* adjusted to local time. 20:00–08:00 UTC is ≈15:00–03:00 CDT / 14:00–02:00 CST in the central US, so the "overnight" variables actually cover late afternoon to early morning local time, not the night. The YAML says the period is "NOT sunset-to-sunrise", consistent with this, but the label "overnight" is misleading for biological interpretation.
* Minor wording difference: README defines the 12 h period as "20 UTC to 07 UTC" (hour stamps), YAML as "20:00 to 08:00" (duration). Both give 12 hourly readings and are consistent with the valid-range maxima; I treat them as the same definition.
* Units (YAML): T, D, TDD in °C; RH in %; VPD in kPa; P in hPa; counts in hours or days. All count variables respect their YAML `valid_range` (0 violations).
* Redundancy by design: e.g. PRE14 and PRE15 windows differ by one day; 5 legacy variables are exact duplicates of standardised ones (verified identical in all rows: RH10 = RH.A.2, RH8010, RH9010, TRH8010, TRH9010); INT3 = T15307 × TRH9010 (verified) is a pre–post product.

## 7. Information leakage risks

* 137 post-anthesis and 18 pre-post variables (including INT3 and RH.A.3, "10 d pre- to 10 d post-anthesis") must be excluded: they use weather after the prediction time.
* The pre-anthesis variables ending at day 0 use up to 1 day (24H) or ~1.3 days (12H) after 00 UTC on the flowering date (see §6). This is a borderline case, handled explicitly in the analysis plan.
* Many variables in the dictionary were introduced in earlier publications by the data authors (VariablesMetaData `origin`), partly *because* they were informative in this or earlier versions of this dataset (README: variables "found to be uninformative for prediction were removed"). The candidate set is therefore already pre-selected on (versions of) these data. Performance of any model chosen from it will carry an optimistic bias that internal validation cannot remove.
* `S` is the only response, so no outcome-derived predictors exist.

## 8. Missing data and data quality

* Only `corn` has missing values: 4 rows (ids 967–970, MN 2015). All weather columns complete.
* YAML vs parquet: `resist` is described as "ordinal" but stored as an unordered factor (levels in the documented order VS, S, MS, MR); `corn` is documented as integer but is float in parquet (because of the NAs). All ranges and missing percentages in YAML match the data.
* Extreme values: several count variables are zero-inflated and skewed, e.g. hours with T > 30 °C (T.G30.CHD.2 is 0 in 91.5% of rows; T.G30.PRE5.24H 0 in 70%); 22 pre-anthesis variables have some values with |z| > 5, almost all in hot/cold-hour counts and short-window overnight dewpoint-depression means. These are plausible weather values, not errors, but they are potential high-leverage points for linear logit terms.

## 9. Correlations among pre-anthesis predictors

Computed at environment level (one row per environment, n = 545), Spearman, on the 174 non-deprecated pre-anthesis variables (30,276 pairs): 4.2% of pairs have |ρ| > 0.8 and 0.4% |ρ| > 0.95 (mostly the same quantity over nested windows, or 12H vs 24H versions). The first principal component explains 44% and the first 3 components 69% of the variance; 14 components are needed for 90%. So the candidate space is large but dominated by a few correlated dimensions (temperature level, moisture/humidity, variability). Selecting "the best" of many near-equivalent variables would be unstable.

Outcome–predictor associations were deliberately **not** examined during the audit, so that the candidate predictors in the plan are chosen from mechanism rather than from the data.

## 10. What the data support — constraints for the analysis

1. **Events per parameter.** At row level there are 273 events; at the environment level about 155–170. A logistic model with ≤ 3 weather terms (≤ 3–6 parameters including any non-linear terms) gives roughly 25–50 environment-level events per parameter, which is ample *for a pre-specified model*. The real threat is not the final model's size but selection among ~170 candidates × windows: selection must be minimal, pre-specified, and repeated inside validation folds.
2. **Grouped validation is mandatory.** Leave-one-year-out keeps every environment and state-year in one fold and mimics forecasting a new season; leave-one-state-out tests spatial transportability. Pooled out-of-fold predictions are needed because 9 years have no events and many years have < 10 rows; per-year AUC is only estimable for 23 years.
3. **Account for clustering** in coefficient uncertainty (cluster-robust SEs or cluster bootstrap).
4. **Host resistance** explains much of the within-environment variation and is known at anthesis; it is a legitimate non-weather predictor and should be considered alongside the weather terms (reported separately from the weather-term budget).
5. **Strict timing**: decide explicitly whether day-0 windows count as "available at anthesis", and check results with windows ending ≤ day −5.
6. The sample is not a random sample of US wheat fields: it comes from cooperative trials, is concentrated in 2003–2015 and in a few states, and the dictionary's variables were chosen in earlier studies. Transportability to other regions/years is uncertain.
