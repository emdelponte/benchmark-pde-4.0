# Analysis log — chronological record

Times are local (America/Sao_Paulo), 2026-11-22. This log records decisions, dead ends,
code failures and their fixes. Scripts are in `code/`; console logs in `outputs/`.

---

## 0. Scope, before touching data

Read the benchmark task. Planned the deliverables and the order: acquire → audit → plan →
fit → validate → sensitivity → critique → literature (strictly last). Decided that the
literature search would be delegated and run **after** the modelling so that published
choices could not contaminate the independent analysis.

## 1. Environment setup (most of the wall-clock time went here)

| Attempt | Result |
|---|---|
| `python --version` | not found (Windows Store alias only) |
| Bundled runtime found at `…\dsh-primary-runtime\dependencies\python\python.exe` | Python 3.12.14, numpy 2.3.5, pandas 3.0.1 present; **no pyarrow / yaml / sklearn / statsmodels / matplotlib** |
| `python -m pip install pyarrow …` (default) | hung >10 min, produced nothing on disk; killed |
| retry with `--no-cache-dir --target .pylibs` and workspace TMP | `OSError: [Errno 13] Permission denied … *.whl.metadata` → the sandbox denies pip's unpack step |
| `Invoke-WebRequest` to Zenodo | `The underlying connection was closed` (TLS problem in PowerShell 5.1) |
| `curl.exe` to Zenodo | `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS` |
| Python `urllib` to Zenodo and PyPI | **works** (HTTP 200) |

**Workaround adopted:** wheels are ZIP files, so `code/_bootstrap_libs.py` resolves each
package from the PyPI JSON API (preferring `cp312-cp312-win_amd64`, then `py3-none-any`),
downloads it to `data/wheels/` and extracts it into `.pylibs/`. A second script,
`code/_bootstrap_libs2.py`, loops on `ModuleNotFoundError` until the target imports succeed —
this is how the unlisted dependencies `cloudpickle` (joblib) and `narwhals` (scikit-learn
1.9.1) were found.
Matplotlib additionally needed `MPLCONFIGDIR` inside the workspace (its default cache path
under `AppData\Local` is not writable); this is set in `code/fhb_env.py`, which every script
imports first.

Outcome: a self-contained `.pylibs/` tree. Its presence is required to reproduce the
analysis; `README.md` explains how it is rebuilt. This is a **computational workaround, not
an analytical choice**, and it is the reason the environment section of the README is long.

## 2. Data acquisition

`code/_dl.py` (urllib) downloaded from the Zenodo API:
`FHBVer2.parquet` (1,025,846 B), `FHBVer2DataDict.yaml` (350,744 B), `README.txt` (6,022 B),
`VariablesMetaData.csv` (45,772 B), `FHBVer2Codebook.pdf` (1,666,701 B). Sizes matched the
API listing exactly; checksums were not re-verified.

## 3. First inspection (`01_inspect.py`, `02_yaml.py`, `03_yaml_flat.py`, `04_codebook.py`)

* Parquet: 999 rows × 337 columns, 1 row group, all columns untyped metadata (`None`), no
  parquet-level units or labels — the YAML/CSV are the only documentation.
* YAML top level: `glossary`, `conventions`, `tables[1].columns[337]`.
* `VariablesMetaData.csv`: 329 rows × 14 columns; 329 + 8 design columns = 337, consistent.
* Flattened the YAML to `outputs/yaml_columns_flat.csv` (337 × 23).
* Extracted the 242-page codebook text (`outputs/codebook_text.txt`, 113 k chars).

**Key finding that changed the whole analysis:** searching the codebook, the YAML and the
CSV for *epidemic / binary / threshold / outbreak / dichotomous / cut-off / classification*
returned **zero hits**, and `S` is the only column with `category: response`. The benchmark
premise of a documented binary outcome is not met by the release. Decision: define the
outcome myself, after the audit and before fitting, and treat the cut-point as a sensitivity
axis. Recorded in `data_audit.md` §3.

Minor false start: my regex search initially reported "no hits" only because the PowerShell
`Select-String` was reading a UTF-16 log; re-checking inside Python confirmed the absence
was real.

## 4. Audit (`05_audit.py`, `06_catalogue.py`, `07_candidates.py`, `08_audit2.py`)

* `05_audit.py` crashed with `KeyError: 'day'` — the YAML (unlike `VariablesMetaData.csv`)
  does not carry the 24h/12h field; switched that grouping to the CSV and recorded the gap
  as a metadata inconsistency.
* Discovered the sign-convention difference between the two metadata files
  (YAML signed −25…−15, CSV unsigned 25…15 with a `pre` flag). Not an error, but a trap;
  documented, and the YAML convention used throughout.
* Discovered the "7 d pre-anthesis to anthesis" window is **8 calendar days**: hours T ≥ 15
  plus hours T < 15 sum to exactly 192 h in every row. Documented.
* Grouping statistics initially wrong: I hashed all 337 columns to identify weather records,
  which included `year` and `corn` and produced 953 "distinct weather vectors". After
  excluding the 8 design columns the correct number is **545** — and it cross-checks exactly
  with the codebook's "# unique values = 545" for every weather variable. Both numbers are
  kept in the log because the first one was briefly believed.
* `07_candidates.py` crashed on `astype(float)` because the YAML column list includes
  `state`/`type`/`resist`; fixed with a dtype filter. The corrected run produced the
  univariate screen: maximum |Spearman ρ| with the outcome is 0.26 (mean RH over −20…0 d),
  and **mean temperature is essentially uninformative (ρ = −0.005)**.
* `08_audit2.py` added environment-level event counts (492 environments, 221 with a case),
  within/between variance (76% between environments; ICC ≈ 0.53), and consistency checks.

