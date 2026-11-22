# ==============================================================================
# 02_model_fitting_and_validation.R
# Pre-specified logistic regression models (M0-M5) + exploratory benchmarks,
# evaluated under Leave-One-Year-Out (LOYO), Leave-One-State-Out (LOSO), and
# 5x10-fold Grouped (state x year) Cross-Validation
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(pROC)
  library(glmnet)
  library(mgcv)
})

set.seed(20261122)
dir.create("output", showWarnings = FALSE)

# 1. Load primary Parquet dataset and audit metadata
df <- as.data.frame(nanoparquet::read_parquet("data/FHBVer2.parquet"))
aud <- readRDS("output/audit_artifacts.rds")
w_check <- aud$w_check

# Construct primary binary outcome Y = I(S >= 10%) and grouping keys
df$epid10 <- as.integer(df$S >= 10)
df$state_year <- paste(df$state, df$year, sep = "_")

pre_cols_all <- w_check %>% filter(analysis_period == "pre", !deprecated) %>% pull(name)
w_hash_pre <- apply(df[, pre_cols_all], 1, function(r) paste(signif(r, 12), collapse = "|"))
df$env_id <- as.integer(factor(w_hash_pre))

# Candidate pool for M5 nested L1 selection:
# 24h pre-anthesis variables with window_start_day >= -30 (excluding 12H UTC-shifted & >30d proxies)
m5_pool_cols <- w_check %>%
  filter(analysis_period == "pre", !deprecated, day == "24h", window_start_day >= -30) %>%
  pull(name)
cat("M5 candidate 24h pre-anthesis pool (window_start_day >= -30):", length(m5_pool_cols), "variables\n")

# ------------------------------------------------------------------------------
# Helper functions: Cluster-robust SEs, PR-AUC, Calibration, Evaluation Metrics
# ------------------------------------------------------------------------------
cluster_vcov_logit <- function(fit, cluster) {
  X <- model.matrix(fit)
  y <- fit$y
  p <- fitted(fit)
  # Bread: (X' W X)^(-1) = summary(fit)$cov.unscaled
  bread <- summary(fit)$cov.unscaled
  # Score residuals per observation for canonical logit link: X_i * (y_i - p_i)
  u <- X * as.numeric(y - p)
  cl <- as.factor(cluster)
  G <- nlevels(cl)
  N <- nrow(X)
  K <- ncol(X)
  u_cl <- rowsum(u, cl)
  meat <- crossprod(u_cl)
  adj <- (G / (G - 1)) * ((N - 1) / (N - K))
  bread %*% (adj * meat) %*% bread
}

vif_from_glm <- function(fit) {
  v <- vcov(fit)
  if (ncol(v) <= 2) return(setNames(rep(1.0, ncol(v) - 1), colnames(v)[-1]))
  v_sub <- v[-1, -1, drop = FALSE]
  R <- cov2cor(v_sub)
  diag(solve(R))
}

calc_pr_auc <- function(y, p) {
  ord <- order(p, decreasing = TRUE)
  y_ord <- y[ord]
  tp <- cumsum(y_ord == 1)
  fp <- cumsum(y_ord == 0)
  total_pos <- sum(y == 1)
  if (total_pos == 0 || total_pos == length(y)) return(NA_real_)
  rec <- c(0, tp / total_pos)
  prec <- c(1, tp / (tp + fp))
  sum(diff(rec) * (head(prec, -1) + tail(prec, -1)) / 2)
}

clip_prob <- function(p, eps = 1e-6) pmin(pmax(p, eps), 1 - eps)

