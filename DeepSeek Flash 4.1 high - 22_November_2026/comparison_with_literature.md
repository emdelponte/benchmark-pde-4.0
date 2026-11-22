# Comparison with the literature

**This file was written only after the independent analysis was complete.** The modelling
choices above were fixed in `analysis_plan.md` before any literature was consulted, and the
literature search was delegated and run last. Where a published choice coincides with mine,
that is noted as a coincidence; where it differs, the difference is discussed rather than
retrofitted. A "before/after" summary is in §8.

---

## 1. What was searched, and how much to trust it

I searched the four publications listed by Zenodo as *isReferencedBy*, the four papers cited
in the dataset README, and other FHB weather-risk work (2015–2026). Metadata were verified
against Crossref, PubMed/Europe PMC, DataCite and OpenAlex; full text was available for the
two open-access papers (PLoS Computational Biology; Phil. Trans. R. Soc. B). Publisher pages
for the APS journals were not readable (Cloudflare), so their abstracts came from
publisher-supplied Crossref JATS deposits. Every number below is either quoted from an
accessible abstract/full text or explicitly marked as unverified. A small number of details
could **not** be verified (see §7) and are not used to support any conclusion.

DataCite's citation graph for this record lists exactly the four legacy papers
(`citationCount: 4`), and I found no independent third-party peer-reviewed re-analysis of
the deposited 999-row file. So "the literature on this dataset" is, at present, the authors'
own series.

---

## 2. The single most important finding: the "documented binary outcome" exists — in the
literature, not in the release

The audit (`data_audit.md` §3) concluded that the release documents only the continuous FHB
index `S` and no binary outcome. That was correct **for the release**. But the associated
literature has used a binary outcome all along:

* Shah et al. (2013, *Phytopathology* 103:906–919) define a "major epidemic" as FHB severity
  **≥ 10%**.
* Shah et al. (2019a, *Phytopathology* 109:96–110) use **FHB index ≥ 10%**.
* Shah et al. (2019b, *Phil. Trans. R. Soc. B* 374:20180273) report **999 observations,
  273 epidemics and 726 non-epidemics**.
* The boosted-regression-tree (2014) and random-forest (2023) papers use the same binary
  framing.

I recomputed the cut-points **before** knowing this. My sensitivity table
(`outputs/sensitivity.csv`) gives, for `S ≥ 10%`, **273 events of 999** — an exact match to
the published 273/999. That is a strong independent confirmation that the canonical binary
outcome of this data matrix is `S ≥ 10%` and that it is reconstructible from `S` alone.

**What this means for my analysis.** My pre-registered outcome (`S ≥ 5%`, 395 events) is
*not* the field convention. It was fixed before the literature search and I have not changed
it (that would be exactly the retrofitting the brief warns against), but the comparison below
is run at **both** thresholds, and the 10% results are the like-for-like ones. The 5% choice
is defensible on its own terms (it captures moderate epidemics that the 10% rule calls
non-epidemics), but a reader should know that the published models answer a stricter
question.

Post hoc alignment at 10% (`code/16_threshold10_alignment.py`,
`outputs/threshold10_alignment.csv`, LOYO grouped CV):

| Specification | k (weather + agronomic) | LOYO AUC [95% CI] | Brier | Calib. slope |
|---|---|---|---|---|
| prevalence only | 0 | 0.500 | 0.199 | — |
| mean RH, −7…0 d | 1 | 0.658 [0.605, 0.709] | 0.188 | 0.90 |
| RH ≥ 90 h, −7…0 d | 1 | 0.615 [0.564, 0.667] | 0.194 | 0.83 |
| De Wolf (2003) term: h 15–30 °C & RH ≥ 90%, −7…0 d | 1 | 0.552 [0.492, 0.610] | 0.200 | 0.43 |
| warm–wet h 9–30 °C & RH ≥ 80%, −7…0 d | 1 | 0.636 [0.581, 0.689] | 0.190 | 0.90 |
| **M2, primary** (RH ≥ 90 h + T > 30 h) | 2 | **0.616 [0.569, 0.665]** | 0.194 | 0.78 |
| M5 (warm–wet h + T > 30 h) | 2 | 0.639 [0.586, 0.691] | 0.190 | 0.86 |
| mean RH + T > 30 h | 2 | 0.661 [0.606, 0.709] | 0.189 | 0.86 |
| M4 (M2 + resistance + corn) | 4 (2+2) | 0.689 [0.647, 0.731] | 0.182 | 0.87 |
| mean RH + resistance + corn | 3 (1+2) | **0.719 [0.674, 0.761]** | 0.175 | 0.91 |

