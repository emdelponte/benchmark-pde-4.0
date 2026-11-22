# ==============================================================================
# 03_sensitivity_and_figures.R
# Pre-specified sensitivity analyses (S1-S5), influential cluster diagnostics,
# and publication-quality diagnostic & calibration plots
# ==============================================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
  library(pROC)
})

set.seed(20261122)
dir.create("output/figures", recursive = TRUE, showWarnings = FALSE)

mod_res <- readRDS("output/modeling_results.rds")
df <- mod_res$df

# Helper for fast LOYO + LOSO evaluation of any GLM formula on arbitrary dataset/outcome
eval_glm_loyo_loso <- function(data_in, formula_str, y_col = "epid10") {
  f_obj <- as.formula(formula_str)
  yrs <- unique(data_in$year)
  sts <- unique(as.character(data_in$state))

  # LOYO
  p_loyo <- numeric(nrow(data_in))
  p_null_loyo <- numeric(nrow(data_in))
  for (yr in yrs) {
    idx_te <- which(data_in$year == yr)
    tr <- data_in[-idx_te, , drop = FALSE]
    te <- data_in[idx_te, , drop = FALSE]
    fit <- suppressWarnings(glm(f_obj, data = tr, family = binomial))
    p_loyo[idx_te] <- as.numeric(predict(fit, newdata = te, type = "response"))
    p_null_loyo[idx_te] <- mean(tr[[y_col]])
  }

  # LOSO
  p_loso <- numeric(nrow(data_in))
  p_null_loso <- numeric(nrow(data_in))
  for (st in sts) {
    idx_te <- which(data_in$state == st)
    tr <- data_in[-idx_te, , drop = FALSE]
    te <- data_in[idx_te, , drop = FALSE]
    fit <- suppressWarnings(glm(f_obj, data = tr, family = binomial))
    p_loso[idx_te] <- as.numeric(predict(fit, newdata = te, type = "response"))
    p_null_loso[idx_te] <- mean(tr[[y_col]])
  }

  y <- data_in[[y_col]]
  p_loyo <- pmin(pmax(p_loyo, 1e-6), 1 - 1e-6)
  p_loso <- pmin(pmax(p_loso, 1e-6), 1 - 1e-6)

  cal_loyo <- coef(suppressWarnings(glm(y ~ qlogis(p_loyo), family = binomial)))[2]
  cal_loso <- coef(suppressWarnings(glm(y ~ qlogis(p_loso), family = binomial)))[2]
  citl_loyo <- coef(suppressWarnings(glm(y ~ 1, offset = qlogis(p_loyo), family = binomial)))[1]
  citl_loso <- coef(suppressWarnings(glm(y ~ 1, offset = qlogis(p_loso), family = binomial)))[1]

  data.frame(
    Formula = formula_str,
    Outcome = y_col,
    N = nrow(data_in),
    Events = sum(y),
    LOYO_AUC = as.numeric(pROC::auc(y, p_loyo, quiet = TRUE, direction = "<")),
    LOYO_Brier = mean((y - p_loyo)^2),
    LOYO_BSS = 1 - mean((y - p_loyo)^2) / mean((y - p_null_loyo)^2),
    LOYO_CalInt = unname(citl_loyo),
    LOYO_CalSlope = unname(cal_loyo),
    LOSO_AUC = as.numeric(pROC::auc(y, p_loso, quiet = TRUE, direction = "<")),
    LOSO_Brier = mean((y - p_loso)^2),
    LOSO_BSS = 1 - mean((y - p_loso)^2) / mean((y - p_null_loso)^2),
    LOSO_CalInt = unname(citl_loso),
    LOSO_CalSlope = unname(cal_loso),
    stringsAsFactors = FALSE
  )
}

