# Benchmark summary report

`benchmark_summary.qmd` renders `benchmark_summary.html`, a self-contained comparison of every model run in the
Drive folder `01_GenAI_PDE_benchmark`. It finds one sub-folder per run, named `Model name - DD_Month_YYYY`, and uses the date in the name as the date the run was added.

## Render

Requires Quarto and R with the `yaml`, `knitr`, `rmarkdown` and `htmltools` packages (`install.packages(c("yaml", "knitr", "rmarkdown", "htmltools"))`).

    quarto render benchmark_summary.qmd

The benchmark folder is looked up in this order: `quarto render benchmark_summary.qmd -P bench_dir:/path`, then `$BENCH_DIR`, then
`~/Library/CloudStorage/GoogleDrive-delponte@ufv.br/Meu Drive/21-workingpapers/01_GenAI_PDE_benchmark`, and finally `./drive_mirror`.
`drive_mirror/` holds only file listings (`_files.txt`) taken from Drive on 16 Oct 2026. It lets the report render
where Drive is not mounted.

## Files

| File | What it is |
|---|---|
| `bench_lib.R` | Folder discovery, auto-extraction for uncurated runs, and the SVG/HTML charts |
| `scorecards/<slug>.yml` | Curated numbers, findings and conduct scores for each run (the slug comes from the folder name) |
| `consensus.yml` | Matrix of which runs agree with each cross-model finding |
| `synthesis.yml` | The "bottom line" text. Its `covers` list makes the report warn when newer runs are not covered |
| `report.css` | Styles (light and dark) |

A new folder with no scorecard still appears. Its card is auto-extracted from `results.md` (the headline and the first AUC with a CI) and marked *auto*.
