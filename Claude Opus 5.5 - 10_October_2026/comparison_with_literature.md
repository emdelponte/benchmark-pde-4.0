# Comparison with the literature

**Written after** `results.md` and `critical_assessment.md` were complete (see the 14:20 entry in `analysis_log.md`). Nothing in those two files was changed after the search. Post-literature checks are in `code/05_post_literature.py` / `outputs/models/post_literature_checks.csv` and are labelled as such.

## How the search was done, and its limits

Web searches only. Every attempt to open full texts (PubMed Central, PLOS, APS, DOAJ, Crossref, OpenAlex) was refused by this session's network policy, so **everything below rests on abstracts and search-engine excerpts, not on the papers themselves.** Numbers quoted from excerpts could be misattributed; I flag where a figure could not be checked against its source. A full-text comparison would need those sites to be allowed.

## Studies of this dataset or its predecessors

| Study | Data | Outcome | Approach (per abstract/excerpts) | Reported performance |
|---|---|---|---|---|
| De Wolf, Madden & Lipps 2003, *Phytopathology* 93:428 | 50 location-years, 4 states | epidemic (FHB index ≥ 10%) | logistic regression; narrow windows around anthesis (e.g. hours 15–30 °C, RH ≥ 90%, 7 d pre / 10 d post) | ~84% accuracy (meeting report); independent validation n = 9, accuracy 6% lower |
| Shah et al. 2013, *Phytopathology* 103:906 | 527 obs (31% epidemics) | severity ≥ 10% | LR with indicators for resistance, wheat type and corn residue plus up to 4 weather predictors chosen by leaps-and-bounds with bootstrap selection from **380** candidates; 70/30 split | test misclassification 19% lower than the then-operational models; RH variables captured moisture best |
| Shah et al. 2014, *Phytopathology* 104:702 | 527 obs, 15 states, 26 years | same | boosted regression trees vs the 2013 LR | post-anthesis CV AUCs ~0.87–0.91 (excerpt) |
| Shah et al. 2019, *Phil. Trans. R. Soc. B* 374:20180273 | this dataset lineage | epidemic | scalar-on-function regression on 140-d weather series around anthesis | fitted better than LR; **periods much earlier before anthesis than previously realised** were associated with epidemics; yielded new summary variables (in this dataset) |
| Shah et al. 2021, *PLoS Comput. Biol.* | **999 obs, 273 epidemics / 726 non-epidemics** (same counts as mine) | FHB index ≥ 10% | ensembles of ~38–39 simple, highly correlated LR models (soft voting, weighted averaging, stacking) | ensembles generally better than base models; stacking best; models' Brier scores highly correlated (mean r ≈ 0.87) |
| Shah et al. 2023, *Phytopathology* 113:1483 ("Into the Trees") | this dataset lineage | epidemic | random forests with variable selection (Boruta, varSelRF, VSURF) from 90 candidates; 58 models of ≤ 14 predictors | RF "overall superior" to LR; most frequently selected predictor: **temperature stability in the 20 d before anthesis** |
| Peng, Zhang & Wang 2024, *Infect. Dis. Model.* 9:1138 | 999 obs, 273/726 | same | boosted regression trees on the Shah et al. models' variables; every model included RESIST and a wheat-type × corn-residue variable | simplified pre-anthesis models: CV AUC 0.802 (5-d window) to 0.875 (14-d) (excerpt; CV scheme not seen) |
| Matengu et al. 2024, *Plant Pathology* (review) | — | — | review of weather-based FHB models | not used for numbers |

## Point-by-point comparison

**Prediction objective and outcome.** Same: binary epidemic, FHB index ≥ 10%. My derived outcome (273 / 726) reproduces the counts reported for the 999-row dataset exactly. My choice was disclosed as informed by prior knowledge of this convention, so the agreement is not independent corroboration.

**Weather variables and exposure periods.**
* Agreement: the published LR work found relative-humidity variables to be the best moisture representation. My pre-specified models found mean RH before anthesis to carry nearly all the weather signal, while rainfall-type or "favourable-hours" duration variables did worse.
* Disagreement / what I missed: Shah et al. 2023 found **temperature stability (variability) in the 20 days before anthesis** to be the most frequently selected predictor, and Shah et al. 2019 emphasised periods well before anthesis. I chose mean temperature over the last 10 days, which had no association. Two observations of my own fit their findings. First, my strict-timing model M6 found a positive temperature effect in an earlier window (−20…−10 d). Second, my supplementary random forest (run before the search, but whose importance list I first read after it) ranked TDD.A.1, T.SD.1 and T.MINMAXDIFF.1 (all 20-d pre-anthesis, two of them temperature-variability measures) at the top. *Post-literature check:* replacing mean T with T.SD.1 raises weather-only LOYO AUC from 0.645 to 0.693, and M4 from 0.702 to 0.729. This is **not independent confirmation**: the variable was discovered on (versions of) these same data, so this is in-sample corroboration at best.

