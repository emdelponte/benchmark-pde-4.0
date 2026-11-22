# Data audit — FHBVer2 (Zenodo record 23189372, v2.1.0)

*Audit performed before any model fitting. All numbers below are reproducible from
`code/01_inspect.py` … `code/08_audit2.py`; raw console output is in `outputs/`.*

---

## 1. Provenance and files

| Item | Value |
|---|---|
| Record | Zenodo 23189372 (concept 10.5281/zenodo.16952506), version 2.1.0, published 2026-10-06 |
| Title | *Field-plot dataset of Fusarium head blight (FHB) severity in wheat: fungicide-untreated small plots across the United States* |
| Creators | Shah, De Wolf, Paul, Madden (USWBSI IM-CP) |
| Licence | CC-BY-4.0 |
| Files used | `FHBVer2.parquet` (1.03 MB), `FHBVer2DataDict.yaml` (351 kB), `VariablesMetaData.csv`, `FHBVer2Codebook.pdf` (242 pp.), `README.txt` |
| Also present (not used) | `FHBVer2.csv`, `FHBVer2.rds`, `VariablesMetaData.rds`, `FHBVer2Codebook.html` |

Checksums were not verified against the Zenodo API, but sizes matched the API listing exactly.
The parquet file was read with `pyarrow`; the YAML dictionary with `PyYAML`; the PDF text
with `pypdf`. The CSV/RDS duplicates were not analysed (the parquet is the release's
preferred format and preserves factor types).

**Version note.** README documents three versions: v1 (527 rows, local-time weather),
v2.0 (999 rows, all weather re-sourced through Wolfram *WeatherData* for the nearest
standard/citizen weather station, dates in UTC, new variable nomenclature), v2.1
(parquet + YAML added; values unchanged from v2.0). Therefore all modelling below uses
the v2.0/v2.1 weather block.

---

## 2. Observational unit, size, coverage

* **Unit of observation:** one fungicide-untreated small field plot in one trial
  (cultivar × location × year × anthesis date). Not a farm field, not a county, not a
  year. 999 rows × 337 columns, `id` unique 1…999, **no exact duplicate rows**.
* **Geographic coverage:** 17 conterminous US states (AR, DE, IL, IN, KS, KY, MD, MI, MN,
  MO, ND, NE, NY, OH, PA, SD, WI). ND dominates (265 plots), then IL (104), OH (99),
  MD (86), IN (81), SD (75); AR (4) and DE (5) are marginal.
* **Temporal coverage:** 1982–2015 (32 years), anthesis dates 26 May – 14 July (12 plots
  in April). Effort is very uneven: 1982–1993 contribute 1–4 plots per year, whereas
  2009 contributes 167, 2014 88, 2011 85, 2012 85.
* **Grouping variables:** `year` (32), `state` (17), `fdate` (anthesis date, 426 distinct
  dates), `type` (spring 265 / winter 734), `resist` (VS 135, S 412, MS 213, MR 239),
  `corn` (residue present 348, absent 647, missing 4).

### Dependence structure (critical)
* `state × year` cells: 142; 23 cells hold a single plot.
* `state × year × anthesis date` ("env"): 492 groups, median 2 plots, max 10; 232 singletons.
* **Distinct weather vectors: 545** for 999 plots. 719 plots share their entire 329-column
  weather block with at least one other plot (max 8 plots per identical vector). This is a
  direct consequence of using the *station* rather than the plot as the weather source:
  all plots of a trial share one weather record. Weather vectors are strictly nested within
  state-year-anthesis-date groups, but **47 of the 492 groups contain more than one vector**
  — i.e. trials in the same state-year with the same anthesis date were matched to different
  stations, so location is not recoverable from the date alone.
* Consequence: the **effective sample size for weather–disease inference is ~545, not 999**
  (and ~492 at the trial level). Any interval estimate that treats plots as independent
  is too narrow.
* Outcome clustering is strong: 76% of the variance of the FHB index is between
  environment means; a crude one-way ICC is ≈ 0.53; plot-level `S` correlates 0.87 with its
  own environment mean.

---

## 3. Response variable(s)

Only **one** response is documented: `S`.

> *"FHB index, or severity of FHB symptoms on the spike", unit = percent, valid range 0–100.*

`S` is therefore a **continuous plot-level disease severity index** (FHB index =
incidence × severity on a 0–100% scale), not a binary variable.

Observed: n = 999, 0 missing, min 0, max 86.18, mean 8.81, SD 13.70, median 2.87;
skewed right; **18.6% exact zeros**; percentiles: p25 = 0.20, p75 = 11.31, p90 = 25.87,
p95 = 39.52, p99 = 65.14. No values outside [0, 100].

