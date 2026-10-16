# FHB epidemic prediction benchmark — reproducible analysis

An independent analysis of the Fusarium head blight data matrix v2.1.0 (Zenodo record 23189372; files supplied by the user because zenodo.org was blocked from the analysis environment). The goal was a parsimonious logistic model for the risk of an FHB epidemic (FHB index ≥ 10%), using only weather available by wheat anthesis.

**Bottom line.** Two pre-specified pre-anthesis weather terms (mean RH and mean T over the 10 days before anthesis) give a leave-one-year-out AUC of 0.645 (95% CI 0.55–0.73) and only a small Brier gain over prevalence. That is a weak, season-level signal, carried almost entirely by humidity. Adding cultivar resistance and corn residue raises the AUC to 0.70. See `results.md` and `critical_assessment.md`.

## Files, in the order they were written

| File | Content |
|---|---|
| `analysis_log.md` | chronological record: blocked download, restart, decisions, failures, literature timing |
| `data_audit.md` | dataset description, YAML vs parquet cross-check, quality and clustering audit |
| `analysis_plan.md` | plan v1.0, frozen before model fitting; amendments appended at the end |
| `results.md` | estimates, validation, calibration, sensitivity analyses, final model |
| `critical_assessment.md` | limitations, robustness, robust vs exploratory findings (written before the literature search) |
| `comparison_with_literature.md` | comparison with published work (written after) |
| `code/` | `01_audit.py`, `02_audit_detailed.py`, `03_models.py` (all pre-specified models), `04_exploratory.py` (post hoc), `05_post_literature.py` (post-literature checks), `run_all.sh` |
| `outputs/audit/`, `outputs/models/` | all tables (csv/json) and figures (`calibration_plots.png`, `year_level_calibration_M1.png`) |
| `data/` | input files as supplied (parquet, YAML dictionary, README, csv, rds, codebooks, VariablesMetaData) |

## Reproduce

```bash
cd fhb-benchmark
python3 -m pip install -r requirements.txt
bash code/run_all.sh          # about 2-3 minutes on 2 CPUs
```

Each script takes `<data_dir> <out_dir>` and is run with `python -I` (isolated mode) so nothing in the data folder can shadow a library. All randomness is seeded (`numpy` default_rng 20261010 for bootstraps and CV folds; random forests `random_state=1`). A clean re-run from a copy of `code/` and `data/` reproduced `performance.csv`, `sensitivity.csv`, `coefficients.csv`, `per_group_performance.csv`, `bootstrap.json` and `post_literature_checks.csv` byte for byte.

## Software

Python 3.13.16; pyarrow 26.0.0, PyYAML 6.0.1, pandas 3.0.5, numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1, matplotlib 3.11.2 (pinned in `requirements.txt`). Linux container (Claude Code cloud session).

## Input checksums (MD5)

```
ba455c9687fbe7fd975b79102d031663  data/FHBVer2.parquet
6365e99efcd0b14fda24bb2454ef5165  data/FHBVer2DataDict.yaml
e964800dec97844e225549af632a587e  data/README.txt
968314b6017d31ed5fee74fb0e40b7f6  data/FHBVer2.csv
6553faf6463fcadf82960d57730113b1  data/VariablesMetaData.csv
```

These could not be compared with Zenodo's published checksums (no access to zenodo.org from the analysis environment).

## Known unresolved issues

* No binary epidemic variable is documented; the outcome S ≥ 10% is derived (sensitivity at 5% and 15%).
* Literature comparison is based on abstracts and search excerpts only; full texts were not reachable.
* Weather "environments" (shared station × date) were reconstructed by hashing identical weather vectors; the dataset has no site identifier.