At the convention threshold, the best *parsimonious* model I can build from pre-anthesis
weather plus two agronomic covariates reaches AUC ≈ 0.72 — still below the published
0.79–0.90 range, for reasons discussed in §5.

---

## 3. Paper-by-paper comparison

| Paper | Data | Response | Weather/windows | Model, complexity | Validation | Reported performance |
|---|---|---|---|---|---|---|
| **De Wolf, Madden & Lipps (2003)** *Phytopathology* 93:428–435, doi:10.1094/PHYTO.2003.93.4.428 | 50 location-years, 4 states (independent lineage) | binary epidemic classification (cut-point not in abstract) | 7 d pre-anthesis and 10 d from anthesis; T, RH, rain duration | stepwise logistic, few terms | independent set of 9 location-years | accuracy 62–85%; all-weather model 84% of 50 location-years; **pre-anthesis-only model 70%**; independent validation 6% lower |
| **Shah, Molineros, Paul, Willyerd, Madden & De Wolf (2013)** *Phytopathology* 103:906–919, doi:10.1094/PHYTO-11-12-0304-R | 527 obs (predecessor matrix) | binary, **severity ≥ 10%** (31% major epidemics) | 380 candidate variables, 5/7/10/14/15-d windows pre **and** post anthesis; + resistance, wheat type, corn residue | logistic regression, leaps-and-bounds + bootstrap selection; 15 final models, **≤4 weather predictors each** | 70/30 train/test | mean test misclassification 19% lower than the then-current national system (absolute rate not in abstract) |
| **Shah, De Wolf, Paul & Madden (2014)** *Phytopathology* 104:702–714, doi:10.1094/PHYTO-10-13-0273-R | 527 obs | binary ≥ 10% | 350 weather variables | boosted regression trees | 369 train / 158 test | **test misclassification 0.23**, 31% better than the 15 logistic models; strongest predictors mean daily RH, mean daily T, hours 9–30 °C & RH ≥ 90%; risk rises sharply above mean RH 70% |
| **Shah, De Wolf, Paul & Madden (2019a)** *Phytopathology* 109:96–110, doi:10.1094/PHYTO-11-17-0386-R | 865 obs, 16 states, 31 y | binary, **FHB index ≥ 10%** | 94 series, **120 d pre- to 20 d post-anthesis** | functional data analysis: penalised cubic B-splines + function-on-scalar regression (inference, not a classifier) | none reported | no AUC/accuracy reported; epidemic and non-epidemic mean curves **diverge from ~40 d pre-anthesis**, maximal separation near anthesis; moisture (mean RH) and temperature **variability** separate the classes |
| **Shah, Paul, De Wolf & Madden (2019b)** *Phil. Trans. R. Soc. B* 374:20180273, doi:10.1098/rstb.2018.0273 | **999 obs: 273 epidemics / 726 non-epidemics** | binary (≥ 10% by reconstruction) | 12 prior logistic models (5–15 d windows, pre or post), 6 scalar-on-function models (120 d pre – 20 d post), 8 new logistic models | 26 models: logistic + penalised scalar-on-function | AIC comparison; AUC/Se/Sp at Youden cut-point; no external holdout | s-o-f mean misclassification **0.237** vs **0.310** for logistic models; mean AIC 932 vs 1044 (original lr); **windows crossing anthesis were better predictors than windows restricted to either side** |
| **Shah, De Wolf, Paul & Madden (2021)** *PLoS Comput. Biol.* 17:e1008831, doi:10.1371/journal.pcbi.1008831 | 999 obs | binary epidemic/no-epidemic | 39 logistic base learners, ≤4 weather predictors each from ~300 candidates, + resistance, type, residue | ensembles: soft voting, Brier-weighted averaging, penalised stacking | nested cross-validation | mean **Brier 0.160–0.183 (mean 0.171)**; stacking **+12.7% ROC-AUC** over the mean base learner, +24% PR-AUC (absolute AUCs only in figures) |
| **Shah, De Wolf, Paul & Madden (2023)** *Phytopathology* 113:1483–1493, doi:10.1094/PHYTO-10-22-0380-R | ~999 obs, >300 predictors | binary | 90 candidates; selected ≤14 per model | random forests with Boruta/varSelRF/VSURF selection | nested CV (10 × 10) | **mean ROC-AUC 0.898 (0.792–0.972)** ⚠ provisional (see §7); top predictor = **temperature-stability variable in the 20 d before anthesis** |

