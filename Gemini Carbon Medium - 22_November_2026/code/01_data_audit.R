# ==============================================================================
# 01_data_audit.R
# Comprehensive schema cross-check, metadata verification, and exploratory audit
# of Zenodo record 23189372 (FHBVer2 Version 2.1.0)
# ==============================================================================

suppressPackageStartupMessages({
  library(yaml)
  library(dplyr)
  library(tidyr)
  library(lme4)
})

`%||%` <- function(a, b) if (!is.null(a)) a else b

cat("=== 1. LOADING PRIMARY PARQUET & SUPPLEMENTARY FILES ===\n")
if (requireNamespace("nanoparquet", quietly = TRUE)) {
  df_pq <- as.data.frame(nanoparquet::read_parquet("data/FHBVer2.parquet"))
  cat("Loaded FHBVer2.parquet via nanoparquet:", nrow(df_pq), "rows x", ncol(df_pq), "cols\n")
} else if (requireNamespace("arrow", quietly = TRUE)) {
  df_pq <- as.data.frame(arrow::read_parquet("data/FHBVer2.parquet"))
  cat("Loaded FHBVer2.parquet via arrow:", nrow(df_pq), "rows x", ncol(df_pq), "cols\n")
} else {
  stop("Neither nanoparquet nor arrow is available to read FHBVer2.parquet")
}

df_rds <- readRDS("data/FHBVer2.rds")
df_csv <- read.csv("data/FHBVer2.csv", stringsAsFactors = FALSE)
meta_csv <- read.csv("data/VariablesMetaData.csv", stringsAsFactors = FALSE)
meta_rds <- readRDS("data/VariablesMetaData.rds")
dict_yaml <- yaml::read_yaml("data/FHBVer2DataDict.yaml")

cat("FHBVer2.parquet dims:", nrow(df_pq), "x", ncol(df_pq), "\n")
cat("FHBVer2.rds dims:    ", nrow(df_rds), "x", ncol(df_rds), "\n")
cat("FHBVer2.csv dims:    ", nrow(df_csv), "x", ncol(df_csv), "\n")
cat("VariablesMetaData.csv dims:", nrow(meta_csv), "x", ncol(meta_csv), "\n")
cat("YAML columns count:  ", length(dict_yaml$tables[[1]]$columns), "\n")

cat("\n=== 2. SCHEMA CROSS-CHECK & METADATA INCONSISTENCIES ===\n")
cat("Columns in RDS/CSV but MISSING from Parquet & YAML:",
    paste(setdiff(names(df_rds), names(df_pq)), collapse = ", "), "\n")
cat("Columns in Parquet but missing from RDS/CSV:",
    paste(setdiff(names(df_pq), names(df_rds)), collapse = ", "), "\n")

yaml_cols <- lapply(dict_yaml$tables[[1]]$columns, function(x) {
  data.frame(
    name = x$name %||% NA_character_,
    yaml_type = x$type %||% NA_character_,
    category = x$category %||% NA_character_,
    unit = x$unit %||% NA_character_,
    condition = x$condition %||% NA_character_,
    missing_pct = x$missing_pct %||% NA_real_,
    yaml_metric = x$metric %||% NA_character_,
    yaml_time_step = x$time_step %||% NA_character_,
    analysis_period = x$analysis_period %||% NA_character_,
    window_start_day = x$window_start_day %||% NA_integer_,
    window_end_day = x$window_end_day %||% NA_integer_,
    valid_min = if (!is.null(x$valid_range)) x$valid_range$min else NA_real_,
    valid_max = if (!is.null(x$valid_range)) x$valid_range$max else NA_real_,
    range_min = if (!is.null(x$range)) as.character(x$range$min) else NA_character_,
    range_max = if (!is.null(x$range)) as.character(x$range$max) else NA_character_,
    canonical = if (!is.null(x$canonical)) x$canonical else NA,
    deprecated = if (!is.null(x$deprecated)) x$deprecated else FALSE,
    identical_to = x$identical_to %||% NA_character_,
    description = x$description %||% NA_character_,
    stringsAsFactors = FALSE
  )
})
yaml_df <- bind_rows(yaml_cols)

