# Revision 1 — literature-informed target repair, before model fitting

Date: 2026-10-10. The independent audit, original plan, results and critique were frozen in outputs/independent_snapshot before the first literature search. Their hashes are preserved. This revision does not retroactively change independent decisions.

The cited [Shah et al. 2021 study](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1008831), Equation 1, defines y=1 when S>=10%, otherwise 0. Its publisher XML was downloaded to data/literature/shah2021.xml; MathML confirms the inclusive inequality (the browser showed an equation image). Applying it to this release gives 273/999 events and 726 nonevents, exactly matching the paper. Its sample size, resistance counts and years also agree. This supports using that operational definition for a **literature-informed continuation**, although a record-by-record identity comparison with the original publication's data has not been performed. The binary label is derived transparently from documented continuous S, not present as a supplied column.

Preserve all original weather candidates, transformations and grouped validation choices. Do not copy the paper's model equations or agronomic predictor choices. Only the target gate is repaired. The baseline, alternative and nonlinear/window sensitivities remain those in analysis_plan.md. Fit the fixed models without predictor selection, tuning or random observation-level splitting.

## Target audit before fitting

Events=273, nonevents=726, prevalence=27.327%; two rows equal exactly S=10 (>= is material). There are nine single-class year groups and four single-class states; group AUC is undefined there. Full outcome distributions are in outputs/target_by_year.csv, target_by_state.csv, target_by_resist.csv and target_by_type.csv. Years/states with few events remain weak validation units even when both classes exist. Resistance prevalences are 46.67% VS, 32.04% S, 22.07% MS and 12.97% MR; this creates an omitted-host-information limitation for the weather-only estimand.

The baseline moisture variable ranges 46–238 hours, and T.A.2 9.759–24.490 degC; their Pearson r is -0.301. No missing predictor values need imputation. One-to-three predictor parameters are plausible for an initial fixed-specification analysis relative to 273/726 row-level outcomes, but repeated weather environments and 32 years limit effective information and uncertainty. Quantify unique profiles carrying events/nonevents before fitting; do not claim 273 independent epidemics. No automatic feature search is justified.

## Concrete robustness implementation

Run leave-one-year-out for all prespecified specifications; leave-one-state-out and a <=2008 versus >=2009 temporal holdout for the baseline and two-term alternative plus intercept reference. Report negative as well as positive results. Estimate full-data coefficients with year-clustered covariance, Wald confidence intervals using t(31) critical values (approximate, uneven clusters), and prediction influence using ordinary-GLM Cook distance. Perform leave-one-year deletion coefficient ranges, duplicate removal and profile-balanced training weights (1/profile size, normalized to mean 1) as sensitivity analyses for the baseline/two-term alternative.

Use 1000 year-block resamples of fixed year-out predictions for AUC/Brier intervals and paired Brier differences; these intervals do not include full refitting uncertainty. Fixed 5 equal-width reliability bins show denominators; include a scatter of predictions versus observed group prevalence. No recalibration is fitted and applied to held-out observations; calibration regressions are diagnostics only. Avoid unstable per-group calibration estimates; per-group AUC/Brier/prevalence/mean prediction reveal variability.

After fitting, choose a provisional research specification based on calibration, Brier, parsimony and stability together; explicitly acknowledge selection based on these same validation data and consequent optimism. No claim of prospective validation or operational readiness.