# ------------------------------------------------------------------------------
# S1. Exposure Window Sensitivity ([-5,0] through [-30,0] for T+RH and TRH)
# ------------------------------------------------------------------------------
cat("=== S1: EXPOSURE WINDOW SENSITIVITY ===\n")
win_specs <- list(
  "PRE5 [-5,0] (24h T+RH)"   = "epid10 ~ T.A.PRE5.24H + RH.A.PRE5.24H",
  "PRE7 [-7,0] (24h T+RH)"   = "epid10 ~ T.A.PRE7.24H + RH7",
  "PRE10 [-10,0] (24h T+RH)" = "epid10 ~ T.A.PRE10.24H + RH.A.PRE10.24H",
  "PRE14 [-14,0] (24h T+RH)" = "epid10 ~ T.A.PRE14.24H + RH.A.PRE14.24H",
  "PRE15 [-15,0] (24h T+RH)" = "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H",
  "PRE5 [-5,0] (TRH80)"      = "epid10 ~ TRH.15T30nRHG80.PRE5.24H",
  "PRE7 [-7,0] (TRH80)"      = "epid10 ~ TRH807",
  "PRE10 [-10,0] (TRH80)"    = "epid10 ~ TRH.15T30nRHG80.PRE10.24H",
  "PRE14 [-14,0] (TRH80)"    = "epid10 ~ TRH.15T30nRHG80.PRE14.24H",
  "PRE15 [-15,0] (TRH80)"    = "epid10 ~ TRH.15T30nRHG80.PRE15.24H",
  "PRE30 [-30,0] (TRH80)"    = "epid10 ~ TRH.15T30nRHG80.CHD.1"
)
s1_tab <- bind_rows(lapply(names(win_specs), function(nm) {
  cbind(Window_Spec = nm, eval_glm_loyo_loso(df, win_specs[[nm]], "epid10"))
}))
print(s1_tab %>% select(Window_Spec, LOYO_AUC, LOYO_Brier, LOYO_BSS, LOYO_CalSlope, LOSO_AUC, LOSO_Brier, LOSO_BSS, LOSO_CalSlope) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# ------------------------------------------------------------------------------
# S2. Outcome Threshold Sensitivity (S >= 5%, S > 10%, S >= 15%)
# ------------------------------------------------------------------------------
cat("\n=== S2: EPIDEMIC THRESHOLD SENSITIVITY ===\n")
df$epid05 <- as.integer(df$S >= 5)
df$epid10_strict <- as.integer(df$S > 10)
df$epid15 <- as.integer(df$S >= 15)

s2_rows <- list()
for (yc in c("epid05", "epid10", "epid10_strict", "epid15")) {
  s2_rows[[paste0(yc, "_M1")]] <- cbind(Model = "M1_Add15d",
    eval_glm_loyo_loso(df, paste(yc, "~ T.A.PRE15.24H + RH.A.PRE15.24H"), yc))
  s2_rows[[paste0(yc, "_M2")]] <- cbind(Model = "M2_Hydro3",
    eval_glm_loyo_loso(df, paste(yc, "~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2"), yc))
  s2_rows[[paste0(yc, "_M3")]] <- cbind(Model = "M3_Int10d",
    eval_glm_loyo_loso(df, paste(yc, "~ T.A.PRE10.24H * RH.A.PRE10.24H"), yc))
}
s2_tab <- bind_rows(s2_rows)
print(s2_tab %>% select(Outcome, Events, Model, LOYO_AUC, LOYO_Brier, LOYO_BSS, LOSO_AUC, LOSO_Brier, LOSO_BSS) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# ------------------------------------------------------------------------------
# S3. UTC 12H ("Overnight") Artifact Check & Strict Lead-Time (<= -5 d) Check
# ------------------------------------------------------------------------------
cat("\n=== S3: UTC 12H VS 24H & STRICT LEAD-TIME (<= -5 d) SENSITIVITY ===\n")
s3_specs <- list(
  "24h PRE10 (T + RH)"            = "epid10 ~ T.A.PRE10.24H + RH.A.PRE10.24H",
  "12h UTC PRE10 (T_24h + RH_12h)"= "epid10 ~ T.A.PRE10.24H + RH.A.PRE10.12H",
  "24h PRE15 (TRH80)"             = "epid10 ~ TRH.15T30nRHG80.PRE15.24H",
  "12h UTC PRE15 (TRH80_12h)"     = "epid10 ~ TRH.15T30nRHG80.PRE15.12H",
  "Lead-time <= -5d (VPD_L635[-15,-5] + T[-20,-10])" = "epid10 ~ VPD.L635.CHD.1 + T.A.2",
  "Lead-time <= -10d (T[-20,-10] + RH_G70[-40,-10])" = "epid10 ~ T.A.2 + RH.G70.CD.1",
  "Ultra-early P proxy (P.A.3 [-60,-50] + P.A.4 [-80,-70])" = "epid10 ~ P.A.3 + P.A.4",
  "M2 Parsimonious Reduction (VPD.A.1 [-10,0] + T.A.2 [-20,-10], 2p)" = "epid10 ~ VPD.A.1 + T.A.2",
  "Post-anthesis [0,+10d] Upper Bound (T.A.4 + RH.A.2)" = "epid10 ~ T.A.4 + RH.A.2",
  "Pre + Post Combined [T15d+RH15d + Post_TRH9010]" = "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H + TRH.15T30nRHG90.CHD.3"
)
s3_tab <- bind_rows(lapply(names(s3_specs), function(nm) {
  cbind(Check = nm, eval_glm_loyo_loso(df, s3_specs[[nm]], "epid10"))
}))
print(s3_tab %>% select(Check, LOYO_AUC, LOYO_Brier, LOYO_BSS, LOSO_AUC, LOSO_Brier, LOSO_BSS) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# ------------------------------------------------------------------------------
# S4. Environment-Deduplicated (N = 545) & Agronomic-Adjusted Sensitivity
# ------------------------------------------------------------------------------
cat("\n=== S4: ENVIRONMENT-DEDUPLICATED (N=545) & AGRONOMIC SENSITIVITY ===\n")
env_df <- df %>%
  group_by(env_id, year, state) %>%
  summarise(
    n_plots = n(),
    events = sum(epid10),
    any_epid10 = as.integer(any(epid10 == 1)),
    prop_epid10 = mean(epid10),
    T.A.PRE15.24H = first(T.A.PRE15.24H),
    RH.A.PRE15.24H = first(RH.A.PRE15.24H),
    TRH.15T30nRHG80.PRE15.24H = first(TRH.15T30nRHG80.PRE15.24H),
    VPD.A.1 = first(VPD.A.1),
    T.A.2 = first(T.A.2),
    T.A.PRE10.24H = first(T.A.PRE10.24H),
    RH.A.PRE10.24H = first(RH.A.PRE10.24H),
    .groups = "drop"
  )

# Fit unweighted binomial GLM (equal weight per environment: k/n with weights = 1 or any_epid10)
fit_env_binom <- glm(cbind(events, n_plots - events) ~ T.A.PRE15.24H + RH.A.PRE15.24H,
                     data = env_df, family = binomial)
fit_env_unwt  <- suppressWarnings(glm(prop_epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H,
                     data = env_df, family = quasibinomial))
cat("M1 (T.A.PRE15 + RH.A.PRE15) plot-weighted vs equal-environment-weighted coefficients:\n")
print(round(rbind(
  Plot_Weighted_GLM = coef(fit_env_binom),
  Equal_Env_Quasibinom = coef(fit_env_unwt)
), 4))

# Evaluate equal-environment-weighted any_epid10 on N=545 unique environments
s4_env_any <- bind_rows(
  cbind(Model = "Env545_M1_Add15d", eval_glm_loyo_loso(env_df, "any_epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H", "any_epid10")),
  cbind(Model = "Env545_M2_Hydro3", eval_glm_loyo_loso(env_df, "any_epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2", "any_epid10")),
  cbind(Model = "Env545_M3_Int10d", eval_glm_loyo_loso(env_df, "any_epid10 ~ T.A.PRE10.24H * RH.A.PRE10.24H", "any_epid10"))
)
print(s4_env_any %>% select(Model, N, Events, LOYO_AUC, LOYO_Brier, LOYO_BSS, LOSO_AUC, LOSO_Brier, LOSO_BSS) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# Agronomic sensitivity (strictly secondary, on N = 995 complete-corn rows)
df_cc <- df %>% filter(!is.na(corn))
s4_agro <- bind_rows(
  cbind(Spec = "Weather_Only (M1, N=995)", eval_glm_loyo_loso(df_cc, "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H", "epid10")),
  cbind(Spec = "Agronomic_Only (resist + corn)", eval_glm_loyo_loso(df_cc, "epid10 ~ resist + corn", "epid10")),
  cbind(Spec = "M1_Weather + resist", eval_glm_loyo_loso(df_cc, "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H + resist", "epid10")),
  cbind(Spec = "M1_Weather + resist + corn", eval_glm_loyo_loso(df_cc, "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H + resist + corn", "epid10")),
  cbind(Spec = "M2_Weather + resist + corn", eval_glm_loyo_loso(df_cc, "epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2 + resist + corn", "epid10")),
  cbind(Spec = "M1_Weather + type (spring/winter)", eval_glm_loyo_loso(df_cc, "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H + type", "epid10"))
)
cat("\nAgronomic covariate sensitivity (N = 995 complete cases):\n")
print(s4_agro %>% select(Spec, LOYO_AUC, LOYO_Brier, LOYO_BSS, LOSO_AUC, LOSO_Brier, LOSO_BSS) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# ------------------------------------------------------------------------------
# S5. Influential Cluster / Subpopulation Diagnostics (Leave-Out ND, Winter vs Spring)
# ------------------------------------------------------------------------------
cat("\n=== S5: SUBPOPULATION & INFLUENTIAL ENVIRONMENT DIAGNOSTICS ===\n")
df_winter <- df %>% filter(type == "winter")
df_spring <- df %>% filter(type == "spring")
df_no_nd  <- df %>% filter(state != "ND")
df_post2000 <- df %>% filter(year >= 2001)

s5_sub <- bind_rows(
  cbind(Subset = "Winter wheat only (n=734, 16 st)", eval_glm_loyo_loso(df_winter, "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H", "epid10")),
  cbind(Subset = "Winter wheat M2 (n=734, 16 st)", eval_glm_loyo_loso(df_winter, "epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2", "epid10")),
  cbind(Subset = "Spring wheat only (n=265, 3 st)", eval_glm_loyo_loso(df_spring, "epid10 ~ T.A.PRE15.24H + RH.A.PRE15.24H", "epid10")),
  cbind(Subset = "Spring wheat M2 (n=265, 3 st)", eval_glm_loyo_loso(df_spring, "epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2", "epid10")),
  cbind(Subset = "Excluding ND (n=734, 16 st)", eval_glm_loyo_loso(df_no_nd, "epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2", "epid10")),
  cbind(Subset = "Modern era 2001-2015 (n=922)", eval_glm_loyo_loso(df_post2000, "epid10 ~ TRH.15T30nRHG80.PRE15.24H + VPD.A.1 + T.A.2", "epid10"))
)
print(s5_sub %>% select(Subset, N, Events, LOYO_AUC, LOYO_Brier, LOYO_BSS, LOSO_AUC, LOSO_Brier, LOSO_BSS) %>%
        mutate(across(where(is.numeric), ~round(., 3))), row.names = FALSE)

# Check cluster-level Cook's distance on state_year for M1, M2, M3
cat("\nTop 5 influential state-year clusters (leave-one-state-year-out max |delta beta / SE|):\n")
for (m_nm in c("M1_Add15d", "M2_Hydro3")) {
  fm <- mod_res$full_models[[m_nm]]
  b_full <- coef(fm)[-1]
  se_full <- sqrt(diag(vcov(fm)))[-1]
  sy_list <- unique(df$state_year)
  max_dfb <- sapply(sy_list, function(sy) {
    f_sub <- glm(formula(fm), data = df[df$state_year != sy, ], family = binomial)
    max(abs((b_full - coef(f_sub)[-1]) / se_full))
  })
  top5 <- head(sort(max_dfb, decreasing = TRUE), 5)
  cat(m_nm, "top state-year DFBETAs:", paste(sprintf("%s (%.2f)", names(top5), top5), collapse = ", "), "\n")
}

# Save sensitivity tables
write.csv(s1_tab, "output/sens_s1_windows.csv", row.names = FALSE)
write.csv(s2_tab, "output/sens_s2_thresholds.csv", row.names = FALSE)
write.csv(s3_tab, "output/sens_s3_utc_leadtime_post.csv", row.names = FALSE)
write.csv(s4_agro, "output/sens_s4_agronomic.csv", row.names = FALSE)
write.csv(s5_sub, "output/sens_s5_subpopulations.csv", row.names = FALSE)

# ==============================================================================
# GENERATE PUBLICATION-QUALITY DIAGNOSTIC FIGURES
# ==============================================================================
theme_epi <- theme_bw(base_size = 11) +
  theme(panel.grid.minor = element_blank(),
        strip.background = element_rect(fill = "#f0f4f8", color = "grey70"),
        strip.text = element_text(face = "bold"))

# Figure 1: Calibration curves across LOYO-CV and LOSO-CV for key models (M0, M1, M2, M3, M5a)
cal_models <- c("M0_Base7d", "M1_Add15d", "M2_Hydro3", "M3_Int10d", "M5a_L1GLM3")
cal_labels <- c(
  M0_Base7d   = "M0: 7-d T + RH (2p)",
  M1_Add15d   = "M1: 15-d T + RH (2p)",
  M2_Hydro3   = "M2: 15-d TRH80 + VPD10 + T20_10 (3p)",
  M3_Int10d   = "M3: 10-d T x RH Interaction (3p)",
  M5a_L1GLM3  = "M5a: Nested L1-GLM (<=3p)"
)

build_cal_bins <- function(oof_df, scheme_label) {
  bind_rows(lapply(cal_models, function(m) {
    p <- oof_df[[m]]
    y <- oof_df$epid10
    grp <- ntile(p, 8)
    data.frame(y = y, p = p, grp = grp) %>%
      group_by(grp) %>%
      summarise(
        mean_pred = mean(p),
        obs_rate = mean(y),
        se_obs = sqrt(mean(y) * (1 - mean(y)) / n()),
        n = n(),
        .groups = "drop"
      ) %>%
      mutate(Model = cal_labels[m], Scheme = scheme_label)
  }))
}
cal_df <- bind_rows(
  build_cal_bins(mod_res$loyo_oof, "Leave-One-Year-Out CV (32 Years)"),
  build_cal_bins(mod_res$loso_oof, "Leave-One-State-Out CV (17 States)")
)

p_cal <- ggplot(cal_df, aes(x = mean_pred, y = obs_rate, color = Model)) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "grey40") +
  geom_line(linewidth = 0.8, alpha = 0.85) +
  geom_point(size = 2.2) +
  facet_wrap(~ Scheme) +
  coord_equal(xlim = c(0, 0.8), ylim = c(0, 0.8)) +
  labs(
    title = "Out-of-Sample Calibration Across Temporal (LOYO) and Spatial (LOSO) Validation",
    subtitle = "Octile-binned observed epidemic frequency (S >= 10%) vs. mean predicted probability (N = 999 plots)",
    x = "Mean Out-of-Fold Predicted Epidemic Probability",
    y = "Observed Epidemic Proportion (S >= 10%)",
    color = "Logistic Specification"
  ) +
  theme_epi +
  theme(legend.position = "bottom", legend.direction = "vertical")
ggsave("output/figures/fig1_calibration_curves.png", p_cal, width = 9.5, height = 6.2, dpi = 300)

# Figure 2: Exposure Window Sensitivity Profile (LOYO vs LOSO AUC and Brier Skill Score)
s1_plot_df <- s1_tab %>%
  mutate(
    Family = ifelse(grepl("T\\+RH", Window_Spec), "Additive Mean T + Mean RH (2 params)", "Joint Hours 15<=T<=30 & RH>=80 (1 param)"),
    Window_Days = as.integer(sub(".*\\[-([0-9]+),0\\].*", "\\1", Window_Spec))
  ) %>%
  select(Family, Window_Days, LOYO_AUC, LOSO_AUC, LOYO_BSS, LOSO_BSS) %>%
  pivot_longer(cols = c(LOYO_AUC, LOSO_AUC, LOYO_BSS, LOSO_BSS),
               names_to = c("Scheme", "Metric"), names_sep = "_", values_to = "Value") %>%
  mutate(
    Metric = ifelse(Metric == "AUC", "ROC AUC", "Brier Skill Score (BSS)"),
    Scheme = ifelse(Scheme == "LOYO", "Leave-One-Year-Out (Temporal)", "Leave-One-State-Out (Spatial)")
  )

p_win <- ggplot(s1_plot_df, aes(x = Window_Days, y = Value, color = Family, shape = Scheme, linetype = Scheme)) +
  geom_line(linewidth = 0.9) +
  geom_point(size = 2.8) +
  facet_wrap(~ Metric, scales = "free_y") +
  scale_x_continuous(breaks = c(5, 7, 10, 14, 15, 30)) +
  labs(
    title = "Sensitivity of Pre-Anthesis Predictive Skill to Exposure Window Length",
    subtitle = "Evaluated across closed windows [-d, 0] ending at anthesis (N = 999 plots)",
    x = "Pre-Anthesis Window Start Offset (days prior to anthesis)",
    y = "Out-of-Sample Metric Value",
    color = "Predictor Formulation",
    shape = "Validation Design",
    linetype = "Validation Design"
  ) +
  theme_epi +
  theme(legend.position = "bottom", legend.box = "vertical")
ggsave("output/figures/fig2_window_sensitivity.png", p_win, width = 9.5, height = 5.8, dpi = 300)

# Figure 3: Environmental Heterogeneity — State-by-State (LOSO) and Year-by-Year (LOYO) Observed vs Predicted
st_long <- mod_res$st_perf %>%
  mutate(state = reorder(state, obs_prev))
p_st <- ggplot(st_long, aes(y = state)) +
  geom_segment(aes(x = obs_prev, xend = M2_pred, yend = state), color = "grey55", linewidth = 0.7) +
  geom_point(aes(x = obs_prev, color = "Observed Epidemic Rate"), size = 3) +
  geom_point(aes(x = M2_pred, color = "LOSO Predicted Risk (M2)"), size = 3, shape = 17) +
  scale_color_manual(values = c("Observed Epidemic Rate" = "#1b4965", "LOSO Predicted Risk (M2)" = "#d95f02")) +
  labs(
    title = "Spatial Transportability: Leave-One-State-Out Predicted vs. Observed Epidemic Prevalence",
    subtitle = "Each state predicted strictly out-of-sample from the other 16 states (4 states have 0 observed epidemics)",
    x = "Proportion of Plots with FHB Index S >= 10%",
    y = "U.S. State (ordered by observed prevalence)",
    color = NULL
  ) +
  theme_epi +
  theme(legend.position = "bottom")
ggsave("output/figures/fig3_loso_state_transportability.png", p_st, width = 8.5, height = 5.8, dpi = 300)

# Figure 4: Predicted Pre-Anthesis Risk Surface (15-d T vs RH vs Joint Hydrothermal Contour)
grid_df <- expand.grid(
  T.A.PRE15.24H = seq(11.5, 25.5, length.out = 100),
  RH.A.PRE15.24H = seq(45, 86, length.out = 100)
)
grid_df$prob_M1 <- predict(mod_res$full_models$M1_Add15d, newdata = grid_df, type = "response")

p_surf <- ggplot() +
  geom_raster(data = grid_df, aes(x = T.A.PRE15.24H, y = RH.A.PRE15.24H, fill = prob_M1), alpha = 0.85) +
  geom_contour(data = grid_df, aes(x = T.A.PRE15.24H, y = RH.A.PRE15.24H, z = prob_M1),
               breaks = c(0.1, 0.2, 0.3, 0.5, 0.7), color = "white", linewidth = 0.45) +
  geom_point(data = df, aes(x = T.A.PRE15.24H, y = RH.A.PRE15.24H, shape = factor(epid10)),
             alpha = 0.55, size = 1.6, color = "black") +
  scale_fill_viridis_c(option = "plasma", name = "Predicted\nP(S >= 10%)", limits = c(0, 0.85)) +
  scale_shape_manual(values = c("0" = 1, "1" = 16), labels = c("Nonevent (S < 10%)", "Epidemic (S >= 10%)"), name = "Observed Outcome") +
  labs(
    title = "Estimated Pre-Anthesis FHB Epidemic Risk Surface (15-d Mean T and Mean RH, Model M1)",
    subtitle = "White contours = predicted risk isoclines (0.10, 0.20, 0.30, 0.50, 0.70); points = 999 field plots",
    x = "15-d Pre-Anthesis Mean Daily Air Temperature (°C)",
    y = "15-d Pre-Anthesis Mean Daily Relative Humidity (%)"
  ) +
  theme_epi +
  theme(legend.position = "right")
ggsave("output/figures/fig4_risk_surface_15d.png", p_surf, width = 8.8, height = 5.8, dpi = 300)

cat("\n=== 03_SENSITIVITY_AND_FIGURES COMPLETE ===\n")