cat("Exact column order match (Parquet vs YAML):", identical(names(df_pq), yaml_df$name), "\n")
weather_cols_pq <- yaml_df$name[yaml_df$category == "weather_derived"]
cat("Exact weather column match (Parquet vs VariablesMetaData.csv):",
    identical(weather_cols_pq, meta_csv$variable_name), "\n")
cat("VariablesMetaData.csv vs VariablesMetaData.rds identical values:",
    all(mapply(function(a, b) all(as.character(a) == as.character(b)), meta_csv, meta_rds)), "\n")

# Check physical/R types in Parquet vs YAML
pq_classes <- sapply(df_pq, function(x) paste(class(x), collapse = "/"))
type_comp <- data.frame(
  name = names(df_pq),
  pq_class = pq_classes,
  yaml_type = yaml_df$yaml_type,
  stringsAsFactors = FALSE
) %>%
  mutate(match = (pq_class == yaml_type) |
           (pq_class == "POSIXct/POSIXt" & yaml_type == "POSIXct"))
cat("Any Parquet class vs YAML type mismatch?:", sum(!type_comp$match), "\n")
if (sum(!type_comp$match) > 0) print(type_comp[!type_comp$match, ])

# Check factor level ordering in Parquet vs YAML
for (fcol in c("state", "type", "resist")) {
  yaml_levs <- dict_yaml$tables[[1]]$columns[[which(yaml_df$name == fcol)]]$levels
  pq_levs <- levels(df_pq[[fcol]])
  cat(sprintf("Factor %-6s | levels identical (PQ vs YAML): %-5s | levels: %s\n",
              fcol, identical(pq_levs, yaml_levs), paste(pq_levs, collapse = ", ")))
}

# Cross-check YAML weather metadata vs VariablesMetaData.csv
w_check <- yaml_df %>%
  filter(category == "weather_derived") %>%
  left_join(meta_csv, by = c("name" = "variable_name")) %>%
  mutate(
    csv_signed_start = ifelse(win_start_period == "pre", -win_start_day, win_start_day),
    csv_signed_end = ifelse(win_end_period == "pre", -win_end_day, win_end_day),
    closed_n_days = window_end_day - window_start_day + 1,
    emp_min = sapply(name, function(v) min(df_pq[[v]], na.rm = TRUE)),
    emp_max = sapply(name, function(v) max(df_pq[[v]], na.rm = TRUE))
  )

cat("\nWindow length discrepancy (closed_n_days in YAML/data vs win_length in VariablesMetaData.csv):\n")
print(table(closed_minus_csv_win_length = w_check$closed_n_days - w_check$win_length))

exceeds_csv_naive <- w_check %>%
  mutate(
    naive_max = case_when(
      time_step == "daily" & !is.na(valid_max) ~ win_length * 1.0,
      day == "24h" & !is.na(valid_max) ~ win_length * 24.0,
      day == "12h" & !is.na(valid_max) ~ win_length * 12.0,
      TRUE ~ NA_real_
    )
  ) %>%
  filter(!is.na(naive_max) & emp_max > naive_max)
cat("Count variables where observed empirical max EXCEEDS naive win_length bound:",
    nrow(exceeds_csv_naive), "out of", sum(!is.na(w_check$valid_max)), "bounded count variables\n")
print(head(exceeds_csv_naive %>%
             select(name, window_start_day, window_end_day, win_length, closed_n_days, naive_max, emp_max, valid_max), 10))
cat("Any variable exceeding YAML valid_max?:", sum(!is.na(w_check$valid_max) & w_check$emp_max > w_check$valid_max), "\n")
cat("Any variable below YAML valid_min?:", sum(!is.na(w_check$valid_min) & w_check$emp_min < w_check$valid_min), "\n")

# Check YAML missing condition or unit fields
cat("Weather vars in YAML without 'condition' field:",
    paste(w_check$name[is.na(w_check$condition)], collapse = ", "), "\n")