### ⚠ The "documented binary epidemic outcome" does not exist in this release
The benchmark brief refers to a *documented binary epidemic outcome*. I searched the
README, the 242-page codebook, the YAML dictionary (all 337 column entries, including
every `description`, `value_labels`, `condition` and `derivation` field) and
`VariablesMetaData.csv`:

* `S` is the only column with `category: response`;
* the strings *epidemic*, *binary*, *threshold*, *outbreak*, *dichotomous*, *cut-off* and
  *classification* do **not occur anywhere** in the codebook or the YAML dictionary;
* no two-level outcome column and no documented cut-point exist.

This is a genuine documentation gap, not an extraction failure (the codebook text
extracted cleanly — 113 k characters, 242 pages). **I therefore define the binary
outcome myself after the audit and before any modelling, and treat threshold choice as a
sensitivity axis** (see `analysis_plan.md`, §2). Excerpts of prevalence at candidate
thresholds (from `outputs/threshold_prevalence.csv`):

| cut-point (S > x%) | events | non-events | prevalence |
|---|---|---|---|
| 0 | 813 | 186 | 0.814 |
| 1 | 633 | 366 | 0.634 |
| 2 | 551 | 448 | 0.552 |
| **5** | **393** | **606** | **0.393** |
| 10 | 271 | 728 | 0.271 |
| 15 | 201 | 798 | 0.201 |
| 20 | 156 | 843 | 0.156 |
| 25 | 104 | 895 | 0.104 |

---

## 4. Weather variables: structure of the dictionary

329 of the 337 columns are weather-derived (`category: weather_derived`). The remaining 8
are design variables (id, year, state, fdate, type, resist, corn, S).

Nomenclature (README + YAML glossary): `T` air temperature (°C), `D` dewpoint (°C),
`P` barometric pressure (hPa), `RH` relative humidity (%), `VPD` vapour pressure deficit
(kPa), `TDD`/`DD` temperature–dewpoint depression (°C), `TRH` combined T-and-RH condition;
`A` mean, `SD` standard deviation, `MINMAXDIFF` mean daily range, `G`/`L` greater/less than
a threshold, `CHD` count of hours over a 24-h day, `CD` count of days, `PRE`/`POST` relative
to anthesis.

**Temporal reference.** Anthesis = 00:00 UTC of `fdate`. Windows are *closed* day intervals:
`n_days = window_end_day − window_start_day + 1`. Verified against the data: the
"7 d pre-anthesis to anthesis" window is 8 calendar days — hours with T ≥ 15 °C plus hours
with T < 15 °C sum to exactly **192 h** in every row (= 8 × 24), not 168 h.
**This is a factor of ~1.14 that matters whenever counts are compared across window
lengths, and the label "7 d" is misleading.**

Windows offered, by end day: 151 variables end at day 0 (anthesis), and 23 end before
anthesis (−5 to −70). 174 variables are labelled `pre` (period = pre), 137 `post`, 18
`pre-post`. Time step: 118 are daily summaries and 211 hourly counts; by daily scope,
209 variables use the full 24-h day and 120 use the fixed "overnight" 12-h period.

### ⚠ Metadata inconsistencies and ambiguities found

1. **Overnight definition conflict.** README: *"a 12 h daily period was defined as from
   20 UTC to 07 UTC"* (11 h). YAML `overnight_fixed_hours`: *"20:00 to 08:00 the next day
   (12 h per night)"*. The YAML's 12 h is the one consistent with the observed bounds
   (`valid_range.max = 12 × n_days`), so the README sentence appears to be wrong.
2. **UTC vs local time.** README v2.0 states that *"weather data and flowering date were
   all in UTC, not adjusted to local time zone"*, while the YAML calls `fdate`
   *"Anthesis date as a date-time variable in UTC"* with all timestamps at 00:00:00. For
   17 US states in the Central/Eastern time zones (UTC−6…−4), a "day" of 00–23 UTC is
   roughly **18:00–17:00 local**, and the "overnight" 20–08 UTC period is roughly
   **14:00–02:00 local** — i.e. mostly *afternoon and evening*, not night. All `12H`
   ("overnight") variables are therefore **misaligned with the biological night** by
   ~6 h, and `fdate` is best read as a local calendar date labelled as UTC. Anyone
   interpreting "overnight leaf wetness" from these columns will mis-interpret them.
   → Consequence for modelling: **prefer 24-h variables**, and do not build a hypothesis
   on the overnight/12-h block.