Related but not using this dataset: Kriss, Paul & Madden (2010, *Phytopathology*
100:784–797) found moisture windows of 15 and 30 d near anthesis positively correlated with
FHB and **no significant temperature-only correlations**; de Carvalho & Del Ponte (2026,
*Plant Pathology* 75:e70173) modelled Brazilian FHB at a >10% threshold and report individual
ROC-AUC 0.79–0.81, ensemble ≤0.84, leave-one-year-out/leave-one-location-out 0.75–0.83;
Alves et al. (2025, *Phytopathology* 115:1329–1343, with Shah) warn that random forests
overfit small epidemiological datasets and settle on a 4-predictor spline logistic model
(C = 0.77).

---

## 4. Where my results agree with the literature

1. **Pre-anthesis moisture is the dominant weather signal** — specifically RH-based
   variables. My best single weather term is mean RH over −7…0 d (LOYO AUC 0.635 at 5%,
   0.658 at 10%), and RH ≥ 90 h counts are positive and significant with OR 1.13 per 10 h.
   That is the same family the logistic/BRT lineage repeatedly selects (mean daily RH,
   hours RH ≥ 90, TRH combinations). Kriss et al. (2010) found the same and, like me,
   **no temperature-only signal**.
2. **Pre-anthesis-only weather is informative but weaker than weather spanning anthesis.**
   De Wolf et al. (2003): 70% vs 84% accuracy; Shah et al. (2019b): windows crossing
   anthesis fit best (mean AIC 999 vs ~1052 for pre-anthesis models). My models are
   pre-anthesis-only by design, and they land in exactly the weaker range those papers
   describe. My result is therefore not a contradiction of theirs — it is what their own
   pre-anthesis-only comparison predicts.
3. **Agronomic covariates carry a large share of the signal.** Resistance class
   (OR 0.59 per step) and corn residue (OR 2.47) dominate my weather terms and lift LOYO
   AUC from 0.62 to 0.69 at 10% (0.69–0.72 with mean RH). Every paper in this lineage
   includes resistance, wheat type and residue in its models, and Shah et al. (2019b)
   report mean AIC 992 for two scalar predictors vs 1030 for a resistance-only model, i.e.
   agronomy materially improves fit.
4. **No single best model, and predictors are interchangeable.** Shah et al. (2013)
   explicitly say that because predictors are intercorrelated "no single best model" exists.
   That is precisely what I found: mean RH, warm–wet hours and RH ≥ 90 h give AUC 0.57–0.66
   with overlapping intervals, and window choice (5/7/10/14/15 d) is not identifiable.
5. **Skill is modest in absolute terms.** Published misclassification 0.23–0.31 at ~27%
   prevalence, and the authors themselves note that "overlapping fitted-probability
   distributions … highlight the difficulty in accurately predicting FHB epidemics from
   local environmental data" (Shah et al. 2019b). My Brier 0.175–0.194 at 10% and
   calibration slopes 0.78–0.91 are consistent with that assessment.