cat("Weather vars in YAML without 'unit' field:",
    paste(w_check$name[is.na(w_check$unit)], collapse = ", "), "\n")

# Check exact duplicate columns in weather matrix
w_mat <- as.matrix(df_pq[, weather_cols_pq])
cor_all <- cor(w_mat)
ident_idx <- which(abs(cor_all - 1) < 1e-12 & upper.tri(cor_all), arr.ind = TRUE)
cat("\nExact/near-exact linear pairs (r == 1.0) among all 329 weather columns:\n")
for (k in seq_len(nrow(ident_idx))) {
  v1 <- weather_cols_pq[ident_idx[k, 1]]
  v2 <- weather_cols_pq[ident_idx[k, 2]]
  cat(sprintf("  %-26s vs %-26s | max_abs_diff = %g | YAML identical_to: %s / %s\n",
              v1, v2, max(abs(df_pq[[v1]] - df_pq[[v2]])),
              w_check$identical_to[w_check$name == v1],
              w_check$identical_to[w_check$name == v2]))
}
neg_ident_idx <- which(abs(cor_all + 1) < 1e-12 & upper.tri(cor_all), arr.ind = TRUE)
cat("Exact negative linear pairs (r == -1.0):", nrow(neg_ident_idx), "\n")
for (k in seq_len(nrow(neg_ident_idx))) {
  v1 <- weather_cols_pq[neg_ident_idx[k, 1]]
  v2 <- weather_cols_pq[neg_ident_idx[k, 2]]
  cat(sprintf("  %-26s vs %-26s | sum range = [%g, %g]\n",
              v1, v2, min(df_pq[[v1]] + df_pq[[v2]]), max(df_pq[[v1]] + df_pq[[v2]])))
}

# Check exact linear combinations (e.g. T.L15 + T.15T30 + T.G30 == 24 * n_days!)
cat("Check T partition identity on PRE5 (T.L15 + T.15T30 + T.G30):\n")
t_sum_pre5 <- df_pq$T.L15.PRE5.24H + df_pq$T.15T30.PRE5.24H + df_pq$T.G30.PRE5.24H
print(summary(t_sum_pre5))
cat("Note: where T == 30 exactly? Or missing hourly stamps in station series! Let's check min/median/max of T_sum_pre5 (expected 144 if 100% hourly completeness):\n")
cat("Rows with T.L15 + T.15T30 + T.G30 < 144 in PRE5:", sum(t_sum_pre5 < 144), "out of 999!\n")
print(quantile(t_sum_pre5, probs = c(0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1)))

t_sum_pre10 <- df_pq$T.L15.PRE10.24H + df_pq$T.15T30.PRE10.24H + df_pq$T.G30.PRE10.24H
cat("Distribution of T.L15 + T.15T30 + T.G30 in PRE10 (theoretical full hours = 264):\n")
print(quantile(t_sum_pre10, probs = c(0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1)))
cat("Rows with < 264 recorded hours in PRE10:", sum(t_sum_pre10 < 264),
    "| Rows with < 240 hours (<91%):", sum(t_sum_pre10 < 240),
    "| Rows with < 200 hours (<76%):", sum(t_sum_pre10 < 200), "\n")

t_sum_pre15 <- df_pq$T.L15.PRE15.24H + df_pq$T.15T30.PRE15.24H + df_pq$T.G30.PRE15.24H
cat("Distribution of T.L15 + T.15T30 + T.G30 in PRE15 (theoretical full hours = 384):\n")
print(quantile(t_sum_pre15, probs = c(0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1)))

# Also check T.L9 + T.9T30 + T.G30 in PRE7 (where T.15T30.PRE7.24H is omitted because T15307 exists!)
t9_sum_pre7 <- df_pq$T.L9.PRE7.24H + df_pq$T.9T30.PRE7.24H + df_pq$T.G30.PRE7.24H
cat("Distribution of T.L9 + T.9T30 + T.G30 in PRE7 (theoretical full hours = 192):\n")
print(quantile(t9_sum_pre7, probs = c(0, 0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 1)))
cat("Compare T157 - T15307 vs T.G30.PRE7.24H (diff should be >=0 if T157 includes >30):\n")
print(summary((df_pq$T157 - df_pq$T15307) - df_pq$T.G30.PRE7.24H))

