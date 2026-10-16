# Helpers for benchmark_summary.qmd.
#
# Discovers one sub-folder per model run inside the benchmark directory, pairs each
# with a curated scorecard (scorecards/<slug>.yml) when one exists, and otherwise
# auto-extracts a headline and the first AUC-with-CI it can find in results.md.

library(yaml)

HERE <- normalizePath(getwd())

# Files/folders the benchmark prompt asks every run to deliver.
DELIVERABLES <- c(
  "data_audit.md" = "Data audit", "analysis_plan.md" = "Analysis plan", "code/" = "Code",
  "results.md" = "Results", "critical_assessment.md" = "Critical assessment",
  "comparison_with_literature.md" = "Literature comparison", "analysis_log.md" = "Analysis log",
  "README.md" = "README"
)

RUBRIC <- data.frame(
  key = c("audit", "timing", "outcome", "parsimony", "validation", "calibration",
          "sensitivity", "negatives", "literature", "claims"),
  name = c("Metadata audit", "Prediction-time discipline", "Outcome definition", "Parsimony",
           "Grouped validation", "Calibration & heterogeneity", "Sensitivity analyses",
           "Negative results kept", "Literature, after the fact", "Calibrated claims"),
  desc = c("Cross-checked YAML, schema and data quality; reported inconsistencies",
           "Used only information truly available at anthesis",
           "Justified the binary target without pretending it was documented",
           "Respected the ≤3 weather-term budget and justified complexity",
           "Year/state/temporal hold-outs; honest uncertainty intervals",
           "Calibration plus variation across years, states, hosts",
           "Windows, thresholds, alternative specs",
           "Reported failures without spin or silent replacement",
           "Kept pre/post-literature separate; sourced claims",
           "Language matches the strength of the evidence"),
  stringsAsFactors = FALSE
)

DEFAULT_DRIVE <- path.expand(
  "~/Library/CloudStorage/GoogleDrive-delponte@ufv.br/Meu Drive/21-workingpapers/01_GenAI_PDE_benchmark")

# Read text as UTF-8 regardless of the session locale.
read_utf8 <- function(p) { x <- rawToChar(readBin(p, "raw", file.size(p))); Encoding(x) <- "UTF-8"; x }
read_yaml_utf8 <- function(p) yaml::yaml.load(read_utf8(p))

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0 || (length(a) == 1 && is.na(a))) b else a
esc <- function(x) htmltools::htmlEscape(as.character(x), attribute = TRUE)
fmt <- function(x, d = 3) formatC(x, format = "f", digits = d)
fdate <- function(d, f = "%d %b %Y") {  # month names in English whatever the locale
  m <- if (grepl("%B", f)) month.name else month.abb
  f <- sub("%B|%b", m[as.integer(format(d, "%m"))], f)
  format(d, f)
}

slugify <- function(name) gsub("^-|-$", "", gsub("[^a-z0-9]+", "-", tolower(name)))

resolve_bench_dir <- function(param = "") {
  # Candidates in order. The report folder's parent comes early, so keeping these
  # files in a sub-folder of the benchmark folder (e.g. 01_GenAI_PDE_benchmark/github) just works.
  cands <- c(param, Sys.getenv("BENCH_DIR"), dirname(HERE), HERE, DEFAULT_DRIVE,
             sub("Meu Drive", "My Drive", DEFAULT_DRIVE, fixed = TRUE), file.path(HERE, "drive_mirror"))
  cands <- unique(path.expand(cands[nzchar(cands)]))
  for (cand in cands) {
    if (dir.exists(cand) && any(vapply(list.dirs(cand, recursive = FALSE), is_model_folder, TRUE)))
      return(normalizePath(cand))
  }
  if (nzchar(param) && !dir.exists(path.expand(param)))
    warning("bench_dir does not exist: ", param)
  stop("No folder with model sub-folders (named 'Model - DD_Month_YYYY') found. Tried:\n  ",
       paste(cands, collapse = "\n  "),
       "\nSet params: bench_dir: in benchmark_summary.qmd to the folder that holds the model sub-folders.")
}