6. **Simple logistic regression remains competitive** with tree ensembles when the number
   of predictors is honest and the validation is grouped (my M4 at AUC 0.69 vs the RF
   paper's 0.90; see §5 for why those are not directly comparable).

---

## 5. Where my results differ, and why

### 5.1 Absolute performance is lower (AUC ≈ 0.62–0.72 vs published 0.79–0.90)
Five differences explain most of the gap, in descending order of importance:

1. **Post-anthesis information.** The published models mostly use windows that cross or
   follow anthesis (Shah 2019b's best logistic models; RF models with 14 predictors drawn
   from 90 candidates that include post-anthesis windows). Post-anthesis wetness is the
   proximal driver of infection. My constraint forbids it. This is a design difference, not
   a performance failure: my models answer the question "what can be said *at* anthesis".
2. **Validation design.** Shah et al. (2013, 2014) use random 70/30 plot-level splits and
   the 2021/2023 papers use (nested) CV over observations. In this dataset **719 of 999
   plots share their entire weather record with another plot** (max 8 plots per record,
   median 2 plots per trial). Random plot-level splitting therefore puts identical weather
   vectors, and the same epidemic environment, in both training and test folds. My grouped
   LOYO/LOSO design removes that leakage, and the optimism gap I measure (0.03–0.05 AUC
   even for 2-parameter models) shows how much such splitting can inflate a result. Part of
   the published AUC advantage is plausibly this.
3. **Number of predictors.** Their logistic models use up to 4 weather predictors selected
   from 380; the RF paper uses up to 14 from 90. My budget is 2 weather terms by the brief.
4. **Threshold.** Their performance is quoted at 10%; at that threshold my numbers improve
   (M2 0.560 → 0.616; M4 0.657 → 0.689), so the like-for-like comparison is less
   unfavourable than a 5%-vs-10% comparison would suggest.
5. **What is being summarised.** They report test-set misclassification or AUC from a single
   split; I report pooled out-of-fold AUC over 32 held-out years, which is dominated by
   between-year prevalence shifts (visible in the popularity of year-level ranking: my
   weather-only models have between-year AUC 0.64–0.72 but within-year AUC 0.53–0.58).
   A pooled AUC and a within-sample AUC are different estimands.

### 5.2 Temperature: my null vs the random-forest finding
My heat-stress term (hours T > 30 °C) is null in every binary model and protective only in
the continuous-outcome model. Shah et al. (2023) report that the most frequently selected
RF predictor was a **temperature-*stability* variable in the 20 d before anthesis**, and
Shah et al. (2019a) found temperature *variability* discriminated the classes. These are not
direct contradictions — I never tested temperature variability, because I excluded all
`SD` and `MINMAXDIFF` variables a priori as "second-order proxies" (`analysis_plan.md` §3).
**That exclusion may have been wrong.** It is the clearest case in which the literature
suggests my candidate set was too narrow. I have not re-run the analysis to chase it (that
would be post-hoc selection on the same data), but it is recorded as a limitation and a
priority for future work.

### 5.3 The role of "temperature" in my models
Mean temperature entered only at p = 0.052 (M3, OR 1.07 per °C) and slightly worsened
calibration; adding it did not improve LOYO AUC. This agrees with Kriss et al. (2010)
("no significant temperature-only correlations") and with Shah et al. (2019b)'s
finding that single-series models on RH alone were no better than logistic models, while
disagreeing with the RF paper's emphasis on temperature stability. The balance of evidence
across papers and my analysis favours moisture as the primary axis and treats temperature as
a second-order or variability (not level) effect.

### 5.4 De Wolf et al.'s specific pre-anthesis term is a poor discriminator in this dataset
The classic 2003 term "hours with 15 ≤ T ≤ 30 °C and RH ≥ 90% in the 7 d pre-anthesis"
(`TRH907`) is a **significant** predictor in my data (OR 1.19 per 10 h, p = 0.0005) but it
discriminates poorly on its own (LOYO AUC 0.552 at 10%). Interpretation: the variable is
directionally right but its reference range in the multi-state matrix is compressed (mean
18 h of 192, many zeros), so a 2-parameter logistic built on it cannot rank plots. This is a
useful caution about importing a regional model's variable into a national dataset.

### 5.5 What the published work does not report
None of the papers reports **calibration** (intercept/slope), decision-analytic performance
(sensitivity/specificity/PPV at a stated cut-off), the **between-year vs within-year**
decomposition, or an explicit treatment of the shared-weather-record dependence. My
contribution on those four points is not a disagreement; it is an addition.

---

## 6. What my independent analysis adds

1. **A metadata audit of the release** (the sign-convention conflict between the YAML and
   `VariablesMetaData.csv`, the 11-h vs 12-h "overnight" contradiction, the fact that the
   "7 d" window is 8 calendar days, the missing 24-h VPD for −7…0 d, the absent binary
   outcome, and the UTC/local misalignment that makes all `12H` variables biologically
   uninterpretable). None of this is in the codebook.
2. **An exact reconstruction of the field's binary outcome** (`S ≥ 10%` → 273/999 events),
   which makes the release usable for comparisons without external metadata.
3. **Grouped validation** (LOYO/LOSO/chronological blocks) and a quantification of how much
   optimism the shared weather records imply. This is the methodological point most likely to
   matter to future users of the dataset.
4. **The between-year/within-year decomposition**: pre-anthesis weather is a *season*
   classifier, not a *plot* classifier. That reconciles "moisture is consistently
   associated with FHB" with "AUC is only 0.6": both are true, and they answer different
   questions.
5. **Calibration and decision-analytic reporting**, which shows that even the better
   agronomic model flags a quarter of plots to catch a third of epidemics.

---

## 7. Unverified items (do not rely on these)

* **Shah et al. (2023) mean ROC-AUC 0.898 (0.792–0.972).** Obtained from search-engine-
  indexed text of the publisher PDF (the APS full text was blocked). The qualitative claims
  (58 models, ≤14 predictors, temperature-stability predictor, nested CV) come from the
  Crossref abstract and are solid; the AUC value should be treated as provisional.
* **Absolute misclassification rate of the 15 Shah et al. (2013) models** — not in the
  abstract. Arithmetic from the 2014 paper ("31% lower than 0.23") implies ≈0.33, but that
  is inference, not a quoted value.
* **The 10% cut-point in Shah et al. (2019b)** is inferred from the 273/999 count and from
  the companion papers, not quoted from that paper's Methods.
* **Shah et al. (2019a) predictive performance** — not reported in the abstract; the paper
  is an inferential functional analysis, not a prediction study.
* **De Wolf et al. (2003) epidemic cut-point** — not stated in the abstract.
* Interpreting the 2023 and 2019a "temperature stability" findings is limited to abstract
  level; I did not read those methods.

---

## 8. Before/after: what changed because of the literature

| Item | Before the search (independent) | After the search |
|---|---|---|
| Binary outcome | none documented in the release; I defined `S ≥ 5%` a priori and flagged the gap | the field convention is `S ≥ 10%`, reconstructible as 273/999; my 5% choice stands as pre-registered but is now known to be non-standard, and 10% results are reported alongside |
| Primary predictor family | RH-based moisture, chosen from the audit's univariate screen and mechanism | same family as the published LR/BRT work — coincidence of reasoning, not borrowed |
| Temperature | heat hours (> 30 °C) null; mean T borderline | published RF work emphasises temperature *variability* pre-anthesis, which I excluded a priori; recorded as a candidate-set limitation |
| Expected performance | "modest, AUC ~0.6" | published AUC 0.79–0.90 exists, but with post-anthesis windows, ≥4–14 predictors and (mostly) random plot-level splits; my lower value is explained, not overturned |
| Validation | grouped LOYO/LOSO, cluster bootstrap | unchanged; the literature's random splits are an additional argument for the grouped design |
| Interpretation | weather ranks seasons, not plots | unchanged; the literature's accuracy/misclassification figures are consistent with it |

**No number in `results.md` was changed after the literature search.** The only new numbers
are in §2 above (post hoc 10%-threshold alignment) and they are labelled as such in
`code/16_threshold10_alignment.py`.