# Check UTC "overnight" (12H) vs 24H physical anomaly!
cat("\n=== 3. UTC OVERNIGHT (12H) VS 24H ANOMALY CHECK ===\n")
for (w in c(5, 10, 14, 15)) {
  rh12 <- df_pq[[paste0("RH.A.PRE", w, ".12H")]]
  rh24 <- df_pq[[paste0("RH.A.PRE", w, ".24H")]]
  cat(sprintf("PRE%-2d: mean RH 12H ('overnight' 20-07 UTC) = %.2f%% vs 24H = %.2f%% | pct where 12H < 24H: %.1f%%\n",
              w, mean(rh12), mean(rh24), 100 * mean(rh12 < rh24)))
}
cat(sprintf("PRE10: mean VPD 12H ('overnight' 20-07 UTC) = %.3f kPa vs 24H (VPD.A.1) = %.3f kPa | pct where 12H > 24H: %.1f%%\n",
            mean(df_pq$VPD.A.PRE10.12H), mean(df_pq$VPD.A.1), 100 * mean(df_pq$VPD.A.PRE10.12H > df_pq$VPD.A.1)))

cat("\n=== 4. MISSING DATA AUDIT ===\n")
na_counts <- colSums(is.na(df_pq))
print(na_counts[na_counts > 0])
print(df_pq[is.na(df_pq$corn), c("id", "year", "state", "fdate", "type", "resist", "corn", "S")])
cat("Locations in RDS for missing corn rows:", paste(df_rds$location[is.na(df_rds$corn)], collapse = ", "), "\n")

cat("\n=== 5. RESPONSE VARIABLE & BINARY EPIDEMIC OUTCOME AUDIT ===\n")
cat("Summary of S (%):\n")
print(summary(df_pq$S))
cat("Mean S:", round(mean(df_pq$S), 3), "SD S:", round(sd(df_pq$S), 3),
    "Skewness:", round(mean(((df_pq$S - mean(df_pq$S))/sd(df_pq$S))^3), 3), "\n")
cat("Exact S == 0:", sum(df_pq$S == 0), sprintf("(%.2f%%)\n", 100 * mean(df_pq$S == 0)))
cat("S < 1%:", sum(df_pq$S < 1), sprintf("(%.2f%%)\n", 100 * mean(df_pq$S < 1)))

for (thr in c(5, 10, 15, 20)) {
  n_ge <- sum(df_pq$S >= thr)
  n_gt <- sum(df_pq$S > thr)
  cat(sprintf("Threshold %2d%%: S >= %2d -> %3d events (%.2f%%), %3d nonevents | S > %2d -> %3d events (%.2f%%)\n",
              thr, thr, n_ge, 100 * n_ge / nrow(df_pq), nrow(df_pq) - n_ge, thr, n_gt, 100 * n_gt / nrow(df_pq)))
}
cat("Exact S == 10 rows:", sum(df_pq$S == 10), "| S in [9.8, 10.2]:",
    paste(sort(df_pq$S[df_pq$S >= 9.8 & df_pq$S <= 10.2]), collapse = ", "), "\n")

cat("\n=== 6. OBSERVATIONAL UNIT, CLUSTERING, & EFFECTIVE SAMPLE SIZE ===\n")
# Exact weather profile fingerprint across all 174 pre-anthesis weather columns
pre_cols <- w_check %>% filter(analysis_period == "pre", !deprecated) %>% pull(name)
cat("Weather variable breakdown by analysis_period:\n")
print(table(period = w_check$analysis_period, deprecated = w_check$deprecated))