# "Claude Opus 5.5 - 10_October_2026" -> list(model = "Claude Opus 5.5", date = as.Date("2026-10-10"))
parse_folder_name <- function(name) {
  m <- regmatches(name, regexec("(\\d{1,2})[_ -]+([A-Za-z]+)[_ -]+(\\d{4})\\s*$", name))[[1]]
  if (length(m) == 4) {
    mon <- match(tolower(m[3]), tolower(month.name))
    if (!is.na(mon)) {
      model <- trimws(sub("\\s*[-–]\\s*$", "", substr(name, 1, regexpr(m[1], name, fixed = TRUE) - 1)))
      return(list(model = model, date = as.Date(sprintf("%s-%02d-%02d", m[4], mon, as.integer(m[2])))))
    }
  }
  list(model = name, date = NULL)
}

# Names in a model folder; directories get a trailing slash. Adds _files.txt entries in a mirror.
list_entries <- function(folder) {
  f <- list.files(folder, all.files = FALSE, no.. = TRUE)
  f <- f[!grepl("^[._]", f) & !grepl("\\.(gdoc|gsheet)$", f)]
  names <- ifelse(dir.exists(file.path(folder, f)), paste0(f, "/"), f)
  snap <- file.path(folder, "_files.txt")
  if (file.exists(snap)) names <- union(names, trimws(Filter(nzchar, strsplit(read_utf8(snap), "\n")[[1]])))
  names
}

is_model_folder <- function(folder) {
  b <- basename(folder)
  dir.exists(folder) && !grepl("^[._]", b) &&
    (!is.null(parse_folder_name(b)$date) || "results.md" %in% list_entries(folder))
}

strip_md <- function(s) {
  s <- gsub("\\\\([\\\\`*_{}()#+.!$|>\\[\\]-])", "\\1", s)   # unescape exported markdown
  s <- gsub("\\[([^]]*)\\]\\([^)]*\\)", "\\1", s)
  s <- gsub("[*_`#>]+", "", s)
  trimws(gsub("\\s+", " ", s))
}

AUC_CI <- "(0\\.\\d{2,4})\\**\\s*[([]\\s*(?:95\\s*%\\s*CI[:\\s]*)?(0\\.\\d{2,4})\\s*(?:–|-|,|to)\\s*(0\\.\\d{2,4})\\s*[])]"

# Best-effort summary for a run that has no curated scorecard yet.
auto_extract <- function(folder) {
  out <- list(auto = TRUE)
  res <- file.path(folder, "results.md")
  if (!file.exists(res)) return(out)
  text <- read_utf8(res)
  for (p in trimws(strsplit(text, "\n\\s*\n")[[1]])) {
    if (nchar(p) > 120 && !grepl("^\\\\?(#|\\||!|\\*\\*Author|\\*\\*Date)", p)) {
      h <- strip_md(p)
      out$headline <- if (nchar(h) > 420) paste0(substr(h, 1, 420), "…") else h
      break
    }
  }
  clean <- gsub("\\", "", text, fixed = TRUE)
  anchor <- regexpr("LOYO|leave-one-year", clean, ignore.case = TRUE, perl = TRUE)
  chunks <- c(if (anchor > 0) substring(clean, anchor), clean)
  for (ch in chunks) {
    m <- regmatches(ch, regexec(AUC_CI, ch, perl = TRUE))[[1]]
    if (length(m) == 4) {
      v <- as.numeric(m[2:4])
      if (v[1] > 0.4 && v[1] < 1 && v[2] <= v[1] && v[1] <= v[3]) {
        out$weather_model <- list(label = "auto-extracted: first AUC with CI in results.md",
                                  auc = v[1], auc_lo = v[2], auc_hi = v[3])
        break
      }
    }
  }
  out
}

discover <- function(bench_dir) {
  folders <- sort(list.dirs(bench_dir, recursive = FALSE))
  runs <- list()
  for (folder in folders) {
    if (!is_model_folder(folder)) next
    nm <- basename(folder)
    pf <- parse_folder_name(nm)
    date <- pf$date %||% as.Date(file.info(folder)$mtime)
    slug <- slugify(nm)
    card <- NULL
    for (cand in c(file.path(folder, "scorecard.yml"), file.path(HERE, "scorecards", paste0(slug, ".yml")))) {
      if (file.exists(cand)) { card <- read_yaml_utf8(cand) %||% list(); break }
    }
    data <- card %||% auto_extract(folder)
    data$model <- data$model %||% pf$model
    data$slug <- slug; data$folder <- nm; data$date <- date
    data$curated <- !is.null(card); data$entries <- list_entries(folder)
    runs[[length(runs) + 1]] <- data
  }
  ord <- order(vapply(runs, function(r) as.numeric(r$date), 0), vapply(runs, function(r) tolower(r$model), ""))
  runs <- runs[ord]
  for (i in seq_along(runs)) runs[[i]]$color <- sprintf("var(--s%d)", (i - 1) %% 8 + 1)
  runs
}

