# FHB anthesis-time risk benchmark analysis

Completed 2026-10-10 using Zenodo record 23189372, version 2.1.0. Start with results.md for findings and data_audit.md for interpretation. The provisional two-weather-term logistic model has leave-one-year-out AUC 0.616 and Brier 0.193. Discrimination is modest; transportability and cultivar-specific calibration are poor. It is a research model, not an operational recommendation.

The released dictionary contains continuous S but no binary epidemic outcome. The independent audit/plan were frozen before searching papers. A subsequent cited-paper definition, **S>=10%**, enabled the clearly marked literature-informed fitting phase. The original plan was preserved; analysis_plan_revisions.md documents the before-fitting repair. Predictor windows ending day 0 were excluded under the YAML closed-interval convention. The CSV window lengths remain inconsistent with that convention.

## Deliverables

- data_audit.md: source, YAML interpretation, quality, timing and dependency audit.
- analysis_plan.md: original conditional plan, before literature/model fitting.
- analysis_plan_revisions.md: target repair and implementation details, before fitting.
- code/: acquisition, audit, model, report and verification scripts; pinned dependencies.
- results.md: equations, parameter counts, confidence intervals, validation, calibration and robustness.
- critical_assessment.md: uncertainty, limitations and prospective-data needs.
- comparison_with_literature.md: post-independent-analysis comparison.
- analysis_log.md: ordered decisions, access failures, implementation corrections.
- data/raw/: unmodified original Parquet, YAML, CSVs, README, HTML and record JSON.
- data/literature/shah2021.xml: publisher XML used to verify the target equation.
- outputs/: CSV diagnostics, plots, fitted coefficients, prediction records and warning logs.
- outputs/independent_snapshot/: preserved independent documents and SHA256 hashes.

## Reproduce

Run from this directory with Python 3.12.14 (used on macOS ARM64). No R is required. Main versions: pandas 3.0.6, PyArrow 26.0.0, PyYAML 6.0.3, NumPy 2.5.3, SciPy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1 and matplotlib 3.11.2. All transitive versions are pinned in code/requirements.txt; wheel availability on other platforms is not guaranteed.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r code/requirements.txt
.venv/bin/python code/audit.py
.venv/bin/python code/model.py
.venv/bin/python code/plots.py
.venv/bin/python code/report.py
.venv/bin/python code/verify.py
```

Downloaded inputs are already included, so these commands run offline. Scripts use their own location to resolve inputs/outputs. model.py checks that both plans exist and verifies the >=10 equation in the saved publisher XML before deriving the outcome. Fixed physical predictor scaling requires no data-estimated preprocessing. The seed for the 1000 year-block fixed-prediction bootstrap is 20261010. All fits use MLE logistic regression; no hyperparameter search occurs. Expect a few minutes for the audit/model scripts, depending on hardware.

Optional fresh acquisition, requiring internet:

```sh
.venv/bin/python code/download.py
curl -L --fail 'https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1008831&type=manuscript' -o data/literature/shah2021.xml
```

download.py requests the **exact** record version, validates its listed MD5s and preserves originals; it does not follow a moving latest version. It downloads the HTML codebook as supplementary documentation. PDF and RDS duplicates were not needed and are not downloaded. A fresh record API response can include changed usage statistics while file checksums stay fixed. CSV readers used to recompute ranking metrics should use pandas float_precision="round_trip", so serialization does not change ties. plots.py improves chart labels and adds group calibration plots. model.py overwrites generated CSV/PNG/JSON diagnostics; report.py regenerates results.md. Neither rewrites the original plan, chronology, independent snapshot or manually composed assessment/literature review. Historical first-run warnings are retained separately.

Important output definitions: calibration_in_large is an offset intercept with fixed unit slope; calibration_intercept/slope are jointly estimated diagnostics. Bootstrap intervals condition on saved held-out predictions and do not refit models. Frequency weighting by inverse profile size is a training sensitivity; profile-balanced scoring changes evaluation weighting. State/year groups are proxies because actual site IDs are absent. Full equations and units are in outputs/fitted_model.json.

Known limitations and failures are documented in analysis_log.md. The scientific conclusion depends on the supplied closed-window metadata; raw hourly data are needed to resolve the contradictory CSV length convention and support clean weather windows immediately before flowering.