w_hash_all329 <- apply(df_pq[, weather_cols_pq], 1, function(r) paste(signif(r, 12), collapse = "|"))
w_hash_pre174 <- apply(df_pq[, pre_cols], 1, function(r) paste(signif(r, 12), collapse = "|"))
df_pq$env_all_id <- as.integer(factor(w_hash_all329))
df_pq$env_pre_id <- as.integer(factor(w_hash_pre174))
df_pq$loc_rds <- df_rds$location
df_pq$epid10 <- as.integer(df_pq$S >= 10)
df_pq$epid05 <- as.integer(df_pq$S >= 5)
df_pq$epid15 <- as.integer(df_pq$S >= 15)

cat("Total plot rows:", nrow(df_pq), "\n")
cat("Unique weather profiles (all 329 weather vars):", n_distinct(df_pq$env_all_id), "\n")
cat("Unique weather profiles (174 pre-anthesis vars):", n_distinct(df_pq$env_pre_id), "\n")
cat("Unique (state, loc_rds, year, fdate) in RDS:", nrow(distinct(df_pq, state, loc_rds, year, fdate)), "\n")
cat("Unique (state, loc_rds, year) site-years in RDS:", nrow(distinct(df_pq, state, loc_rds, year)), "\n")
cat("Unique (state, loc_rds) locations in RDS:", nrow(distinct(df_pq, state, loc_rds)), "\n")
cat("Unique (state, year, fdate) in Parquet:", nrow(distinct(df_pq, state, year, fdate)), "\n")
cat("Unique (state, year) state-years in Parquet:", nrow(distinct(df_pq, state, year)), "\n")
cat("Unique years:", n_distinct(df_pq$year), "| Unique states:", n_distinct(df_pq$state), "\n")

cat("\nPlots per unique pre-anthesis weather profile (env_pre_id):\n")
print(table(plots_per_env = table(df_pq$env_pre_id)))

env_agg <- df_pq %>%
  group_by(env_pre_id) %>%
  summarise(
    n_plots = n(),
    n_states = n_distinct(state),
    n_locs = n_distinct(loc_rds),
    n_fdates = n_distinct(fdate),
    n_resist = n_distinct(resist),
    n_corn = n_distinct(corn, na.rm = TRUE),
    events10 = sum(epid10),
    any_epid10 = as.integer(any(epid10 == 1)),
    all_epid10 = as.integer(all(epid10 == 1)),
    discordant10 = (min(epid10) != max(epid10)),
    .groups = "drop"
  )
cat("Weather profiles with >=1 epidemic plot (S>=10):", sum(env_agg$any_epid10), "out of", nrow(env_agg),
    sprintf("(%.1f%%)\n", 100 * mean(env_agg$any_epid10)))
cat("Weather profiles with >1 plot:", sum(env_agg$n_plots > 1),
    "| Discordant on S>=10 within identical weather:", sum(env_agg$discordant10),
    sprintf("(%.1f%% of multi-plot weather profiles)\n", 100 * sum(env_agg$discordant10) / sum(env_agg$n_plots > 1)))
cat("Weather profiles shared across >1 location in RDS:", sum(env_agg$n_locs > 1),
    "| >1 fdate:", sum(env_agg$n_fdates > 1),
    "| >1 state:", sum(env_agg$n_states > 1), "\n")

# Compute theoretical upper bound on AUC and Brier score for ANY pure pre-anthesis weather model!
# Evaluate both overall and on the 265 multi-plot environments (n = 719 plots) where within-env variance is observable
oracle_prob <- ave(df_pq$epid10, df_pq$env_pre_id, FUN = mean)
oracle_brier <- mean((df_pq$epid10 - oracle_prob)^2)
oracle_auc <- as.numeric(pROC::auc(df_pq$epid10, oracle_prob, quiet = TRUE))
multi_df <- df_pq %>% filter(env_pre_id %in% env_agg$env_pre_id[env_agg$n_plots > 1])
multi_op <- ave(multi_df$epid10, multi_df$env_pre_id, FUN = mean)
multi_brier <- mean((multi_df$epid10 - multi_op)^2)
multi_auc <- as.numeric(pROC::auc(multi_df$epid10, multi_op, quiet = TRUE))
cat(sprintf("In-sample weather-profile ceiling: All 999 plots AUC=%.4f, min_Brier=%.4f | Multi-plot subset (n=%d in %d envs): AUC=%.4f, min_Brier=%.4f\n",
            oracle_auc, oracle_brier, nrow(multi_df), sum(env_agg$n_plots > 1), multi_auc, multi_brier))