rubric_total <- function(r) if (length(r$rubric)) sum(unlist(r$rubric[RUBRIC$key]), na.rm = TRUE) else NA

has_auc <- function(m) !is.null(m) && !is.null(m$auc)

html_block <- function(s) cat("\n```{=html}\n", s, "\n```\n", sep = "")

# ----------------------------------------------------------------------------- charts
auc_forest <- function(runs, lit_band = c(0.80, 0.90)) {
  rows <- Filter(function(r) has_auc(r$weather_model) || has_auc(r$host_model), runs)
  if (!length(rows)) return("<p>No AUC values available yet.</p>")
  W <- 760; left <- 190; right <- 24; top <- 34; rowh <- 54
  n <- length(rows); H <- top + rowh * n + 42
  X <- function(v) left + (v - 0.45) / (0.95 - 0.45) * (W - left - right)
  s <- sprintf('<svg class="viz" viewBox="0 0 %d %d" role="img" aria-label="Leave-one-year-out AUC by model">', W, H)
  s <- c(s, sprintf(paste0('<rect x="%.1f" y="%d" width="%.1f" height="%d" class="band"><title>Published AUCs on this ',
                           'dataset lineage (random/stratified CV, larger predictor sets, often post-anthesis or host terms)',
                           '</title></rect>'), X(lit_band[1]), top - 8, X(lit_band[2]) - X(lit_band[1]), rowh * n + 8),
         sprintf('<text x="%.1f" y="%d" class="lab-s" text-anchor="middle">published, other validation</text>',
                 mean(X(lit_band)), top - 14))
  for (t in c(0.5, 0.6, 0.7, 0.8, 0.9)) {
    s <- c(s, sprintf('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="%s"/>', X(t), X(t), top - 8, top + rowh * n,
                      if (t == 0.5) "ref" else "grid"),
           sprintf('<text x="%.1f" y="%d" class="lab-s" text-anchor="middle">%.1f</text>', X(t), top + rowh * n + 18, t))
  }
  s <- c(s, sprintf('<text x="%.1f" y="%d" class="lab-s">chance</text>', X(0.5) + 4, top + rowh * n - 4),
         sprintf('<text x="%.1f" y="%d" class="lab-s" text-anchor="middle">Out-of-fold ROC AUC, leave-one-year-out (95%% CI)</text>',
                 (left + W - right) / 2, H - 4))
  for (i in seq_along(rows)) {
    r <- rows[[i]]; cy <- top + rowh * (i - 1) + rowh / 2
    s <- c(s, sprintf('<text x="%d" y="%.1f" class="lab" text-anchor="end">%s</text>', left - 14, cy - 4, esc(r$model)),
           sprintf('<text x="%d" y="%.1f" class="lab-s" text-anchor="end">added %s</text>', left - 14, cy + 12, fdate(r$date)))
    for (spec in list(list("weather_model", -9, "circle"), list("host_model", 9, "diamond"))) {
      m <- r[[spec[[1]]]]
      if (!has_auc(m)) next
      y <- cy + spec[[2]]
      tip <- paste0(r$model, " | ", m$label %||% "", ": AUC ", fmt(m$auc),
                    if (!is.null(m$auc_lo)) sprintf(" (%s–%s)", fmt(m$auc_lo), fmt(m$auc_hi)) else "",
                    if (!is.null(m$brier)) paste0(", Brier ", fmt(m$brier)) else "",
                    if (!is.null(m$cal_slope)) paste0(", cal. slope ", fmt(m$cal_slope, 2)) else "",
                    if (!is.null(m$ci_method)) paste0(" | CI: ", m$ci_method) else "")
      s <- c(s, sprintf('<g class="pt"><title>%s</title>', esc(tip)),
             sprintf('<rect x="%d" y="%.1f" width="%d" height="16" fill="transparent"/>', left, y - 8, W - left - right))
      if (!is.null(m$auc_lo))
        s <- c(s, sprintf('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="%s" stroke-width="2" stroke-linecap="round"/>',
                          X(m$auc_lo), X(m$auc_hi), y, y, r$color))
      fill <- if (isTRUE(r$auto)) "var(--surface)" else r$color
      cx <- X(m$auc)
      s <- c(s, if (spec[[3]] == "circle")
        sprintf('<circle cx="%.1f" cy="%.1f" r="5.5" fill="%s" stroke="%s" stroke-width="2" class="ring"/>', cx, y, fill, r$color)
      else
        sprintf('<rect x="%.1f" y="%.1f" width="10" height="10" transform="rotate(45 %.1f %.1f)" fill="%s" stroke="%s" stroke-width="2" class="ring"/>',
                cx - 5, y - 5, cx, y, fill, r$color),
      sprintf('<text x="%.1f" y="%.1f" class="lab-s">%s</text></g>', X(m$auc_hi %||% m$auc) + 8, y + 4, fmt(m$auc)))
    }
  }
  legend <- paste0('<div class="legend"><span><svg width="14" height="14"><circle cx="7" cy="7" r="5" class="lg"/></svg> weather only</span>',
                   '<span><svg width="14" height="14"><rect x="3" y="3" width="8" height="8" transform="rotate(45 7 7)" class="lg"/></svg> weather + host</span>',
                   '<span><svg width="14" height="14"><rect width="14" height="14" class="band"/></svg> published range</span>',
                   '<span><svg width="14" height="14"><circle cx="7" cy="7" r="5" class="lg hollow"/></svg> auto-extracted, not yet curated</span></div>')
  paste0('<figure class="viz-wrap">', paste(c(s, "</svg>"), collapse = ""), legend, "</figure>")
}

