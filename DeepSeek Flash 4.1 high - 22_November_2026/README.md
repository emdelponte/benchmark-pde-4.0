# Reproducing the FHB epidemic-risk analysis

Independent analysis of the Zenodo dataset
[10.5281/zenodo.23189372](https://zenodo.org/records/23189372) — *Field-plot dataset of
Fusarium head blight (FHB) severity in wheat: fungicide-untreated small plots across the
United States* (v2.1.0, Shah, De Wolf, Paul & Madden, CC-BY-4.0).

**Read in this order:** `data_audit.md` → `analysis_plan.md` → `results.md` →
`critical_assessment.md` → `comparison_with_literature.md`, with `analysis_log.md` as the
chronological record of decisions and failures.

---

## 1. What is here

```
├── data_audit.md                  dataset description, metadata audit, quality assessment
├── analysis_plan.md               pre-specified analysis plan (+ append-only revisions)
├── results.md                     estimates, diagnostics, validation, sensitivity
├── critical_assessment.md         limitations, robustness, what would change the answer
├── comparison_with_literature.md  comparison with published work (done after the analysis)
├── analysis_log.md                chronological record incl. failed attempts
├── README.md                      this file
├── data/                          downloaded release files (not tracked if re-cloned)
├── code/                          all analysis scripts (below)
├── outputs/                       machine-readable results, console logs, figures/
└── .pylibs/                       locally installed Python packages (see §2)
```

### Scripts (run in this order)

| Script | Purpose | Main outputs |
|---|---|---|
| `code/_dl.py` | download the five release files from the Zenodo API via `urllib` | `data/*` |
| `code/_bootstrap_libs.py`, `code/_bootstrap_libs2.py` | install Python packages by extracting wheels into `.pylibs` (sandbox workaround) | `.pylibs/` |
| `code/fhb_env.py` | shared bootstrap: `sys.path`, `MPLCONFIGDIR`, paths | — |
| `code/01_inspect.py` | parquet schema, YAML top level, metadata CSV | `outputs/01_inspect.log`, `fhb_raw.pkl` |
| `code/02_yaml.py` | unpack YAML column entries | `outputs/02_yaml.log` |
| `code/03_yaml_flat.py` | flatten dictionary; search for epidemic/binary language | `outputs/yaml_columns_flat.csv` |
| `code/04_codebook.py` | extract 242-page codebook text; search it | `outputs/codebook_text.txt` |
| `code/05_audit.py` | structural audit, outcome distribution, clustering, metadata gaps | `outputs/audit_stats.txt`, `threshold_prevalence.csv`, `fhb_raw2.pkl` |
| `code/06_catalogue.py` | catalogue of the 174 pre-anthesis variables by family × window | `outputs/pre_catalogue.csv` |
| `code/07_candidates.py` | availability, redundancy, univariate associations | `outputs/candidate_screen.csv` |
| `code/08_audit2.py` | environment/weather-record structure, event counts, consistency checks | `outputs/audit_stats2.txt` |
| `code/fhb_model.py`, `code/fhb_specs.py` | shared utilities and the fixed model registry | — |
| `code/10_models.py` | fit M0–M7, cluster-robust ORs, VIF, apparent performance | `outputs/model_estimates.csv`, `model_correlations.csv`, `apparent_performance.csv`, `10_models.txt` |
| `code/11_validate.py` | LOYO / LOSO / K5 cross-validation, pooled OOF metrics, bootstrap CIs | `outputs/cv_summary.csv`, `cv_folds.csv`, `optimism_gap.csv`, `11_validate.txt` |
| `code/12_sensitivity.py` | S1–S11 sensitivity analyses | `outputs/sensitivity.csv`, `12_sensitivity.txt` |
| `code/13_confounding.py` | variance decomposition, year/state fixed-effect checks, 2009 influence | `outputs/13_confounding.txt` |
| `code/14_figures.py` | within- vs between-year discrimination and all figures | `outputs/within_between_auc.csv`, `outputs/figures/*.png` |
| `code/15_decision.py` | sensitivity/specificity/PPV/NPV at decision cut-offs | `outputs/decision_thresholds.csv` |
| `code/16_threshold10_alignment.py` | **post hoc** (added after the literature search): re-runs the specifications at the published FHB index ≥ 10% epidemic definition and with De Wolf (2003) terms | `outputs/threshold10_alignment.csv`, `16_threshold10.txt` |

`outputs/*.pkl` are intermediate caches; they can be regenerated from the parquet file.

---

## 2. Software environment

The analysis was run with the DeepSeek Harness bundled Python, because no system Python was
available and `pip install` could not unpack wheels inside the sandboxed workspace
(`OSError: Permission denied … *.whl.metadata`). Packages were instead extracted from
wheels into `.pylibs/` (see `analysis_log.md` §1).

| Component | Version |
|---|---|
| Python | 3.12.14 |
| numpy | 2.3.5 |
| pandas | 3.0.1 |
| scipy | 1.18.1 |
| pyarrow | 26.0.1 |
| pyyaml | 6.0.4 |
| scikit-learn | 1.9.1 (pulls `joblib` 1.6.0, `threadpoolctl` 3.8.0, `narwhals` 2.29.0, `cloudpickle` 3.1.3) |
| statsmodels | 0.15.0 (pulls `patsy` 1.0.3, `packaging` 26.3) |
| matplotlib | 3.11.2 (pulls `contourpy`, `cycler`, `fonttools`, `kiwisolver`, `pyparsing`) |
| pypdf | 7.1.1 |
| Pillow | 12.3.0 (pre-installed) |

### Rebuild the environment

```powershell
$py = "C:\Users\<user>\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py code\_bootstrap_libs.py           # first pass: the main packages
& $py code\_bootstrap_libs2.py          # iterative pass: whatever import is still missing
```

Every script starts with `import fhb_env`, which prepends `.pylibs` to `sys.path` and points
matplotlib at a writable cache directory. If you use a normal (non-sandboxed) environment,
`pip install pyarrow pyyaml scikit-learn statsmodels matplotlib pypdf` is equivalent and
`.pylibs` is unnecessary; the scripts will then import the system packages because
`fhb_env` only *prepends* a path that may not exist.

---

## 3. Run the analysis end to end

```powershell
$py = "…\dependencies\python\python.exe"
& $py code\_dl.py                 # only if data/ is empty
& $py code\01_inspect.py
& $py code\02_yaml.py
& $py code\03_yaml_flat.py
& $py code\04_codebook.py
& $py code\05_audit.py
& $py code\06_catalogue.py
& $py code\07_candidates.py
& $py code\08_audit2.py
& $py code\10_models.py
& $py code\11_validate.py         # ~5 min (bootstrap + refits)
& $py code\12_sensitivity.py      # ~7 min
& $py code\13_confounding.py
& $py code\14_figures.py          # ~2 min
& $py code\15_decision.py
& $py code\16_threshold10_alignment.py   # post hoc, only for the literature comparison
```

Scripts write both to stdout and to `outputs/`. `05_audit.py` and `08_audit2.py` must run
before `07_*`, `10_*` and later, because they create `outputs/fhb_raw2.pkl` and
`outputs/yaml_columns_flat.csv`.

### Determinism

* Maximum-likelihood fits are deterministic.
* Cross-validation folds are deterministic (sorted year/state identifiers).
* The only stochastic steps are the cluster bootstrap (seed `20240101`, 1000–2000
  replicates) and the ridge inner-CV tie-breaking (deterministic grid order). Re-running
  reproduces every table to the printed precision; bootstrap intervals may differ in the
  third decimal if the number of replicates is changed.

---

## 4. Data provenance and integrity

* Files were downloaded from the Zenodo REST API
  (`https://zenodo.org/api/records/23189372/files/<name>/content`) with `urllib`, because
  PowerShell and curl could not complete TLS in this sandbox.
* Downloaded sizes matched the API listing byte-for-byte. MD5 checksums published by
  Zenodo were **not** re-verified (no local md5 tool was used); a re-user should verify them
  if integrity matters.
* The release was not modified. All derived variables and the binary outcome are created in
  code, never by editing `data/`.

## 5. Reproducing the headline numbers

| Claim in `results.md` | Where it comes from |
|---|---|
| 395 events / 604 non-events at S ≥ 5% | `outputs/audit_stats.txt`, `outputs/10_models.txt` §A |
| Primary model ORs and CIs | `outputs/model_estimates.csv` (rows with `model == "M2"`) |
| LOYO/LOSO/K5 AUCs, Brier, calibration | `outputs/cv_summary.csv` |
| Optimism gap | `outputs/optimism_gap.csv` |
| Sensitivity table S1–S11 | `outputs/sensitivity.csv` |
| Within- vs between-year AUC | `outputs/within_between_auc.csv` |
| Year/state fixed-effect checks | `outputs/13_confounding.txt` |
| Decision-threshold table | `outputs/decision_thresholds.csv` |
| Figures 1–5 | `outputs/figures/` |

## 6. Licence

The dataset is CC-BY-4.0 (© the dataset authors). The code and documents here may be reused
with attribution. If you reuse the data, cite the Zenodo record and the associated papers
listed in `comparison_with_literature.md`.