# Variance decomposition / Intraclass Correlation (ICC) on logit scale via adaptive Gauss-Hermite quadrature (nAGQ = 20)
m_vc_env <- glmer(epid10 ~ 1 + (1 | env_pre_id), data = df_pq, family = binomial, nAGQ = 20)
m_vc_sy  <- glmer(epid10 ~ 1 + (1 | state:year), data = df_pq, family = binomial, nAGQ = 20)
m_vc_yr  <- glmer(epid10 ~ 1 + (1 | year) + (1 | state), data = df_pq, family = binomial, nAGQ = 1)
var_env <- as.numeric(VarCorr(m_vc_env)$env_pre_id)
var_sy  <- as.numeric(VarCorr(m_vc_sy)$`state:year`)
var_yr  <- as.numeric(VarCorr(m_vc_yr)$year)
var_st  <- as.numeric(VarCorr(m_vc_yr)$state)
pi2_3 <- (pi^2) / 3
icc_env <- var_env / (var_env + pi2_3)
icc_sy  <- var_sy / (var_sy + pi2_3)
cat(sprintf("Logit-scale variance components (nAGQ=20): Var(env_pre_id)=%.3f (ICC=%.3f); Var(state:year)=%.3f (ICC=%.3f); Var(year)=%.3f, Var(state)=%.3f\n",
            var_env, icc_env, var_sy, icc_sy, var_yr, var_st))

# Kish design effect & effective sample size
cluster_sizes_env <- table(df_pq$env_pre_id)
mean_m_env <- mean(cluster_sizes_env)
cv_m_env <- sd(cluster_sizes_env) / mean_m_env
deff_env <- 1 + ((mean_m_env * (1 + cv_m_env^2)) - 1) * icc_env
n_eff_env <- nrow(df_pq) / deff_env
events_eff_env <- sum(df_pq$epid10) / deff_env

cluster_sizes_sy <- table(paste(df_pq$state, df_pq$year))
mean_m_sy <- mean(cluster_sizes_sy)
cv_m_sy <- sd(cluster_sizes_sy) / mean_m_sy
deff_sy <- 1 + ((mean_m_sy * (1 + cv_m_sy^2)) - 1) * icc_sy
n_eff_sy <- nrow(df_pq) / deff_sy
events_eff_sy <- sum(df_pq$epid10) / deff_sy

cat(sprintf("Design effect (weather env clustering): DEFF = %.2f -> N_eff = %.0f, Events_eff (S>=10) = %.0f\n",
            deff_env, n_eff_env, events_eff_env))
cat(sprintf("Design effect (state-year clustering):  DEFF = %.2f -> N_eff = %.0f, Events_eff (S>=10) = %.0f\n",
            deff_sy, n_eff_sy, events_eff_sy))

cat("\n=== 7. GEOGRAPHIC, TEMPORAL & AGRONOMIC DISTRIBUTIONS ===\n")
state_tab <- df_pq %>%
  group_by(state) %>%
  summarise(
    n_plots = n(),
    n_locs_rds = n_distinct(loc_rds),
    n_envs = n_distinct(env_pre_id),
    n_years = n_distinct(year),
    yr_span = paste0(min(year), "-", max(year)),
    pct_spring = round(100 * mean(type == "spring"), 1),
    pct_corn = round(100 * mean(corn == 1, na.rm = TRUE), 1),
    events10 = sum(epid10),
    prev10 = round(100 * mean(epid10), 1),
    med_S = round(median(S), 2),
    max_S = round(max(S), 1),
    .groups = "drop"
  ) %>%
  arrange(desc(n_plots))
