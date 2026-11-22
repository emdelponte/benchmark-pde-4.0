# ==============================================================================
# 04_posthoc_refinement_check.R
# Post-plan parsimony reduction diagnostics (documented in analysis_log.md):
# Testing nested 1-param reduction of M0 (M0r: RH7) and 2-param reduction of M2
# (M2r: VPD.A.1 + T.A.2) after full-sample cluster-robust inference showed
# redundant thermal/TRH terms (p = 0.61 in M0; p = 0.73 in M2).
# Also generates Figure 4b (M2r 2-stage risk surface).
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(pROC)
})

set.seed(20261122)
mod_res <- readRDS("output/modeling_results.rds")
df <- mod_res$df

# Reuse exact cluster_vcov_logit and evaluate_predictions logic
cluster_vcov_logit <- function(fit, cluster) {
  X <- model.matrix(fit)
  u <- X * as.numeric(fit$y - fitted(fit))
  bread <- summary(fit)$cov.unscaled
  cl <- as.factor(cluster)
  G <- nlevels(cl); N <- nrow(X); K <- ncol(X)
  u_cl <- rowsum(u, cl)
  adj <- (G / (G - 1)) * ((N - 1) / (N - K))
  bread %*% (adj * crossprod(u_cl)) %*% bread
}

eval_posthoc <- function(formula_str, model_label) {
  f_obj <- as.formula(formula_str)
  fm <- glm(f_obj, data = df, family = binomial)
  est <- coef(fm)
  se_naive <- summary(fm)$coefficients[, 2]
  se_env <- sqrt(diag(cluster_vcov_logit(fm, df$env_id)))
  se_sy  <- sqrt(diag(cluster_vcov_logit(fm, df$state_year)))
  z_sy <- est / se_sy
  p_sy <- 2 * pnorm(-abs(z_sy))

  v <- vcov(fm)
  vifs <- if (ncol(v) <= 2) c(NA_real_, 1.0) else c(NA_real_, diag(solve(cov2cor(v[-1, -1]))))

  cat("\n--- Full-Sample Fit:", model_label, "---\n")
  cat(sprintf("AIC = %.2f | BIC = %.2f | Deviance = %.2f | Apparent AUC = %.4f | Apparent Brier = %.4f\n",
              AIC(fm), BIC(fm), deviance(fm),
              as.numeric(pROC::auc(df$epid10, fitted(fm), quiet = TRUE, direction = "<")),
              mean((df$epid10 - fitted(fm))^2)))
  print(data.frame(
    Term = names(est), Estimate = round(est, 4), SE_Naive = round(se_naive, 4),
    SE_Env = round(se_env, 4), SE_StateYear = round(se_sy, 4),
    Z_SY = round(z_sy, 3), P_SY = round(p_sy, 4), VIF = round(vifs, 3)
  ), row.names = FALSE)

  # LOYO (32 years)
  p_loyo <- numeric(nrow(df)); pn_loyo <- numeric(nrow(df))
  for (yr in unique(df$year)) {
    idx <- which(df$year == yr)
    fit <- glm(f_obj, data = df[-idx, ], family = binomial)
    p_loyo[idx] <- predict(fit, newdata = df[idx, ], type = "response")
    pn_loyo[idx] <- mean(df$epid10[-idx])
  }

  # LOSO (17 states)
  p_loso <- numeric(nrow(df)); pn_loso <- numeric(nrow(df))
  for (st in unique(as.character(df$state))) {
    idx <- which(df$state == st)
    fit <- glm(f_obj, data = df[-idx, ], family = binomial)
    p_loso[idx] <- predict(fit, newdata = df[idx, ], type = "response")
    pn_loso[idx] <- mean(df$epid10[-idx])
  }

  # 5x10 Grouped state_year CV (exact same seeds as 02_model_fitting_and_validation.R!)
  sy_unique <- unique(df$state_year)
  p_grp_acc <- numeric(nrow(df)); pn_grp_acc <- numeric(nrow(df))
  for (r in 1:5) {
    set.seed(20261122 + r * 100)
    shuf_sy <- sample(sy_unique)
    sy_map <- setNames(((seq_along(shuf_sy) - 1) %% 10) + 1, shuf_sy)
    fvec <- sy_map[df$state_year]
    pr <- numeric(nrow(df)); pnr <- numeric(nrow(df))
    for (k in 1:10) {
      idx <- which(fvec == k)
      fit <- glm(f_obj, data = df[-idx, ], family = binomial)
      pr[idx] <- predict(fit, newdata = df[idx, ], type = "response")
      pnr[idx] <- mean(df$epid10[-idx])
    }
    p_grp_acc <- p_grp_acc + pr
    pn_grp_acc <- pn_grp_acc + pnr
  }
  p_grp <- p_grp_acc / 5; pn_grp <- pn_grp_acc / 5

  summ_one <- function(p, pn, scheme) {
    pc <- pmin(pmax(p, 1e-6), 1 - 1e-6)
    lp <- qlogis(pc)
    y <- df$epid10
    lo_fit <- loess(y ~ pc, span = 0.75, degree = 1)
    ici <- mean(abs(predict(lo_fit, newdata = pc) - pc), na.rm = TRUE)
    # Cluster bootstrap 95% CI on state_year
    cl_levels <- unique(df$state_year)
    cl_idx <- split(seq_along(y), df$state_year)
    set.seed(20261122)
    b_auc <- replicate(500, {
      idx <- unlist(cl_idx[sample(cl_levels, length(cl_levels), replace = TRUE)], use.names = FALSE)
      as.numeric(pROC::auc(y[idx], pc[idx], quiet = TRUE, direction = "<"))
    })
    data.frame(
      Model = model_label, Scheme = scheme,
      ROC_AUC = round(as.numeric(pROC::auc(y, pc, quiet = TRUE, direction = "<")), 3),
      AUC_Lo = round(quantile(b_auc, 0.025), 3),
      AUC_Hi = round(quantile(b_auc, 0.975), 3),
      Brier = round(mean((y - pc)^2), 3),
      BSS = round(1 - mean((y - pc)^2) / mean((y - pn)^2), 3),
      Cal_Int = round(unname(coef(glm(y ~ 1, offset = lp, family = binomial))[1]), 3),
      Cal_Slope = round(unname(coef(glm(y ~ lp, family = binomial))[2]), 3),
      ICI = round(ici, 3),
      stringsAsFactors = FALSE
    )
  }

  res_cv <- bind_rows(
    summ_one(p_loyo, pn_loyo, "LOYO_32yr"),
    summ_one(p_loso, pn_loso, "LOSO_17st"),
    summ_one(p_grp,  pn_grp,  "GroupSY_5x10")
  )
  print(res_cv, row.names = FALSE)
  list(fit = fm, cv = res_cv, p_loyo = p_loyo, p_loso = p_loso)
}