skill_vs_rigor <- function(runs) {
  pts <- Filter(function(r) has_auc(r$weather_model) && !is.na(rubric_total(r)), runs)
  if (length(pts) < 2) return("")
  W <- 560; H <- 340; l <- 56; b <- 46; t <- 20; rt <- 20
  xmax <- 2 * nrow(RUBRIC); xlo <- xmax * 0.4; ylo <- 0.55; yhi <- 0.72
  X <- function(v) l + (v - xlo) / (xmax - xlo) * (W - l - rt)
  Y <- function(v) H - b - (v - ylo) / (yhi - ylo) * (H - b - t)
  s <- sprintf('<svg class="viz" viewBox="0 0 %d %d" role="img" aria-label="Predictive skill versus scientific conduct">', W, H)
  for (v in seq(xlo, xmax, by = 2))
    s <- c(s, sprintf('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" class="grid"/><text x="%.1f" y="%d" class="lab-s" text-anchor="middle">%d</text>',
                      X(v), X(v), t, H - b, X(v), H - b + 16, as.integer(v)))
  for (v in c(0.55, 0.60, 0.65, 0.70))
    s <- c(s, sprintf('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" class="grid"/><text x="%d" y="%.1f" class="lab-s" text-anchor="end">%.2f</text>',
                      l, W - rt, Y(v), Y(v), l - 8, Y(v) + 4, v))
  s <- c(s, sprintf('<text x="%.1f" y="%d" class="lab-s" text-anchor="middle">Scientific-conduct score (0–%d, rubric below)</text>', (l + W - rt) / 2, H - 8, xmax),
         sprintf('<text transform="translate(14 %.1f) rotate(-90)" class="lab-s" text-anchor="middle">Weather-only LOYO AUC</text>', (t + H - b) / 2))
  for (r in pts) {
    x <- X(rubric_total(r)); y <- Y(r$weather_model$auc)
    tip <- sprintf("%s: conduct %d/%d, AUC %s", r$model, as.integer(rubric_total(r)), xmax, fmt(r$weather_model$auc))
    s <- c(s, sprintf(paste0('<g class="pt"><title>%s</title><circle cx="%.1f" cy="%.1f" r="14" fill="transparent"/>',
                             '<circle cx="%.1f" cy="%.1f" r="7" fill="%s" class="ring"/>',
                             '<text x="%.1f" y="%.1f" class="lab" text-anchor="end">%s</text></g>'),
                      esc(tip), x, y, x, y, r$color, x - 11, y + 4, esc(r$model)))
  }
  paste0('<figure class="viz-wrap narrow">', paste(c(s, "</svg>"), collapse = ""), "</figure>")
}

