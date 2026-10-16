# GenAI × Plant-Disease Epidemiology Benchmark (FHB, v4.0)

This repository holds the outputs of autonomous AI agents that were each given the same task: build and critically evaluate a parsimonious logistic model that predicts Fusarium head blight (FHB) epidemics from weather available by wheat anthesis (USWBSI dataset v2.1, Zenodo record 23189372). It also holds a summary report that compares them.

`index.qmd` renders `index.html`, a self-contained report that compares the main results, cross-model agreement and scientific conduct of every model run in this repository.

## Layout

```
benchmark-pde-4.0/
├── index.qmd                 # the report
├── index.html                # rendered report (self-contained)
├── bench_lib.R               # folder discovery, auto-extraction, charts and tables
├── report.css                # styles (light and dark)
├── scorecards/<slug>.yml     # curated numbers, findings and conduct scores, one per run
├── consensus.yml             # which runs agree with each cross-model finding
├── synthesis.yml             # the "bottom line" text
├── Claude Opus 5.5 - 10_October_2026/
├── Gemini Flash 3.8 high - 10_October_2026/
└── GPT-6.1 Sol Medium - 10_October_2026/
```

Each model folder holds that agent's deliverables: `data_audit.md`, `analysis_plan.md`, `code/`, `results.md`, `critical_assessment.md`, `comparison_with_literature.md`, `analysis_log.md` and `README.md`.

## Render

You need Quarto and R with these packages:

```r
install.packages(c("yaml", "knitr", "rmarkdown", "htmltools"))
```

Then, from the repository folder:

```
quarto render index.qmd
```

The report finds the model folders by itself. It looks first in `params: bench_dir` (or `quarto render index.qmd -P bench_dir:/path`), then in `$BENCH_DIR`, then in the folder above the report, and then in the report's own folder. The last of these is the case in this repository.

## Adding a new model or version

1. Add the agent's output folder to the repository, named `Model name - DD_Month_YYYY` (for example `Claude Opus 6 - 02_December_2026`). The date in the name becomes the run's entry date in the report.
2. Re-render `index.qmd`. The new run appears in the charts, tables and timeline. Its card is auto-extracted from `results.md` (the headline and the first AUC with a CI) and marked *auto*.
3. To curate it, copy a file in `scorecards/` to `scorecards/<slug>.yml` (the slug is shown on the card) and fill it in. Then add the run to `consensus.yml` and update `synthesis.yml`. The report warns when the synthesis does not yet cover a run.

## Notes

- Python virtual environments (`.venv/`) and render byproducts are excluded by `.gitignore`. The dataset itself is public on Zenodo and is not needed to render the report.
- The conduct scores and the synthesis were drafted by Claude, which belongs to the same model family as one of the evaluated agents. Treat them as editable judgements, not ground truth.
