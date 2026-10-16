# 01_fit_models.R
# Autonomous Epidemiological Analysis Benchmark — FHB Prediction
# Reproducible R script fitting primary models and executing Leave-One-Year-Out Cross-Validation (LOYO-CV)

suppressPackageStartupMessages({
  library(arrow)
  library(dplyr)
  library(pROC)
})

cat("Loading FHBVer2.parquet in R...\n")
df <- read_parquet("FHBVer2.parquet")

df <- df %>%
  mutate(
    epidemic = as.integer(S >= 10.0),
    env_id = paste(year, state, fdate, sep = "_"),
    resist = factor(resist, levels = c("VS", "S", "MS", "MR")),
    RH_A_PRE7_12H = `RH.A.PRE7.12H`,
    T_9T30_PRE7_24H = `T.9T30.PRE7.24H`,
    TRH_9T30nRHG80_PRE7_24H = `TRH.9T30nRHG80.PRE7.24H`
  )

cat("Total observations:", nrow(df), "\n")
cat("Epidemic prevalence (S >= 10%):", mean(df$epidemic), "(", sum(df$epidemic), "events)\n\n")

# Model definitions
formulas <- list(
  M1 = epidemic ~ RH_A_PRE7_12H,
  M2 = epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H,
  M3 = epidemic ~ RH_A_PRE7_12H * T_9T30_PRE7_24H,
  M4 = epidemic ~ TRH_9T30nRHG80_PRE7_24H,
  M5 = epidemic ~ RH_A_PRE7_12H + T_9T30_PRE7_24H + resist
)

cat("=== FULL DATASET MODEL SUMMARIES ===\n")
for (m_name in names(formulas)) {
  cat("\n----------------", m_name, "----------------\n")
  fit <- glm(formulas[[m_name]], data = df, family = binomial(link = "logit"))
  print(summary(fit))
  cat("AIC:", AIC(fit), "BIC:", BIC(fit), "\n")
}

# Leave-One-Year-Out Cross-Validation
cat("\n=== RUNNING LEAVE-ONE-YEAR-OUT CROSS-VALIDATION (LOYO-CV) ===\n")
years <- sort(unique(df$year))
loyo_preds <- data.frame(matrix(NA, nrow = nrow(df), ncol = length(formulas)))
colnames(loyo_preds) <- names(formulas)

for (yr in years) {
  train_data <- df %>% filter(year != yr)
  test_data  <- df %>% filter(year == yr)
  test_idx   <- which(df$year == yr)
  
  if (length(unique(train_data$epidemic)) < 2) next
  
  for (m_name in names(formulas)) {
    fit_cv <- glm(formulas[[m_name]], data = train_data, family = binomial(link = "logit"))
    loyo_preds[test_idx, m_name] <- predict(fit_cv, newdata = test_data, type = "response")
  }
}

cat("\n=== LOYO-CV VALIDATION METRICS ===\n")
for (m_name in names(formulas)) {
  preds <- loyo_preds[[m_name]]
  roc_obj <- roc(df$epidemic, preds, quiet = TRUE)
  auc_val <- as.numeric(auc(roc_obj))
  ci_val <- ci.auc(roc_obj)
  brier <- mean((preds - df$epidemic)^2)
  
  # Recalibration
  logits <- qlogis(pmax(pmin(preds, 1 - 1e-6), 1e-6))
  cal_mod <- glm(df$epidemic ~ logits, family = binomial)
  cal_slope <- coef(cal_mod)[2]
  
  cat(sprintf("%-4s: LOYO AUC = %.4f [95%% CI: %.3f - %.3f] | Brier = %.4f | Cal Slope = %.4f\n",
              m_name, auc_val, ci_val[1], ci_val[3], brier, cal_slope))
}