# ----------------------------------------------------------------------------- tables / cards
dot <- function(r) sprintf('<span class="dot" style="background:%s"></span>', r$color)

metrics_table <- function(runs) {
  cell <- function(m, k, d = 3) if (!is.null(m) && !is.null(m[[k]])) fmt(m[[k]], d) else "–"
  ci <- function(m) if (!is.null(m) && !is.null(m$auc_lo))
    sprintf('%s <span class="muted">(%s–%s)</span>', fmt(m$auc), fmt(m$auc_lo), fmt(m$auc_hi)) else cell(m, "auc")
  h <- c('<div class="tbl-wrap"><table class="mtable"><thead><tr><th>Model</th><th>Added</th><th>Outcome</th>',
         '<th>Weather-only model</th><th>AUC (95% CI)</th><th>Brier</th><th>Cal. slope</th>',
         '<th>Best model with host</th><th>AUC (95% CI)</th><th>Brier</th></tr></thead><tbody>')
  for (r in runs) {
    w <- r$weather_model; hm <- r$host_model
    h <- c(h, paste0('<tr><td>', dot(r), esc(r$model), if (isTRUE(r$auto)) ' <span class="badge">auto</span>' else '', '</td>',
                     '<td>', fdate(r$date), '</td><td class="small">', esc(r$outcome %||% "–"), '</td>',
                     '<td class="small">', if (!is.null(w)) esc(w$label) else "–",
                     if (!is.null(w$n_params)) sprintf(' <span class="muted">(%d par.)</span>', as.integer(w$n_params)) else "", '</td>',
                     '<td>', ci(w), '</td><td>', cell(w, "brier"), '</td><td>', cell(w, "cal_slope", 2), '</td>',
                     '<td class="small">', if (!is.null(hm)) esc(hm$label) else '<span class="muted">not fitted</span>', '</td>',
                     '<td>', ci(hm), '</td><td>', cell(hm, "brier"), '</td></tr>'))
  }
  paste(c(h, "</tbody></table></div>"), collapse = "")
}

rubric_heatmap <- function(runs) {
  scored <- Filter(function(r) length(r$rubric) > 0, runs)
  if (!length(scored)) return("")
  words <- c("weak", "partial", "strong")
  h <- c('<div class="tbl-wrap"><table class="heat"><thead><tr><th>Criterion</th>',
         vapply(scored, function(r) paste0("<th>", dot(r), esc(r$model), "</th>"), ""), "</tr></thead><tbody>")
  for (i in seq_len(nrow(RUBRIC))) {
    k <- RUBRIC$key[i]
    h <- c(h, sprintf('<tr><td><strong>%s</strong><br><span class="muted small">%s</span></td>', esc(RUBRIC$name[i]), esc(RUBRIC$desc[i])))
    for (r in scored) {
      v <- r$rubric[[k]]
      h <- c(h, if (is.null(v)) '<td class="muted">–</td>' else
        sprintf('<td class="sc%d" title="%s: %s = %d">%d <span class="small">%s</span></td>', v, esc(r$model), esc(RUBRIC$name[i]), v, v, words[v + 1]))
    }
    h <- c(h, "</tr>")
  }
  h <- c(h, '<tr class="total"><td><strong>Total</strong></td>',
         vapply(scored, function(r) sprintf("<td><strong>%d</strong> / %d</td>", as.integer(rubric_total(r)), 2L * nrow(RUBRIC)), ""),
         "</tr></tbody></table></div>")
  paste(h, collapse = "")
}