Audit conclusions committed to `data_audit.md`.

## 5. Analysis plan

Wrote `analysis_plan.md` with the outcome definition, the fixed eight-model set (M0–M7),
the two-parameter budget, LOYO/LOSO/K5 validation, the metric list, and the decision rule
"the primary model is M2 whatever its AUC rank". Written before any model was fitted.

## 6. Model fitting (`10_models.py`)

Small code failures, all fixed in place and visible in the git-less history of the file:

1. `AssertionError: missing columns … ['meanVPD']` — there is no 24-h mean VPD for the
   −7…0 d window in the release (it exists only for −10…0 d). The plan listed VPD as a
   candidate but no model uses it; removed from the required set and noted.
2. `'numpy.ndarray' object has no attribute 'iloc'` in `or_table` — statsmodels returned
   `conf_int()` as an ndarray for a design matrix built from arrays; converted with
   `np.asarray`.
3. `IndexError` then `ValueError: shapes (5,4) and (3,)` when building the risk grid — the
   grid frame accumulated output columns between `predict` calls. Replaced with an explicit
   logistic function of the two coefficients.

Results: wetness OR 1.13 per 10 h (p = 0.0002); heat term null (OR 0.90, p = 0.52); M4
(agronomic) reaches apparent AUC 0.69; the quadratic term is not significant.

## 7. Validation (`11_validate.py`)

Three schemes implemented with all estimation inside training folds; cluster bootstrap by
weather record for intervals; per-fold tables written to `outputs/cv_folds.csv`.

Outcome: LOYO AUC M1 0.569, M2 0.560, M5 0.598, M4 0.659; calibration slopes 0.52–0.84;
optimism 0.03–0.05. **M5 beat the pre-specified primary in all three schemes** → recorded as
a revision (plan §12 R4) and not adopted.

An unexpected artefact had to be explained: the prevalence-only model M0 has a LOYO "AUC" of
0.355, not 0.500. Diagnosis: leave-one-year-out makes the training prevalence anti-correlated
with the held-out year's prevalence. Kept in the table with an explanatory footnote rather
than deleted.

## 8. Sensitivity (`12_sensitivity.py`) — including one forced substitution

* First attempt at the window ladder failed for four of six windows because the 24-h
  `RH ≥ 90%` count does not exist for −5, −10, −14 or −15 d. **Substituted the warm–wet
  hours concept** for the ladder (available for all of −5…−15) and used the RH ≥ 90 h
  concept only for the −20 d point, flagging the change in the results table and in plan
  §12 R2.
* S6 (exclude 2009) collapsed LOYO AUC to 0.498. This was surprising enough that I added two
  analyses that were **not** in the plan: (a) within-year vs between-year discrimination
  (`14_figures.py` section A), and (b) year/state fixed-effects confounding models
  (`13_confounding.py`). Both are labelled exploratory in `results.md` and
  `critical_assessment.md`. The fixed-effects models showed the weather coefficient survives
  (attenuated ~25–30%), which reconciled "signal is real" with "pooled ranking is fragile".
* The continuous-outcome check (fractional logit) produced the only significant heat effect
  (OR 0.70 per 10 h, p = 0.015) — reported, and explicitly not used to rescue the binary heat
  term.

## 9. Decision thresholds and figures

`15_decision.py` (sensitivity/specificity/PPV/NPV at cut-offs) and `14_figures.py`
(five figures). No problems; matplotlib wrote to `outputs/figures/`.

## 10. Write-up

`results.md`, `critical_assessment.md`, this log, `README.md`. Deliberately ordered so that
the literature comparison is written last and kept in a separate file.

## 11. Literature comparison (after the independent analysis)

A dedicated sub-agent searched for the four `isReferencedBy` publications and the papers
cited in the dataset README, then for other FHB pre-anthesis risk models. Results and the
before/after distinction are in `comparison_with_literature.md`. Three things emerged:

1. The associated literature uses a binary outcome — **FHB index ≥ 10%** — which the release
   itself never states. Applying that rule gives 273/999 events, **exactly** the count
   reported in Shah et al. (2019b). This is a strong external check on my reading of `S`.
2. Published models report higher discrimination (AUC 0.79–0.90 at 10%) but use
   post-anthesis windows, 4–14 predictors and, in the older papers, random plot-level splits —
   which in this dataset leak shared weather records across folds.
3. The random-forest paper selects a **temperature-variability** variable pre-anthesis as its
   top predictor, which I had excluded a priori. Recorded as a candidate-set limitation in
   `critical_assessment.md`; not chased post hoc.

A new script, `code/16_threshold10_alignment.py`, was added **after** the search to compare
specifications at the published 10% threshold (`outputs/threshold10_alignment.csv`). It is
labelled post hoc everywhere it is cited; **no number in `results.md` was changed as a
result**, and the pre-registered 5% outcome remains the primary one.

## 12. Things that failed or remain unresolved

1. **No binary outcome in the release.** The benchmark premise could not be met as stated;
   the outcome is my construction. Unresolved by design.
2. **No day-0-free moisture aggregation** → the timing constraint can only be met
   approximately. Unresolved with this release.
3. **`pip` cannot install into this workspace** (sandbox denies wheel unpacking). Worked
   around, not fixed; reproduction depends on `.pylibs/` or on running outside the sandbox.
4. **Station provenance unverifiable** (no IDs, no coordinates); the effect of exposure
   error cannot be quantified. Unresolved.
5. **`corn` missingness** (4 rows) handled two ways with no material difference.
6. I did **not** fit a mixed-effects model with random trial/year effects. That would be
   the statistically natural next step for the dependence structure but was outside the
   pre-specified plan and the parameter budget; it is flagged as follow-up work in
   `critical_assessment.md` §4.