print(as.data.frame(state_tab), row.names = FALSE)

cat("\nTemporal coverage by decade / period:\n")
df_pq <- df_pq %>%
  mutate(era = cut(year, breaks = c(1980, 1995, 2000, 2005, 2010, 2016),
                   labels = c("1982-1995", "1996-2000", "2001-2005", "2006-2010", "2011-2015")))
print(as.data.frame(df_pq %>%
  group_by(era) %>%
  summarise(n_plots = n(), n_years = n_distinct(year), n_states = n_distinct(state),
            n_envs = n_distinct(env_pre_id), events10 = sum(epid10), prev10 = round(100*mean(epid10),1), .groups="drop")),
  row.names = FALSE)

cat("\nYear-by-year counts and epidemic prevalence:\n")
yr_tab <- df_pq %>%
  group_by(year) %>%
  summarise(n_plots = n(), n_states = n_distinct(state), n_envs = n_distinct(env_pre_id),
            events10 = sum(epid10), prev10 = round(100*mean(epid10), 1), .groups = "drop")
print(as.data.frame(yr_tab), row.names = FALSE)

cat("\nAgronomic factors vs epidemic prevalence (S >= 10%):\n")
print(as.data.frame(df_pq %>% group_by(type) %>%
  summarise(n=n(), n_states=n_distinct(state), events10=sum(epid10), prev10=round(100*mean(epid10),1), med_S=round(median(S),2))))
print(as.data.frame(df_pq %>% group_by(resist) %>%
  summarise(n=n(), events10=sum(epid10), prev10=round(100*mean(epid10),1), med_S=round(median(S),2))))
print(as.data.frame(df_pq %>% group_by(corn) %>%
  summarise(n=n(), events10=sum(epid10), prev10=round(100*mean(epid10),1), med_S=round(median(S),2))))
cat("Cross-tab type x state:\n")
print(table(df_pq$state, df_pq$type))

cat("\n=== 8. PRE-ANTHESIS WEATHER PREDICTORS: TAXONOMY, CORRELATIONS & EXTREMES ===\n")
pre_meta <- w_check %>% filter(analysis_period == "pre", !deprecated)
cat("Number of pre-anthesis weather predictors:", nrow(pre_meta), "\n")
print(table(type = pre_meta$type, day_scope = pre_meta$day))
cat("\nUnique pre-anthesis windows [window_start_day, window_end_day]:\n")
print(as.data.frame(pre_meta %>%
  count(window_start_day, window_end_day, closed_n_days) %>%
  arrange(desc(window_end_day), desc(window_start_day))), row.names = FALSE)

# Correlation structure of the 174 pre-anthesis weather predictors (computed on the 545 unique weather profiles!)
env_pre_df <- df_pq %>% distinct(env_pre_id, .keep_all = TRUE)
cor_pre <- cor(as.matrix(env_pre_df[, pre_cols]))
upper_vals <- abs(cor_pre[upper.tri(cor_pre)])
cat(sprintf("Pairwise |r| among 174 pre-anthesis vars (across %d unique envs, %d pairs):\n",
            nrow(env_pre_df), length(upper_vals)))
cat(sprintf("  Pairs with |r| >= 0.99: %d (%.1f%%)\n", sum(upper_vals >= 0.99), 100*mean(upper_vals >= 0.99)))
cat(sprintf("  Pairs with |r| >= 0.95: %d (%.1f%%)\n", sum(upper_vals >= 0.95), 100*mean(upper_vals >= 0.95)))
cat(sprintf("  Pairs with |r| >= 0.90: %d (%.1f%%)\n", sum(upper_vals >= 0.90), 100*mean(upper_vals >= 0.90)))
cat(sprintf("  Pairs with |r| >= 0.80: %d (%.1f%%)\n", sum(upper_vals >= 0.80), 100*mean(upper_vals >= 0.80)))
cat(sprintf("  Median pairwise |r|: %.3f | 90th pct: %.3f\n", median(upper_vals), quantile(upper_vals, 0.9)))

