# Original independent analysis plan — frozen before any predictive fitting

Date: 2026-10-10 (America/Sao_Paulo). This file is preserved; changes belong in analysis_plan_revisions.md. No peer-reviewed modeling paper was consulted to choose this plan. The record and README expose citations, but their modeling methods were not inspected during this stage.

## Target, timing, and decision gate

Predict the probability of the **documented binary FHB epidemic outcome** for a fungicide-untreated wheat observation using weather available at the documented anthesis reference, 00 UTC on flowering date. Intended use is retrospective development of an interpretable warning probability, with prospective evaluation required before management use. The estimand is initially the sampled mixture of cultivar resistance and wheat types, not an individual cultivar-specific or national population risk.

The audit finds only the continuous response S (FHB index, percent), no binary response and no epidemic cutoff in the YAML, README, CSV metadata, or supplementary HTML codebook. Therefore the primary model is gated: **do not invent an outcome or fit logistic regression to S**. Events, nonevents, effective event counts and adequacy for fitting cannot be established for the requested target. Independent analysis ends in a documented identifiability/metadata limitation unless an authoritative definition is established. Literature will only be examined after these independent findings are recorded; any ensuing definition and fits must be labeled as a revised, literature-informed continuation.

## Outcome-blind candidate specifications, conditional on a valid target

Use YAML windows as closed intervals. Exclude every weather summary ending at day 0 or later. Do not infer safety from the word PRE. Full day 0 is unavailable at 00 UTC. Use original aggregates, without attempting to reconstruct hourly weather or change endpoints. No station-level coverage or latency is available to verify operational availability.

- Baseline: intercept plus VPD.L635.CHD.1 / 24, a count of hours with VPD <= 0.635 kPa in days [-15,-5], expressed as 24-hour equivalents. One weather term and one predictor parameter.
- Alternative: add T.A.2, mean daily air temperature (degC) in [-20,-10], centered at 15 degC and divided by 5. Two weather terms and two predictor parameters.
- Sensitivity: add the squared scaled temperature term to the two-predictor model, to allow a temperature optimum. Three weather terms and three predictor parameters, plus one intercept. Treat it as exploratory; no interaction or spline search.
- Window sensitivity: replace T.A.2 with T.A.1 ([-25,-15]) and separately T.A.3 ([-40,-30]); keep the moisture variable unchanged. This evaluates limited thermal-window sensitivity, not a complete sensitivity analysis of moisture windows. Day-0-free near-anthesis moisture alternatives are scarce.

Low VPD provides a moisture proxy potentially relevant to inoculum development and survival before flowering. Temperature affects fungal development but a simple monotone effect may fail across thermal ranges; moisture proxies do not measure rainfall, leaf wetness, inoculum or infection directly. The available periods omit the last four days before day 0 and all flowering-day weather; these compromises constrain biologic relevance. These are hypotheses, not causal assertions.

Do not include redundant low-VPD thresholds together (r=0.939), dewpoint plus correlated temperature without justification, pressure as a presumed mechanism, resistance/corn/type in the weather-only primary model, or precomputed interactions with post-anthesis weather. The candidate set is fixed from metadata and outcome-blind audit, not an automated search through 329 summaries. Plot correlation and inspect predictor ranges; do not discard extreme observations merely for being extreme.

## Complexity and fitting

If the target is validated, use unpenalized maximum-likelihood binomial logistic regression. Count predictor parameters explicitly: 1, 2 or 3, plus intercept. No selection or tuning; the baseline is the parsimonious default. Retain the alternative only if calibration/Brier and group stability support the extra term; AUC alone is insufficient. Separation, convergence failures, large standard errors and covariance warnings must be retained in the log. If MLE fails, report rather than silently replace it. A prespecified ridge sensitivity may be added only with a written revision and tuning nested within training groups; it is not currently planned.

999 rows are not 999 independent environments. There are 545 identical complete weather profiles, 142 state-years, and only 32 observed years. Event counts cannot be assessed before a target definition. Assess events and nonevents per fold and within these dependency proxies; maximum three parameters is a cap, not a guarantee of adequate information. No universal events-per-parameter rule establishes sufficiency.

## Validation and performance

Primary validation: leave one observed year out, with all its observations held together. It evaluates a withheld historical year; training on later years means it is not forward deployment validation. Secondary validation: leave one state out. Actual site IDs are unavailable, so do not call this leave-one-location-out. Temporal deployment sensitivity: develop on years <=2008 and evaluate >=2009, provided both classes exist. That split also changes cultivar mixture and sample intensity, which must be reported.

All coefficients are fitted on training data only. Fixed physical scales require no estimated preprocessing; any future imputation or transformation estimated from data must be learned in training folds. Preserve rows and dependency groups, including unresolved duplicate records, and conduct a duplicate-removal sensitivity if modeling becomes possible.

Report pooled out-of-fold ROC AUC, Brier score, log loss, calibration-in-the-large (offset regression intercept with slope fixed at 1), and jointly estimated calibration intercept/slope, explicitly distinguishing them. Compare to an intercept-only model fitted within each training fold. Provide group-level metrics, marking AUC as not estimable in single-class groups, and calibration as unreliable in tiny groups. Use reliability plots and show bin denominators; do not interpret pooled calibration as universal subgroup calibration. Assess uncertainty using year-block bootstrap of out-of-fold predictions, recognizing that this does not refit the entire model and conditions on the chosen features. Use year-clustered covariance for full-data coefficients with a finite-cluster caveat. Report apparent performance separately, if at all.

## Robustness and stopping rules

Inspect influential observations only after fitting (Cook distance and coefficient sensitivity); standardized predictor extremes are not proof of influence. Evaluate thermal windows, nonlinearity, duplicates, environment weighting, temporal shift and resistance-specific calibration without choosing a new winner for every sensitivity. Treat additional specifications as exploratory. No practical action threshold is chosen without costs, benefits and prospective validation. If target identity or predictor availability cannot be established, report missing quantities rather than invented estimates.