3. **Sign convention differs between the two metadata files.** `VariablesMetaData.csv`
   stores unsigned integers (`win_start_day = 25`, `win_end_day = 15`,
   `win_start_period = pre`), the YAML stores signed offsets (−25, −15). 24 variables
   differ numerically between the files purely for this reason. Not an error, but a trap;
   the YAML (signed) convention is used throughout this analysis.
4. **Fields present in one file but not the other.** `VariablesMetaData.csv` carries
   `origin` (source paper), `variable_type`, `period`, `win_*`; the YAML carries
   `condition`, `unit`, `valid_range`, `value_labels`, `identical_to`, `derivation`, plus
   pre-computed `same_condition_as` / `same_window_as` lists. The YAML omits `day`
   (24h/12h) and `origin`. Neither file alone is sufficient; they must be joined.
5. **The YAML has no binaries/thresholds** for any outcome, and no `S` cut-point
   (see §3).
6. **Naming is not systematic.** Legacy names inherited from De Wolf et al. (2003)
   (`MT7`, `T157`, `T15307`, `RH7`, `RH907`, `TRH807`, `TRH907`, `INT3`) sit alongside the
   new `FAMILY.METRIC.PREn.scope` names, and some windows exist only under the legacy name
   (e.g. the 24-h mean RH for −7…0 d is `RH7`; `RH.A.PRE7.24H` does not exist). Deprecated
   aliases (`identical_to`, `canonical`, `deprecated`) must be honoured to avoid counting
   the same variable twice.
7. **Units** are given in the YAML `unit` field but are *not* carried in the parquet
   schema (all numeric). Units are consistent with observed ranges (T °C, RH %, P hPa
   ≈ 1007–1023, VPD kPa 0.26–1.63, TDD °C 2.8–13.3). Reasonable.
8. **No station identifier, latitude/longitude, or distance to station** is released.
   The "nearest station" provenance cannot be audited, and there is no way to check
   whether two plots sharing a weather vector were geographically close.

---

## 5. Missingness and data-quality checks

* **No missing weather values**: every one of the 329 weather columns has 0 NA.
  This is suspicious in a good way — it is a curated product: station records were
  selected to have complete coverage of the required windows. It also means the release
  gives no information about *failed* station matches, so weather quality cannot be
  audited, and any imputation/fill is invisible to the user.
* **`corn` has 4 missing values (0.4%)** — the only missingness in the file. These rows
  are otherwise complete; they will be handled by complete-case use in the one model that
  uses `corn`.
* **No column violates its documented `valid_range`** (all 329 checked programmatically).
* **No constant columns**; one near-empty column (`T.G30.CHD.2`: 91.5% zeros,
  max 19 h) — not used.
* **Internal consistency is good**: complementary counts sum to the theoretical maximum
  (hours T ≥ 15 + hours T < 15 = 192 h for the −7…0 window); RH ≥ 90 counts never exceed
  the 192 h implied by an 8-day window (observed max 142 h); mean RH and RH ≥ 90 hours
  correlate 0.85 (Spearman).
* **Implausible values:** none detected. Zeros are genuine zeros in dry, disease-free
  years (e.g. 1982–1989, 2007: all-zero FHB index), not missing codes.
* **Possible information leakage:** none identified. No column is derived from `S`, no
  post-hoc summary of the current epidemic exists, and the outcome is defined from a
  separate visual assessment. Post-anthesis weather columns *are* present and are
  tempting but are excluded by the timing constraint (see §7).

---

## 6. Redundancy, collinearity and the candidate space

* The 174 pre-anthesis variables collapse into ~49 "condition families" (e.g. *mean daily
  T*, *hours RH ≥ 90*, *hours 15–30 °C & RH ≥ 80*), each repeated over 5–8 overlapping
  windows (5, 7, 10, 14, 15, 20, 30, 40 d).
* **Windows overlap heavily by construction** (nested), so "5 d" and "7 d" versions of the
  same family correlate r ≈ 0.9–0.95 (e.g. combined warm–wet hours: r = 0.94 between −5…0
  and −7…0; 0.92 between −7…0 and −10…0). Window choice is therefore *not identifiable*
  as a biological quantity in this design; it is a partly arbitrary smoothing choice.
* **Families are strongly collinear within a window** (environment-level Spearman):
  mean RH vs RH ≥ 90 h = 0.85; mean RH vs mean VPD (−7…0 overnight) = −0.80;
  hours 15–30 °C & RH ≥ 80 vs mean RH = 0.71; hours RH ≥ 90 vs hours 15–30 °C & RH ≥ 80
  = 0.56. A 3-term model therefore cannot contain two moisture metrics without
  near-singularity.
