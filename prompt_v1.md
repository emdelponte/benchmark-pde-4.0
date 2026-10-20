# **Autonomous Epidemiological Analysis Benchmark — FHB Prediction**

## **Role and objective**

You are acting as an autonomous data analyst with expertise in plant disease epidemiology, statistics, and predictive modeling. Your task is to independently investigate and analyze a publicly available dataset on Fusarium head blight (FHB) of wheat: **Zenodo record:** [https\://zenodo.org/records/23189372](https://zenodo.org/records/23189372). 

The primary objective is to develop and critically evaluate a parsimonious, scientifically defensible model for predicting FHB epidemic risk using weather information available no later than wheat anthesis. This benchmark evaluates your ability to make independent analytical decisions within a realistic epidemiological problem. You are expected to exercise scientific judgment, document your reasoning, recognize limitations, and critically assess your own work. Do not simply maximize predictive accuracy or reproduce an existing published model.

## **1\. Acquire and understand the data**

Access the Zenodo record and download the relevant files, including:

* The primary dataset in **Parquet format (.parquet)**.  
* The variable dictionary and metadata in **YAML format (.yaml or .yml)**.  
* Any README or supplementary documentation available.

Use suitable software libraries to read these formats, such as arrow and yaml in R, or pyarrow and PyYAML in Python. Treat the YAML dictionary as an essential source for interpreting the dataset. Do not infer variable meanings, units, or temporal relationships solely from column names. Cross-check the documentation against the actual Parquet schema. Report inconsistencies, ambiguous definitions, and missing metadata rather than silently resolving them. Identify:

* The observational unit and sample size.  
* Response variables and their definitions.  
* Geographic and temporal coverage.  
* Relevant grouping variables.  
* Weather variables and their measurement units.  
* Timing of weather measurements relative to anthesis.  
* Potential dependencies among observations.  
* Missing data and other data-quality issues.

If files cannot be accessed or essential information cannot be established, document the limitation. Do not fabricate data or metadata.

## **2\. Audit the dataset**

Before fitting models, conduct a structural and exploratory audit. Examine:

* Distribution and prevalence of the binary FHB epidemic outcome.  
* Number of events and nonevents.  
* Geographic and temporal representation.  
* Missing observations and incomplete weather records.  
* Correlations among weather predictors.  
* Extreme or influential observations.  
* Repeated observations or clustering.  
* Possible information leakage.  
* Effective sample size for model development and validation.

Assess whether the data support reliable predictive modeling and identify constraints that should influence the analysis strategy. Pay particular attention to the number of events relative to the number of candidate predictor parameters. Document the audit before proceeding to model development.

## **3\. Define the prediction problem**

The primary task is to predict the probability of an FHB epidemic using information that would realistically be available **at anthesis**.

### **Mandatory scientific constraints**

1. **Prediction timing:** Use only predictors available by anthesis. Exclude post-anthesis weather observations, future outcomes, or variables that incorporate information unavailable at prediction time.  
2. **Response:** Use the documented binary epidemic outcome. If multiple outcome definitions exist, select and justify one before modeling.  
3. **Primary model:** Use logistic regression as the principal predictive modeling framework.  
4. **Model parsimony:** Limit the final model to a maximum of three weather predictor terms. Clearly report the number of estimated predictor parameters, including additional parameters introduced by nonlinear functions or interactions.  
5. **Overfitting control:** Consider the number of events and nonevents relative to model complexity. Do not rely mechanically on a universal events-per-parameter threshold. Explain why the selected complexity is defensible for this dataset.  
6. **Prediction versus explanation:** Distinguish predictive performance from evidence of biological or causal relationships.

These constraints define the scientific problem, not the detailed analytical solution. You retain freedom to determine how best to summarize weather, select candidate predictors, identify biologically meaningful exposure periods, and implement the modeling strategy.

## **4\. Design an independent analysis strategy**

Before fitting predictive models, write analysis\_plan.md.

Specify:

* The prediction target and intended use.  
* Candidate weather variables and exposure windows.  
* Epidemiological reasoning behind candidate predictors.  
* Predictor transformations or aggregations.  
* Approach to addressing collinearity.  
* Model-building and complexity-control strategy.  
* Validation design.  
* Performance metrics.  
* Sensitivity analyses.

You may explore alternative pre-anthesis exposure windows, transformations, and biologically plausible interactions. Do not introduce additional model complexity without justification. Use a simple logistic regression model as a baseline. You may evaluate alternative logistic specifications, including penalization or nonlinear terms, provided they respect the parameter budget and are appropriately validated. More complex algorithms may be used as supplementary exploratory or sensitivity analyses, but they must not replace the primary logistic regression analysis.

### **Validation**

Select a validation strategy appropriate to the geographic and temporal structure of the dataset. Consider leave-one-year-out, leave-one-location-out, grouped cross-validation, or other defensible approaches. Avoid random observation-level splitting when it would produce optimistic estimates because of clustering or dependence. Perform predictor selection, preprocessing, and tuning within training folds whenever required to prevent leakage. Evaluate discrimination, calibration, and overall predictive accuracy using appropriate measures, such as:

* ROC AUC.  
* Brier score.  
* Calibration intercept and slope, where estimable.  
* Calibration plots.  
* Variability in performance across validation groups.

Explain limitations arising from small or imbalanced validation groups.

## **5\. Implement and compare models**

Execute the analysis using reproducible R or Python code. You are responsible for selecting and justifying the specific workflow. At minimum:

* Fit a baseline logistic regression model.  
* Develop at least one scientifically motivated alternative logistic specification.  
* Evaluate the models using the planned validation strategy.  
* Examine predictor effects and their uncertainty.  
* Assess model calibration and robustness.  
* Compare predictive performance with model complexity.

Avoid extensive automated searches over combinations of variables, exposure windows, and transformations without accounting for the resulting selection bias. Do not choose a final model solely because it has the highest observed AUC. If the dataset cannot support a reliable predictive model, explain why. A scientifically justified conclusion that the data are insufficient is an acceptable benchmark outcome.

## **6\. Critically evaluate your analysis**

Assess the strengths and weaknesses of your workflow. Discuss:

* Whether the selected weather predictors are epidemiologically plausible.  
* Whether the sample size supports the estimated model complexity.  
* Potential overfitting and optimism.  
* Sensitivity to exposure-window definitions.  
* Predictor redundancy and instability.  
* Variation in performance across environments.  
* Calibration and transportability.  
* Limitations of retrospective observational data.  
* What additional data would be needed for prospective validation.

Distinguish robust findings from exploratory observations. If important problems are discovered, you may revise the analysis, but document what changed and why. Do not silently replace unsuccessful models or omit negative results.

## **7\. Compare with the literature only after independent analysis**

After completing and documenting the independent analysis, search for peer-reviewed studies that previously analyzed this dataset or closely related versions. Compare:

* Prediction objectives.  
* Weather variables and exposure periods.  
* Modeling strategies.  
* Model complexity.  
* Validation approaches.  
* Predictive performance.  
* Epidemiological interpretations.

Identify where your results agree or disagree with previous studies. Discuss whether your independent analysis provides additional insights, exposes limitations, or suggests alternative approaches. Do not retroactively present published modeling choices as decisions made independently. Clearly distinguish findings obtained before and after the literature search.

## **8\. Deliverables**

Create the following outputs:

1. data\_audit.md — dataset description, metadata interpretation, and quality assessment.  
2. analysis\_plan.md — analysis strategy written before model fitting.  
3. code/ — executable and reproducible analysis scripts.  
4. results.md — model estimates, diagnostics, and validation results.  
5. critical\_assessment.md — limitations, uncertainty, robustness, and alternative interpretations.  
6. comparison\_with\_literature.md — comparison with previous studies, performed after the independent analysis.  
7. analysis\_log.md — chronological record of decisions, changes, failed attempts, and reasons.  
8. README.md — instructions for reproducing the analysis, including software versions and dependencies.

Preserve the original analysis plan and record subsequent revisions rather than overwriting earlier decisions. Report any unsuccessful analyses, computational failures, or unresolved problems.

## **9\. Principles of autonomous scientific reasoning**

You are expected to:

* Make decisions rather than repeatedly request instructions.  
* Explain consequential analytical choices.  
* Recognize when the data do not support a proposed analysis.  
* Prefer defensible, interpretable models over unnecessary complexity.  
* Use epidemiological knowledge to guide the investigation.  
* Challenge your own assumptions and conclusions.  
* Distinguish observed evidence from speculation.  
* Document the reasoning process sufficiently for independent assessment.

The objective of this benchmark is not to identify which AI agent achieves the highest predictive accuracy. It is to determine whether an autonomous analytical agent can design, execute, critique, and improve a scientifically defensible epidemiological analysis under realistic constraints.