consensus_matrix <- function(runs, path) {
  if (!file.exists(path)) return("")
  claims <- read_yaml_utf8(path)$claims
  icon <- list(yes = c("✓", "agrees"), partial = c("~", "partly"), no = c("✗", "disagrees"), na = c("–", "not tested"))
  h <- c('<div class="tbl-wrap"><table class="cons"><thead><tr><th>Finding</th>',
         vapply(runs, function(r) paste0("<th>", dot(r), esc(r$model), "</th>"), ""), "</tr></thead><tbody>")
  for (cl in claims) {
    h <- c(h, sprintf("<tr><td>%s</td>", esc(cl$claim)))
    for (r in runs) {
      e <- cl$models[[r$slug]]
      if (is.null(e)) { h <- c(h, '<td class="muted small">not assessed yet</td>'); next }
      st <- e$status
      if (is.logical(st)) st <- if (st) "yes" else "no"   # YAML reads yes/no as booleans
      ic <- icon[[st]] %||% c("?", "")
      h <- c(h, sprintf('<td class="st-%s"><span class="ic" aria-label="%s">%s</span> <span class="small">%s</span></td>',
                        esc(st), ic[2], ic[1], esc(e$note %||% "")))
    }
    h <- c(h, "</tr>")
  }
  paste(c(h, "</tbody></table></div>"), collapse = "")
}

timeline <- function(runs) {
  dates <- sort(unique(do.call(c, lapply(runs, `[[`, "date"))), decreasing = TRUE)
  h <- '<ol class="timeline">'
  for (d in as.list(dates)) {
    chips <- vapply(Filter(function(r) r$date == d, runs), function(r)
      sprintf('<span class="chip">%s%s%s</span>', dot(r), esc(r$model), if (isTRUE(r$auto)) " · auto" else ""), "")
    h <- c(h, sprintf("<li><time>%s</time><div>%s</div></li>", fdate(d, "%d %B %Y"), paste(chips, collapse = "")))
  }
  paste(c(h, "</ol>"), collapse = "")
}

model_card <- function(r) {
  ul <- function(items, cls = "") if (length(items))
    sprintf('<ul class="%s">%s</ul>', cls, paste0("<li>", esc(unlist(items)), "</li>", collapse = "")) else ""
  present <- names(DELIVERABLES) %in% r$entries
  checks <- paste0(sprintf('<span class="dl %s" title="%s">%s %s</span>', ifelse(present, "ok", "miss"),
                           esc(names(DELIVERABLES)), ifelse(present, "✓", "✗"), esc(DELIVERABLES)), collapse = "")
  b <- c(sprintf('<article class="card" style="--accent:%s">', r$color),
         sprintf('<header><div><h3>%s</h3><div class="muted small">%s%sadded %s · folder “%s”</div></div>%s</header>',
                 esc(r$model), esc(r$provider %||% ""), if (!is.null(r$provider)) " · " else "",
                 fdate(r$date, "%d %B %Y"), esc(r$folder),
                 if (!is.null(r$tagline)) sprintf('<span class="tag">%s</span>', esc(r$tagline)) else ""))
  if (isTRUE(r$auto)) {
    b <- c(b, sprintf(paste0('<p class="notice">New folder found. No curated scorecard yet, so this card is auto-extracted ',
                             'from results.md. Add <code>scorecards/%s.yml</code> to curate it.</p>'), esc(r$slug)))
    if (!is.null(r$headline)) b <- c(b, sprintf("<blockquote>%s</blockquote>", esc(r$headline)))
  }
  if (!is.null(r$verdict)) b <- c(b, sprintf('<p class="verdict">%s</p>', esc(r$verdict)))
  if (!is.null(r$validation)) b <- c(b, sprintf('<p class="small"><strong>Validation.</strong> %s</p>', esc(r$validation)))
  if (length(r$key_findings)) b <- c(b, "<h4>Main results</h4>", ul(r$key_findings))
  if (length(r$strengths) || length(r$concerns))
    b <- c(b, '<div class="two"><div><h4>What it did well</h4>', ul(r$strengths, "plus"),
           '</div><div><h4>Watch out for</h4>', ul(r$concerns, "minus"), "</div></div>")
  if (!is.null(r$literature)) b <- c(b, sprintf('<p class="small"><strong>Versus the literature.</strong> %s</p>', esc(r$literature)))
  paste(c(b, sprintf('<div class="dls"><span class="muted small">Deliverables in folder:</span> %s</div></article>', checks)), collapse = "")
}