* **Mean temperature carries almost no marginal information** in the pre-anthesis window
  (Spearman with `S ≥ 5%` = −0.005 for −7…0 d; 0.05 for −15…0 d). Moisture variables are
  the informative axis (max |ρ| ≈ 0.26 for mean RH over −20…0 d and TDD).
* Descriptive univariate AUCs (plot level, *not* used for selection):
  mean RH −20…0 d 0.654; mean RH −7…0 d 0.650; warm–wet hours −7…0 d 0.627;
  RH ≥ 90 h −7…0 d 0.606; corn residue 0.600; mean T −7…0 d 0.497;
  hours T > 30 °C 0.443; mean VPD 0.387; resistance class 0.375 (ordinal);
  mean TDD 0.346 (lower TDD = wetter = riskier).
  **Even the best single pre-anthesis weather variable discriminates only modestly.**
* Agronomic covariates are strong and are known at anthesis: mean FHB index is 17.7 (VS),
  9.7 (S), 6.7 (MS), 4.1 (MR); 12.9 with corn residue vs 6.6 without. Within environments
  that contain more than one resistance class the gradient is preserved (VS 17.1 → MR 4.5),
  so it is not an artefact of location confounding.

---

## 7. Constraints implied by the audit

1. **Timing.** Only variables with `window_end_day ≤ 0` (174 of 329) are available at
   anthesis. Post-anthesis and `pre-post` variables (155) are excluded, even though they
   are the stronger classical FHB predictors (post-anthesis wetness drives infection) —
   using them would break the stated prediction problem.
   *Residual timing caveat:* a window ending at day 0 includes the weather of the anthesis
   day itself (00–23 UTC). No day-0-free moisture aggregation is released, so a strictly
   "before anthesis day" model cannot be fitted; the primary model is therefore an
   *end-of-anthesis-day* risk assessment. This is realistic for a decision taken at/just
   after anthesis, but it must be stated.
2. **Effective sample size.** ~545 independent weather records, ~492 trials,
   221 environments with ≥1 case. Event counts at plot level (393 at 5%) overstate
   information because events cluster in environments.
3. **Parameter budget.** With 393 events / 606 non-events but ≈221 case-environments and
   ≈545 independent weather vectors, and with single-predictor AUCs of only 0.60–0.65, the
   defensible complexity is **very small**: 1–3 weather terms, no data-driven search over
   the 174 candidates.
4. **Validation must respect grouping** (year, state, and trial). Random plot-level splits
   would leak shared weather and shared epidemic conditions across folds and give
   optimistic estimates.
5. **Threshold definition of "epidemic" is my choice**, and must be sensitivity-tested.
6. **Transportability is limited**: states enter and leave the record at different times
   (OH 1982–2014, ND 1993–2015, IL 2009–2015 only), so state and year effects are
   partially confounded; there is no location coordinate.

---

## 8. Verdict: are the data adequate?

**Yes for a deliberately small, pre-specified logistic model; no for data-driven
discovery or for a high-accuracy operational risk tool.**

* Adequate: 999 plots, 393 events at a 5% cut-point, complete pre-anthesis weather,
  a strong and interpretable agronomic gradient, and a clear temporal ordering.
* Inadequate for: (i) identifying which of ~49 weather families and 8 windows truly
  matters (severe collinearity + window overlap); (ii) claiming tight effect estimates
  without clustering-aware uncertainty; (iii) external validation beyond the 17 states /
  32 years sampled, which are a convenience sample of USWBSI trials, not a probability
  sample of US wheat fields; (iv) separating weather effects from cultivar, site and year
  effects when trials differ in all three simultaneously.

These constraints drive `analysis_plan.md`.

---

## 9. Addendum after the literature search (appended, not substituted)

The statement in §3 that no binary outcome is documented is correct **for this release** —
but the associated publications do define one, as FHB index **≥ 10%** (Shah et al. 2013,
2019a). Applying that rule to `S` gives exactly **273 events / 726 non-events**, matching the
999/273/726 counts reported in Shah et al. (2019b) — an independent confirmation that the
field's canonical outcome is reconstructible from `S` even though it is absent from the
codebook, the YAML and `VariablesMetaData.csv`. The audit finding stands as a metadata gap;
the practical consequence is that the outcome is documented *outside* the record. See
`comparison_with_literature.md` §2. The pre-registered analysis used `S ≥ 5%` and was not
changed.