evaluate_predictions <- function(y, p, p_null, cluster = NULL, n_boot = 500) {
  p_c <- clip_prob(p)
  lp <- qlogis(p_c)
  brier <- mean((y - p_c)^2)
  brier_null <- mean((y - p_null)^2)
  bss <- 1 - (brier / brier_null)
  logloss <- -mean(y * log(p_c) + (1 - y) * log(1 - p_c))
  auc_obj <- pROC::roc(y, p_c, quiet = TRUE, direction = "<")
  roc_auc <- as.numeric(pROC::auc(auc_obj))
  delong_ci <- as.numeric(pROC::ci.auc(auc_obj, method = "delong"))
  pr_auc <- calc_pr_auc(y, p_c)

  # Calibration-in-the-large (intercept) & calibration slope
  fit_citl <- suppressWarnings(glm(y ~ 1, offset = lp, family = binomial))
  cal_int <- unname(coef(fit_citl)[1])
  if (!is.null(cluster)) {
    se_int <- sqrt(diag(cluster_vcov_logit(fit_citl, cluster)))[1]
  } else {
    se_int <- summary(fit_citl)$coefficients[1, 2]
  }

  if (sd(lp) < 1e-8) {
    cal_slope <- NA_real_
    se_slope <- NA_real_
  } else {
    fit_slope <- suppressWarnings(glm(y ~ lp, family = binomial))
    cal_slope <- unname(coef(fit_slope)[2])
    if (!is.null(cluster)) {
      se_slope <- sqrt(diag(cluster_vcov_logit(fit_slope, cluster)))[2]
    } else {
      se_slope <- summary(fit_slope)$coefficients[2, 2]
    }
  }

  # LOESS Integrated Calibration Index (ICI)
  lo <- tryCatch({
    lo_fit <- suppressWarnings(loess(y ~ p_c, span = 0.75, degree = 1))
    p_obs_sm <- predict(lo_fit, newdata = p_c)
    abs_err <- abs(p_obs_sm - p_c)
    c(ici = mean(abs_err, na.rm = TRUE), e90 = unname(quantile(abs_err, 0.90, na.rm = TRUE)))
  }, error = function(e) c(ici = NA_real_, e90 = NA_real_))

  # Cluster-bootstrap 95% CI for AUC and Brier if cluster supplied
  boot_auc_ci <- c(NA_real_, NA_real_)
  boot_brier_ci <- c(NA_real_, NA_real_)
  if (!is.null(cluster) && n_boot > 0) {
    cl_levels <- unique(cluster)
    cl_idx <- split(seq_along(y), cluster)
    b_res <- replicate(n_boot, {
      samp_cl <- sample(cl_levels, length(cl_levels), replace = TRUE)
      idx <- unlist(cl_idx[samp_cl], use.names = FALSE)
      yb <- y[idx]; pb <- p_c[idx]
      if (length(unique(yb)) < 2) return(c(NA_real_, NA_real_))
      c(as.numeric(pROC::auc(yb, pb, quiet = TRUE, direction = "<")), mean((yb - pb)^2))
    })
    boot_auc_ci <- quantile(b_res[1, ], probs = c(0.025, 0.975), na.rm = TRUE)
    boot_brier_ci <- quantile(b_res[2, ], probs = c(0.025, 0.975), na.rm = TRUE)
  }

  data.frame(
    ROC_AUC = roc_auc,
    AUC_DeLong_Lo = delong_ci[1],
    AUC_DeLong_Hi = delong_ci[3],
    AUC_ClustBoot_Lo = unname(boot_auc_ci[1]),
    AUC_ClustBoot_Hi = unname(boot_auc_ci[2]),
    PR_AUC = pr_auc,
    Brier = brier,
    Brier_ClustBoot_Lo = unname(boot_brier_ci[1]),
    Brier_ClustBoot_Hi = unname(boot_brier_ci[2]),
    BSS = bss,
    LogLoss = logloss,
    Cal_Int = cal_int,
    Cal_Int_SE = unname(se_int),
    Cal_Slope = cal_slope,
    Cal_Slope_SE = unname(se_slope),
    ICI = unname(lo["ici"]),
    E90 = unname(lo["e90"]),
    Mean_Pred = mean(p_c),
    Obs_Prev = mean(y),
    stringsAsFactors = FALSE
  )
}

# ------------------------------------------------------------------------------
# Unsupervised correlation pruning inside training fold for M5 (|r| < 0.85)
# ------------------------------------------------------------------------------
prune_collinear_unsupervised <- function(X_mat, cutoff = 0.85) {
  # Order columns deterministically by variance (on raw scale? No, keep original order
  # or prefer continuous mean / cleaner metrics first; m5_pool_cols order is deterministic)
  keep <- rep(TRUE, ncol(X_mat))
  cmat <- abs(cor(X_mat))
  diag(cmat) <- 0
  for (i in seq_len(ncol(X_mat))) {
    if (!keep[i]) next
    high_corr <- which(cmat[i, ] >= cutoff)
    high_corr <- high_corr[high_corr > i]
    if (length(high_corr) > 0) keep[high_corr] <- FALSE
  }
  colnames(X_mat)[keep]
}