r_m0r <- eval_posthoc("epid10 ~ RH7", "M0r_RH7_1p")
r_m2r <- eval_posthoc("epid10 ~ VPD.A.1 + T.A.2", "M2r_VPD10_T20_2p")

# Likelihood-ratio & Wald comparison of M2 (3p) vs M2r (2p) and M0 (2p) vs M0r (1p)
cat("\nLRT M0 (T.A.PRE7 + RH7) vs M0r (RH7 only): p =",
    round(anova(r_m0r$fit, mod_res$full_models$M0_Base7d, test = "Chisq")$`Pr(>Chi)`[2], 4), "\n")
cat("LRT M2 (TRH15 + VPD10 + T20_10) vs M2r (VPD10 + T20_10): p =",
    round(anova(r_m2r$fit, mod_res$full_models$M2_Hydro3, test = "Chisq")$`Pr(>Chi)`[2], 4), "\n")

write.csv(bind_rows(r_m0r$cv, r_m2r$cv), "output/posthoc_parsimony_reductions.csv", row.names = FALSE)

# Update Figure 4 to show the selected final parsimonious 2-stage model M2r (VPD.A.1 vs T.A.2)
grid_m2r <- expand.grid(
  T.A.2 = seq(9.7, 24.5, length.out = 120),
  VPD.A.1 = seq(0.26, 1.63, length.out = 120)
)
grid_m2r$prob <- predict(r_m2r$fit, newdata = grid_m2r, type = "response")

p_m2r <- ggplot() +
  geom_raster(data = grid_m2r, aes(x = T.A.2, y = VPD.A.1, fill = prob), alpha = 0.88) +
  geom_contour(data = grid_m2r, aes(x = T.A.2, y = VPD.A.1, z = prob),
               breaks = c(0.10, 0.20, 0.30, 0.45, 0.60), color = "white", linewidth = 0.5) +
  geom_point(data = df, aes(x = T.A.2, y = VPD.A.1, shape = factor(epid10)),
             alpha = 0.55, size = 1.6, color = "black") +
  scale_y_reverse() +
  scale_fill_viridis_c(option = "plasma", name = "Predicted\nP(S >= 10%)", limits = c(0, 0.80)) +
  scale_shape_manual(values = c("0" = 1, "1" = 16),
                     labels = c("Nonevent (S < 10%)", "Epidemic (S >= 10%)"),
                     name = "Observed Outcome") +
  labs(
    title = "Final Parsimonious 2-Term Model (M2r): Two-Stage Pre-Anthesis Risk Surface",
    subtitle = "Warm pre-heading T (20-10 d pre) + humid/low-VPD pre-anthesis air (10-0 d pre); y-axis reversed (wetter upward)",
    x = "Pre-Heading Mean Daily Temperature, 20 to 10 d Pre-Anthesis (T.A.2, °C)",
    y = "Pre-Anthesis Mean Vapor Pressure Deficit, 10 to 0 d Pre-Anthesis (VPD.A.1, kPa)"
  ) +
  theme_bw(base_size = 11) +
  theme(panel.grid.minor = element_blank(), legend.position = "right")

ggsave("output/figures/fig5_final_m2r_risk_surface.png", p_m2r, width = 9.0, height = 5.8, dpi = 300)
cat("\n=== 04_POSTHOC_REFINEMENT_CHECK COMPLETE ===\n")
