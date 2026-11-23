# Independent results | proxy endpoint S ≥ 10%
The release supplies no defined binary response. All estimates below concern the analyst-defined severity exceedance. The two-slope additive specification improved both grouped Brier scores and brought both calibration slopes closer to one relative to moisture alone. Retain it as the research candidate. The gain over training prevalence is small and uncertain.

|Validation|Model|ROC AUC|Brier|Calibration offset|Calibration slope|
|---|---|---:|---:|---:|---:|
|Leave year out|Training prevalence|0.353|0.2006|0.006|—|
|Leave year out|Moisture|0.541|0.1995|0.005|0.379|
|Leave year out|Moisture + temperature|0.616|0.1932|0.000|0.773|
|Leave state out|Training prevalence|0.342|0.2015|−0.007|—|
|Leave state out|Moisture|0.536|0.1994|−0.004|0.435|
|Leave state out|Moisture + temperature|0.604|0.1965|−0.058|0.610|
|Train through 2008, test 2009–15|Training prevalence|0.500|0.1939|−0.166|—|
|Same chronological test|Moisture|0.572|0.1906|−0.120|1.144|
|Same chronological test|Moisture + temperature|0.628|0.1890|−0.278|0.727|

Within any mixed-class fold the null AUC is 0.5. Its pooled grouped AUC falls below 0.5 because withholding a high-prevalence group lowers the training prevalence used to predict it. A pooled null slope describes variation between training intercepts and has no individual-risk interpretation. For the additive candidate the paired Brier gains versus training prevalence are 0.0073 (conditional 95% year-bootstrap interval −0.0038 to 0.0185) and 0.0050 (state-bootstrap −0.0020 to 0.0150). Both include zero.

**Full-data equation.** logit(p) = −3.0234 + 0.2823 × (H/24) + 0.7827 × ((T−15)/5), where H is hours with VPD ≤0.635 kPa from days −15 to −5, and T is mean daily air temperature in °C from days −20 to −10. Two predictor parameters and one intercept. Per 24 additional qualifying hours the conditional odds ratio is 1.33 (95% year-cluster interval 1.07–1.64); per 5 °C it is 2.19 (1.32–3.62). Standard errors are cluster sandwich with finite-group correction and a t reference with 31 df. Leaving individual years out gave positive slopes throughout (moisture 0.214–0.336; temperature 0.654–0.943). Plot ID 21, ND 1995, had the largest approximate Cook distance (0.0138). Individual leverage cannot measure shared-environment influence.

**Calibration and variability.** Pooled year predictions averaged 27.32% against 27.33% observed. That agreement conceals deviations within risk strata and groups. In held-out North Dakota (265 plots), predicted risk averaged 34.3% versus 22.6% observed. In the 625 later plots, predicted risk averaged 31.3% versus 26.1% observed. Among estimable groups, year AUC ranged 0.222–1.000 (median 0.750) and state AUC 0.357–1.000 (median 0.600). Small groups can give perfect rankings by chance. Year Brier scores ranged 0.024–0.438 and state scores 0.049–0.378. Group sizes and undefined AUCs are retained in outputs/folds.csv.

![Out-of-fold and chronological calibration in five equally populated risk bins](outputs/calibration.png)

**Robustness.** Shifting only the temperature window five days earlier reduced year/state AUC to 0.590/0.570; chronological Brier deteriorated to 0.2026. Replacing the standalone moisture feature with an earlier RH-day count gave 0.566/0.558; changing only its VPD threshold to 1.1 kPa gave 0.584/0.574. Neither establishes an optimal window or threshold. Under S > 10%, additive year/state AUCs were 0.611/0.599. Giving each state-date equal total weight yielded 0.610/0.617; chronological overprediction increased to 31.0% versus 22.2% observed. Weighted and unweighted Brier scores target different populations. Full sensitivity metrics, coefficients and per-plot predictions are supplied as CSVs.