# Fit & predict function for all models on a single (train_df, test_df) split
fit_predict_all_models <- function(train_df, test_df, include_exploratory = TRUE) {
  y_tr <- train_df$epid10
  n_te <- nrow(test_df)
  preds <- list()
  meta_out <- list()

  # Null model (training prevalence)
  preds$Null <- rep(mean(y_tr), n_te)

  # M0: Baseline 7-d additive T + RH (2 terms, 2 slope params)
  f_m0 <- glm(epid10 ~ T.A.PRE7.24H + RH7, data = train_df, family = binomial)
  preds$M0_Base7d <- as.numeric(predict(f_m0, newdata = test_df, type = "response"))

  # M1: 15-d additive T + RH (2 terms, 2 slope params)
  f_m1 <- glm(epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H, data = train_df, family = binomial)
  preds$M1_Add15d <- as.numeric(predict(f_m1, newdata = test_df, type = "response"))

  # M2: Two-stage hydrothermal duration + evaporative demand + pre-heading T (3 terms, 3 slope params)
  f_m2 <- glm(epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2, data = train_df, family = binomial)
  preds$M2_Hydro3 <- as.numeric(predict(f_m2, newdata = test_df, type = "response"))

  # M3: Centered 10-d T * RH interaction (3 terms, 3 slope params)
  mu_T10 <- mean(train_df$T.A.PRE10.24H)
  mu_RH10 <- mean(train_df$RH.A.PRE10.24H)
  tr_m3 <- transform(train_df, cT10 = T.A.PRE10.24H - mu_T10, cRH10 = RH.A.PRE10.24H - mu_RH10)
  te_m3 <- transform(test_df,  cT10 = T.A.PRE10.24H - mu_T10, cRH10 = RH.A.PRE10.24H - mu_RH10)
  f_m3 <- glm(epid10 ~ cT10 + cRH10 + cT10:cRH10, data = tr_m3, family = binomial)
  preds$M3_Int10d <- as.numeric(predict(f_m3, newdata = te_m3, type = "response"))

  # M4: Centered 10-d quadratic T + linear RH (3 terms, 3 slope params)
  f_m4 <- glm(epid10 ~ cT10 + I(cT10^2) + cRH10, data = tr_m3, family = binomial)
  preds$M4_Quad10d <- as.numeric(predict(f_m4, newdata = te_m3, type = "response"))

  # M5: Nested L1-screened <= 3 terms (unsupervised |r| < 0.85 pruning + LASSO top <=3 + GLM / Ridge refit)
  X_tr_raw <- as.matrix(train_df[, m5_pool_cols])
  kept_cols <- prune_collinear_unsupervised(X_tr_raw, cutoff = 0.85)
  X_tr_p <- X_tr_raw[, kept_cols, drop = FALSE]
  X_te_p <- as.matrix(test_df[, kept_cols, drop = FALSE])

  # Fit LASSO path (glmnet standardizes internally using training mean/sd)
  lasso_path <- glmnet(X_tr_p, y_tr, family = "binomial", alpha = 1, nlambda = 200)
  df_path <- lasso_path$df
  idx_le3 <- which(df_path <= 3 & df_path >= 1)
  if (length(idx_le3) > 0) {
    # Pick smallest penalty (furthest along path) that still has <= 3 active predictors
    best_step <- max(idx_le3)
    b_vec <- lasso_path$beta[, best_step]
    sel_vars <- names(b_vec)[which(b_vec != 0)]
  } else {
    sel_vars <- c("T.A.PRE15.24H", "RH.A.PRE15.24H")
  }
  meta_out$m5_selected <- sel_vars

  # M5a: Unpenalized logistic refit on the <= 3 selected predictors
  form_m5 <- as.formula(paste("epid10 ~", paste(sel_vars, collapse = " + ")))
  f_m5_glm <- glm(form_m5, data = train_df, family = binomial)
  preds$M5a_L1GLM3 <- as.numeric(predict(f_m5_glm, newdata = test_df, type = "response"))

  # M5b: L2-shrunk (ridge) logistic refit on the <= 3 selected predictors (nested grouped CV on state_year)
  if (length(sel_vars) >= 2) {
    sy_fac <- as.integer(factor(train_df$state_year))
    n_g <- max(sy_fac)
    foldid_in <- ((sy_fac - 1) %% min(5, n_g)) + 1
    X_sel_tr <- scale(as.matrix(train_df[, sel_vars, drop = FALSE]))
    X_sel_te <- scale(as.matrix(test_df[, sel_vars, drop = FALSE]),
                      center = attr(X_sel_tr, "scaled:center"),
                      scale = attr(X_sel_tr, "scaled:scale"))
    cv_ridge <- cv.glmnet(X_sel_tr, y_tr, family = "binomial", alpha = 0, foldid = foldid_in)
    preds$M5b_L1Ridge3 <- as.numeric(predict(cv_ridge, newx = X_sel_te, s = "lambda.min", type = "response"))
  } else {
    preds$M5b_L1Ridge3 <- preds$M5a_L1GLM3
  }

  # Exploratory secondary benchmarks (strictly separated from primary <=3-term models)
  if (include_exploratory) {
    sy_fac <- as.integer(factor(train_df$state_year))
    foldid_in <- ((sy_fac - 1) %% 5) + 1
    X174_tr <- as.matrix(train_df[, pre_cols_all])
    X174_te <- as.matrix(test_df[, pre_cols_all])
    cv_l174 <- cv.glmnet(X174_tr, y_tr, family = "binomial", alpha = 1, foldid = foldid_in, dfmax = 30)
    preds$E1_LASSO174_1se <- as.numeric(predict(cv_l174, newx = X174_te, s = "lambda.1se", type = "response"))
    meta_out$e1_nvars_1se <- sum(coef(cv_l174, s = "lambda.1se")[-1] != 0)

    # Smooth bivariate GAM on 15-d T and RH
    f_gam <- suppressWarnings(mgcv::gam(
      epid10 ~ s(T.A.PRE15.24H, k = 5) + s(RH.A.PRE15.24H, k = 5) + ti(T.A.PRE15.24H, RH.A.PRE15.24H, k = 4),
      data = train_df, family = binomial, method = "REML"
    ))
    preds$E2_GAM15d <- as.numeric(predict(f_gam, newdata = test_df, type = "response"))
  }

  list(preds = as.data.frame(preds), meta = meta_out)
}