**Modeling strategy and complexity.** The published models start from very large candidate sets (380 in 2013, 90 in 2023) with automated selection, include host indicators by default (resistance, wheat type, corn residue), and go up to 4 weather predictors, ensembles of ~39 models, or random forests with up to 14 predictors. My analysis deliberately did the opposite: 2–3 pre-specified weather terms and no search. My results show the cost of selection when it is validated honestly: tuning only the window of two variables (M5) lost 0.035 AUC under LOYO. The literature's selection procedures are more elaborate (bootstrap stability, resampling) but, as far as abstracts show, were not validated by leaving out whole years with selection repeated inside the folds.

**Validation approach.** The abstracts mention a 70/30 split (2013), "cross-validated" probabilities and AUCs (2014, 2021, 2024) and resampling (2023). I could not see whether folds were grouped by year or by weather environment. In these data, 82% of the variance in the outcome lies between weather environments, so this matters. *Post-literature check:* for my M4, row-level 10-fold CV gives AUC 0.716 vs 0.702 under LOYO. Clustering alone therefore inflates M4's AUC by only ~0.015, and adding wheat type × corn (M4b) does not help (0.691 LOYO / 0.715 row-level).

**Predictive performance.** The published AUCs for pre-anthesis models with host variables (~0.80–0.88, Peng et al. 2024 excerpt) are far above mine (0.70–0.73 for host + 2 weather terms under LOYO). From the checks above, the validation scheme and the missing type × corn term explain at most ~0.03 of that gap. The rest probably comes from some combination of (i) more weather terms selected from large candidate sets on these same data, (ii) different validation schemes, and (iii) better-chosen variables (the temperature-variability result suggests part of it is real signal). I cannot separate these without the full texts. If the published figures come from schemes that do not hold out whole seasons, with variable selection outside the folds, they are likely optimistic for forecasting a new season.

**Epidemiological interpretation.** Both bodies of work agree that moisture before anthesis matters and that host resistance and corn residue strongly modify risk. My analysis adds three cautions not visible in the abstracts:
1. The RH signal in these data is a between-season/region signal, absent within state-years (exploratory).
2. State-level prevalence is poorly transported (e.g. MO underpredicted, PA/NY/WI overpredicted).
3. The dataset's "overnight" variables are fixed UTC hours, ≈ afternoon to early morning local time, which affects their biological reading.

## What this independent analysis adds or questions

* **Adds:** an explicit, parsimonious, season-grouped benchmark. With two mechanistically chosen pre-anthesis weather terms, LOYO AUC is ~0.65; with host information, ~0.70. This is a lower reference point that published, heavily selected models should be compared against under the same validation.
* **Exposes:** the clustering structure (545 weather environments, 142 state-years), the day-0 / UTC timing issues, and the absence of a documented binary outcome or site identifiers in the public release. These limit what any analysis of this dataset can claim.
* **Learns from the literature:** temperature *variability* in the ~20 days before anthesis, which I did not consider a priori, appears to carry real predictive information. A future pre-registered analysis should include it as a candidate dimension and test it on seasons not used in its discovery.
* **Suggests:** a common validation protocol for this dataset (leave-one-year-out with selection inside folds, plus state hold-out), which would make the published model families directly comparable.

## Sources (as found by web search; full texts not accessible from this session)
* De Wolf, Madden, Lipps (2003) Phytopathology 93:428–435 — https://www.apsnet.org/publications/phytopathology/2003/April/Pages/93_4_428.aspx
* Shah et al. (2013) Phytopathology 103:906–919, doi:10.1094/PHYTO-11-12-0304-R — https://pubmed.ncbi.nlm.nih.gov/23527485/
* Shah et al. (2014) Phytopathology 104:702–714, doi:10.1094/PHYTO-10-13-0273-R — https://apsjournals.apsnet.org/doi/10.1094/PHYTO-10-13-0273-R
* Shah et al. (2019) Phil. Trans. R. Soc. B 374:20180273 — https://royalsocietypublishing.org/rstb/article/374/1775/20180273/42285/Predicting-plant-disease-epidemics-from
* Shah et al. (2021) PLoS Comput. Biol., doi:10.1371/journal.pcbi.1008831 — https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1008831 ; data: https://datadryad.org/stash/dataset/doi:10.5061/dryad.fn2z34trv
* Shah et al. (2023) Phytopathology 113:1483–1493, doi:10.1094/PHYTO-10-22-0380-R — https://pubmed.ncbi.nlm.nih.gov/36880796/
* Peng, Zhang, Wang (2024) Infectious Disease Modelling 9:1138–1146 — https://pmc.ncbi.nlm.nih.gov/articles/PMC11253225/
* Matengu et al. (2024) Plant Pathology, doi:10.1111/ppa.13839 — https://bsppjournals.onlinelibrary.wiley.com/doi/10.1111/ppa.13839