# Effective dimensionality via PCA on standardized 174 pre-anthesis predictors
pca_pre <- prcomp(env_pre_df[, pre_cols], center = TRUE, scale. = TRUE)
cum_var <- cumsum(pca_pre$sdev^2) / sum(pca_pre$sdev^2)
cat("PCA cumulative variance explained on 174 pre-anthesis predictors:\n")
for (k in c(1, 2, 3, 5, 10, 15, 20, 30)) {
  cat(sprintf("  Top %2d PCs: %.2f%%\n", k, 100 * cum_var[k]))
}
cat("Number of eigenvalues > 1 (Kaiser):", sum(pca_pre$sdev^2 > 1), "\n")

# Key cross-variable correlations on matching windows (e.g. [-20,0] and [-10,0] and [-7,0])
key_vars <- c("T.A.PRE7.24H", "T.A.PRE10.24H", "T.A.PRE15.24H", "T.A.2", "T.A.3",
              "RH7", "RH.A.PRE10.24H", "RH.A.PRE15.24H", "RH.A.1", "RH.G70.CD.1",
              "VPD.A.1", "VPD.A.2", "TDD.A.1", "D.A.1",
              "RH907", "RH.G90.CHD.1", "RH.G80.CHD.1",
              "TRH807", "TRH907", "TRH.15T30nRHG80.PRE10.24H", "TRH.15T30nRHG80.PRE15.24H",
              "TRH.15T30nRHG80.CHD.1", "P.A.1", "T.MINMAXDIFF.1")
cat("\nCorrelation matrix among representative pre-anthesis variables (selected subset):\n")
sub_vars <- c("T.A.PRE10.24H", "RH.A.PRE10.24H", "VPD.A.1", "TDD.A.1", "D.A.1",
              "RH.G80.CHD.1", "RH.G90.CHD.1", "TRH.15T30nRHG80.PRE10.24H", "T.MINMAXDIFF.1", "P.A.1")
print(round(cor(env_pre_df[, sub_vars]), 2))

# Extreme / influential weather observations check (z-scores > 4 and Mahalanobis distance on top PCs)
z_mat <- scale(env_pre_df[, pre_cols])
max_abs_z <- apply(abs(z_mat), 2, max)
cat("\nPre-anthesis variables with max |z| > 5 across unique environments:\n")
ext_vars <- data.frame(
  name = pre_cols,
  max_abs_z = round(max_abs_z, 2),
  min_val = sapply(pre_cols, function(v) round(min(env_pre_df[[v]]), 2)),
  med_val = sapply(pre_cols, function(v) round(median(env_pre_df[[v]]), 2)),
  max_val = sapply(pre_cols, function(v) round(max(env_pre_df[[v]]), 2))
) %>% filter(max_abs_z > 5) %>% arrange(desc(max_abs_z))
print(ext_vars, row.names = FALSE)

# Identify specific environments with extreme Mahalanobis distance on first 5 PCs
pc5 <- pca_pre$x[, 1:5]
md2 <- mahalanobis(pc5, colMeans(pc5), cov(pc5))
top_out <- order(md2, decreasing = TRUE)[1:8]
cat("\nTop 8 extreme weather environments by 5-PC Mahalanobis distance^2:\n")
print(env_pre_df[top_out, c("id", "year", "state", "loc_rds", "fdate", "type", "S",
                            "T.A.PRE10.24H", "RH.A.PRE10.24H", "VPD.A.1", "T.G30.CHD.1")], row.names = FALSE)

# Save clean audit summary RDS in scratch/output if needed? No, let's keep workspace clean and save audit_summary.rds in data/ or code/output!
dir.create("output", showWarnings = FALSE)
saveRDS(list(
  yaml_df = yaml_df,
  w_check = w_check,
  state_tab = state_tab,
  yr_tab = yr_tab,
  env_agg = env_agg
), "output/audit_artifacts.rds")
cat("\n=== AUDIT COMPLETE ===\n")