# ------------------------------------------------------------------------------
# 2. Run Full-Sample Fits & Parameter / Uncertainty Diagnostics for M0-M5
# ------------------------------------------------------------------------------
cat("\n=== FULL-SAMPLE PARAMETER ESTIMATES & CLUSTER-ROBUST INFERENCE ===\n")
mu_T10_all <- mean(df$T.A.PRE10.24H)
mu_RH10_all <- mean(df$RH.A.PRE10.24H)
df_centered <- transform(df, cT10 = T.A.PRE10.24H - mu_T10_all, cRH10 = RH.A.PRE10.24H - mu_RH10_all)

# Also determine full-sample M5 selected variables
kept_all <- prune_collinear_unsupervised(as.matrix(df[, m5_pool_cols]), cutoff = 0.85)
cat("Full-sample unsupervised |r|<0.85 pruned pool size:", length(kept_all), "of", length(m5_pool_cols), "\n")
lp_all <- glmnet(as.matrix(df[, kept_all]), df$epid10, family = "binomial", alpha = 1, nlambda = 200)
step_all <- max(which(lp_all$df <= 3 & lp_all$df >= 1))
m5_vars_all <- names(lp_all$beta[, step_all])[which(lp_all$beta[, step_all] != 0)]
cat("Full-sample M5 L1-selected (<=3) predictors:", paste(m5_vars_all, collapse = ", "), "\n")

full_models <- list(
  M0_Base7d   = glm(epid10 ~ T.A.PRE7.24H + RH7, data = df_centered, family = binomial),
  M1_Add15d   = glm(epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H, data = df_centered, family = binomial),
  M2_Hydro3   = glm(epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2, data = df_centered, family = binomial),
  M3_Int10d   = glm(epid10 ~ cT10 + cRH10 + cT10:cRH10, data = df_centered, family = binomial),
  M4_Quad10d  = glm(epid10 ~ cT10 + I(cT10^2) + cRH10, data = df_centered, family = binomial),
  M5a_L1GLM3  = glm(as.formula(paste("epid10 ~", paste(m5_vars_all, collapse = " + "))), data = df_centered, family = binomial)
)

coef_rows <- list()
fit_summary_rows <- list()
for (mname in names(full_models)) {
  fm <- full_models[[mname]]
  est <- coef(fm)
  se_naive <- summary(fm)$coefficients[, 2]
  se_env <- sqrt(diag(cluster_vcov_logit(fm, df_centered$env_id)))
  se_sy  <- sqrt(diag(cluster_vcov_logit(fm, df_centered$state_year)))
  vifs <- c(Intercept = NA_real_, vif_from_glm(fm))

  z_sy <- est / se_sy
  p_sy <- 2 * pnorm(-abs(z_sy))

  coef_rows[[mname]] <- data.frame(
    Model = mname,
    Term = names(est),
    Estimate = est,
    SE_Naive = se_naive,
    SE_Clust_Env = se_env,
    SE_Clust_StateYear = se_sy,
    Z_StateYear = z_sy,
    P_StateYear = p_sy,
    CI95_SY_Lo = est - 1.96 * se_sy,
    CI95_SY_Hi = est + 1.96 * se_sy,
    VIF = vifs,
    row.names = NULL,
    stringsAsFactors = FALSE
  )

  p_in <- fitted(fm)
  fit_summary_rows[[mname]] <- data.frame(
    Model = mname,
    Slope_Params = length(est) - 1,
    Total_Params = length(est),
    AIC = AIC(fm),
    BIC = BIC(fm),
    Deviance = deviance(fm),
    Apparent_AUC = as.numeric(pROC::auc(df_centered$epid10, p_in, quiet = TRUE, direction = "<")),
    Apparent_Brier = mean((df_centered$epid10 - p_in)^2),
    Max_VIF = max(vifs, na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}
coef_table <- bind_rows(coef_rows)
fit_summary_table <- bind_rows(fit_summary_rows)
print(fit_summary_table, row.names = FALSE)
cat("\nDetailed coefficients (with naive vs env-clustered vs state:year-clustered SEs):\n")
print(coef_table %>% mutate(across(where(is.numeric), ~round(., 4))), row.names = FALSE)

# ------------------------------------------------------------------------------
# 3. Validation Scheme 1: Leave-One-Year-Out Cross-Validation (LOYO-CV, 32 years)
# ------------------------------------------------------------------------------
cat("\n=== RUNNING LEAVE-ONE-YEAR-OUT CV (32 YEARS) ===\n")
years_vec <- sort(unique(df$year))
loyo_oof_list <- vector("list", length(years_vec))
loyo_m5_sel <- character(0)
loyo_e1_nvars <- integer(0)

for (i in seq_along(years_vec)) {
  yr <- years_vec[i]
  tr <- df[df$year != yr, , drop = FALSE]
  te <- df[df$year == yr, , drop = FALSE]
  res <- fit_predict_all_models(tr, te, include_exploratory = TRUE)
  loyo_oof_list[[i]] <- cbind(te[, c("id", "year", "state", "state_year", "env_id", "epid10", "S")], res$preds)
  loyo_m5_sel <- c(loyo_m5_sel, res$meta$m5_selected)
  loyo_e1_nvars <- c(loyo_e1_nvars, res$meta$e1_nvars_1se)
}
loyo_oof <- bind_rows(loyo_oof_list) %>% arrange(id)

model_cols <- setdiff(names(loyo_oof), c("id", "year", "state", "state_year", "env_id", "epid10", "S", "Null"))
loyo_metrics <- bind_rows(lapply(model_cols, function(m) {
  cbind(Model = m, Scheme = "LOYO_32yr",
        evaluate_predictions(loyo_oof$epid10, loyo_oof[[m]], loyo_oof$Null, cluster = loyo_oof$state_year, n_boot = 500))
}))
cat("LOYO-CV Pooled Metrics:\n")
print(loyo_metrics %>% select(Model, ROC_AUC, AUC_ClustBoot_Lo, AUC_ClustBoot_Hi, PR_AUC, Brier, BSS, Cal_Int, Cal_Slope, ICI) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)
cat("M5 selection frequencies across 32 LOYO folds:\n")
print(sort(table(loyo_m5_sel), decreasing = TRUE))
cat("E1 LASSO-174 active vars (1se) median [IQR]:", median(loyo_e1_nvars),
    sprintf("[%g, %g]\n", quantile(loyo_e1_nvars, 0.25), quantile(loyo_e1_nvars, 0.75)))

# ------------------------------------------------------------------------------
# 4. Validation Scheme 2: Leave-One-State-Out Cross-Validation (LOSO-CV, 17 states)
# ------------------------------------------------------------------------------
cat("\n=== RUNNING LEAVE-ONE-STATE-OUT CV (17 STATES) ===\n")
states_vec <- sort(unique(as.character(df$state)))
loso_oof_list <- vector("list", length(states_vec))
loso_m5_sel <- character(0)

for (i in seq_along(states_vec)) {
  st <- states_vec[i]
  tr <- df[df$state != st, , drop = FALSE]
  te <- df[df$state == st, , drop = FALSE]
  res <- fit_predict_all_models(tr, te, include_exploratory = TRUE)
  loso_oof_list[[i]] <- cbind(te[, c("id", "year", "state", "state_year", "env_id", "epid10", "S")], res$preds)
  loso_m5_sel <- c(loso_m5_sel, res$meta$m5_selected)
}
loso_oof <- bind_rows(loso_oof_list) %>% arrange(id)

loso_metrics <- bind_rows(lapply(model_cols, function(m) {
  cbind(Model = m, Scheme = "LOSO_17st",
        evaluate_predictions(loso_oof$epid10, loso_oof[[m]], loso_oof$Null, cluster = loso_oof$state_year, n_boot = 500))
}))
cat("LOSO-CV Pooled Metrics:\n")
print(loso_metrics %>% select(Model, ROC_AUC, AUC_ClustBoot_Lo, AUC_ClustBoot_Hi, PR_AUC, Brier, BSS, Cal_Int, Cal_Slope, ICI, Mean_Pred, Obs_Prev) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)
cat("M5 selection frequencies across 17 LOSO folds:\n")
print(sort(table(loso_m5_sel), decreasing = TRUE))

# ------------------------------------------------------------------------------
# 5. Validation Scheme 3: 5x10-fold Grouped (state x year) Cross-Validation
# ------------------------------------------------------------------------------
cat("\n=== RUNNING 5x10-FOLD GROUPED (STATE x YEAR) CV ===\n")
sy_unique <- unique(df$state_year)
n_repeats <- 5
k_folds <- 10
grp_rep_metrics <- list()
grp_fold_metrics <- list()
grp_oof_accum <- matrix(0, nrow = nrow(df), ncol = length(model_cols) + 1)
colnames(grp_oof_accum) <- c("Null", model_cols)
grp_m5_sel <- character(0)

for (r in seq_len(n_repeats)) {
  set.seed(20261122 + r * 100)
  shuf_sy <- sample(sy_unique)
  sy_fold_map <- setNames(((seq_along(shuf_sy) - 1) %% k_folds) + 1, shuf_sy)
  fold_vec <- sy_fold_map[df$state_year]

  oof_r <- vector("list", k_folds)
  for (k in seq_len(k_folds)) {
    tr <- df[fold_vec != k, , drop = FALSE]
    te <- df[fold_vec == k, , drop = FALSE]
    res <- fit_predict_all_models(tr, te, include_exploratory = TRUE)
    oof_k <- cbind(te[, c("id", "year", "state", "state_year", "env_id", "epid10")], res$preds)
    oof_r[[k]] <- oof_k
    grp_m5_sel <- c(grp_m5_sel, res$meta$m5_selected)

    # Per-fold distribution of performance (estimable in every fold!)
    for (m in model_cols) {
      ev_k <- evaluate_predictions(oof_k$epid10, oof_k[[m]], oof_k$Null, cluster = NULL, n_boot = 0)
      grp_fold_metrics[[length(grp_fold_metrics) + 1]] <- cbind(Repeat = r, Fold = k, Model = m, ev_k)
    }
  }
  oof_r_df <- bind_rows(oof_r) %>% arrange(id)
  grp_oof_accum <- grp_oof_accum + as.matrix(oof_r_df[, c("Null", model_cols)])
}
grp_oof_avg <- as.data.frame(grp_oof_accum / n_repeats)
grp_oof_df <- cbind(df[, c("id", "year", "state", "state_year", "env_id", "epid10", "S")], grp_oof_avg)

grp_metrics <- bind_rows(lapply(model_cols, function(m) {
  cbind(Model = m, Scheme = "GroupSY_5x10",
        evaluate_predictions(grp_oof_df$epid10, grp_oof_df[[m]], grp_oof_df$Null, cluster = grp_oof_df$state_year, n_boot = 500))
}))
cat("5x10-Fold Grouped (State x Year) Pooled Metrics:\n")
print(grp_metrics %>% select(Model, ROC_AUC, AUC_ClustBoot_Lo, AUC_ClustBoot_Hi, PR_AUC, Brier, BSS, Cal_Int, Cal_Slope, ICI) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

grp_fold_df <- bind_rows(grp_fold_metrics)
cat("\nAcross-fold variability (median [IQR] across 50 grouped folds):\n")
fold_var_tab <- grp_fold_df %>%
  group_by(Model) %>%
  summarise(
    Med_AUC = round(median(ROC_AUC, na.rm = TRUE), 3),
    IQR_AUC = round(IQR(ROC_AUC, na.rm = TRUE), 3),
    Min_AUC = round(min(ROC_AUC, na.rm = TRUE), 3),
    Max_AUC = round(max(ROC_AUC, na.rm = TRUE), 3),
    Med_Brier = round(median(Brier, na.rm = TRUE), 3),
    IQR_Brier = round(IQR(Brier, na.rm = TRUE), 3),
    Med_CalSlope = round(median(Cal_Slope, na.rm = TRUE), 3),
    IQR_CalSlope = round(IQR(Cal_Slope, na.rm = TRUE), 3),
    .groups = "drop"
  )
print(as.data.frame(fold_var_tab), row.names = FALSE)

# ------------------------------------------------------------------------------
# 6. Diagnostic Check: Optimism of Naive Random Observation-Level 10-Fold CV!
# ------------------------------------------------------------------------------
cat("\n=== DIAGNOSTIC LEAKAGE CHECK: NAIVE RANDOM 10-FOLD CV VS GROUPED CV ===\n")
set.seed(20261122)
rand_fold <- sample(rep(1:10, length.out = nrow(df)))
rand_oof_list <- vector("list", 10)
for (k in 1:10) {
  tr <- df[rand_fold != k, , drop = FALSE]
  te <- df[rand_fold == k, , drop = FALSE]
  res <- fit_predict_all_models(tr, te, include_exploratory = TRUE)
  rand_oof_list[[k]] <- cbind(te[, c("id", "epid10", "state_year")], res$preds)
}
rand_oof <- bind_rows(rand_oof_list) %>% arrange(id)
rand_metrics <- bind_rows(lapply(model_cols, function(m) {
  cbind(Model = m, Scheme = "NaiveRandom_10f",
        evaluate_predictions(rand_oof$epid10, rand_oof[[m]], rand_oof$Null, cluster = NULL, n_boot = 0))
}))
print(rand_metrics %>% select(Model, ROC_AUC, Brier, BSS, Cal_Slope) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# ------------------------------------------------------------------------------
# 7. Per-Year and Per-State Validation Heterogeneity Breakdown
# ------------------------------------------------------------------------------
# Per-year breakdown on well-sampled years (n >= 20 and >=1 event and nonevent: 14 years)
yr_perf <- loyo_oof %>%
  group_by(year) %>%
  summarise(
    n = n(),
    events = sum(epid10),
    obs_prev = mean(epid10),
    M1_pred = mean(M1_Add15d),
    M2_pred = mean(M2_Hydro3),
    M3_pred = mean(M3_Int10d),
    M1_brier = mean((epid10 - M1_Add15d)^2),
    M2_brier = mean((epid10 - M2_Hydro3)^2),
    M3_brier = mean((epid10 - M3_Int10d)^2),
    M1_auc = if (n() >= 15 && sum(epid10) >= 1 && sum(epid10 == 0) >= 1) as.numeric(pROC::auc(epid10, M1_Add15d, quiet = TRUE, direction = "<")) else NA_real_,
    M2_auc = if (n() >= 15 && sum(epid10) >= 1 && sum(epid10 == 0) >= 1) as.numeric(pROC::auc(epid10, M2_Hydro3, quiet = TRUE, direction = "<")) else NA_real_,
    M3_auc = if (n() >= 15 && sum(epid10) >= 1 && sum(epid10 == 0) >= 1) as.numeric(pROC::auc(epid10, M3_Int10d, quiet = TRUE, direction = "<")) else NA_real_,
    .groups = "drop"
  )
cat("\nPer-Year LOYO performance (years with n >= 15):\n")
print(as.data.frame(yr_perf %>% filter(n >= 15) %>% mutate(across(where(is.numeric), ~round(., 3)))), row.names = FALSE)

# Per-state breakdown across all 17 states
st_perf <- loso_oof %>%
  group_by(state) %>%
  summarise(
    n = n(),
    events = sum(epid10),
    obs_prev = mean(epid10),
    M1_pred = mean(M1_Add15d),
    M2_pred = mean(M2_Hydro3),
    M3_pred = mean(M3_Int10d),
    M1_brier = mean((epid10 - M1_Add15d)^2),
    M2_brier = mean((epid10 - M2_Hydro3)^2),
    M3_brier = mean((epid10 - M3_Int10d)^2),
    M1_auc = if (sum(epid10) >= 1 && sum(epid10 == 0) >= 1) as.numeric(pROC::auc(epid10, M1_Add15d, quiet = TRUE, direction = "<")) else NA_real_,
    M2_auc = if (sum(epid10) >= 1 && sum(epid10 == 0) >= 1) as.numeric(pROC::auc(epid10, M2_Hydro3, quiet = TRUE, direction = "<")) else NA_real_,
    M3_auc = if (sum(epid10) >= 1 && sum(epid10 == 0) >= 1) as.numeric(pROC::auc(epid10, M3_Int10d, quiet = TRUE, direction = "<")) else NA_real_,
    .groups = "drop"
  ) %>%
  arrange(desc(n))
cat("\nPer-State LOSO performance (all 17 states):\n")
print(as.data.frame(st_perf %>% mutate(across(where(is.numeric), ~round(., 3)))), row.names = FALSE)

# Save all modeling & validation outputs
all_cv_metrics <- bind_rows(loyo_metrics, loso_metrics, grp_metrics, rand_metrics)
write.csv(all_cv_metrics, "output/cv_performance_summary.csv", row.names = FALSE)
write.csv(coef_table, "output/full_model_coefficients.csv", row.names = FALSE)
write.csv(fit_summary_table, "output/full_model_fit_summary.csv", row.names = FALSE)
write.csv(yr_perf, "output/loyo_by_year.csv", row.names = FALSE)
write.csv(st_perf, "output/loso_by_state.csv", row.names = FALSE)

saveRDS(list(
  df = df,
  full_models = full_models,
  coef_table = coef_table,
  fit_summary_table = fit_summary_table,
  all_cv_metrics = all_cv_metrics,
  loyo_oof = loyo_oof,
  loso_oof = loso_oof,
  grp_oof_df = grp_oof_df,
  grp_fold_df = grp_fold_df,
  fold_var_tab = fold_var_tab,
  yr_perf = yr_perf,
  st_perf = st_perf,
  loyo_m5_sel = table(loyo_m5_sel),
  loso_m5_sel = table(loso_m5_sel),
  grp_m5_sel = table(grp_m5_sel)
), "output/modeling_results.rds")
cat("\n=== 02_MODEL_FITTING_AND_VALIDATION COMPLETE ===\n")
