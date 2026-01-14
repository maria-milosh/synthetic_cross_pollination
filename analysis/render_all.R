# Master script to render all figures
# Run this script to generate all visualizations

# Set working directory to analysis folder
if (!grepl("analysis$", getwd())) {
  setwd("analysis")
}

# Create figures directory if it doesn't exist
if (!dir.exists("figures")) {
  dir.create("figures")
}

cat("========================================\n")
cat("LLM Deliberation Experiment Visualizations\n")
cat("========================================\n\n")

# Install required packages if missing
required_packages <- c(
  "tidyverse",
  "jsonlite",
  "ggalluvial",
  "ggtext",
  "patchwork",
  "ggwordcloud",
  "broom",
  "tidytext"
)

missing <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]
if (length(missing) > 0) {
  cat("Installing missing packages:", paste(missing, collapse = ", "), "\n")
  install.packages(missing)
}

# Render each figure
scripts <- c(
  "02_figure_design.R",
  "03_figure_change_rates.R",
  "04_figure_sankey.R",
  "05_figure_demographics.R",
  "06_figure_dialogue.R",
  "07_qualitative.R",
  "08_wordcloud.R"
)

for (script in scripts) {
  cat("\n----------------------------------------\n")
  cat("Running:", script, "\n")
  cat("----------------------------------------\n")

  tryCatch({
    source(script, local = new.env())
    cat("✓ Success\n")
  }, error = function(e) {
    cat("✗ Error:", conditionMessage(e), "\n")
  })
}

cat("\n========================================\n")
cat("All figures complete!\n")
cat("Output directory: figures/\n")
cat("========================================\n")

# List generated files
cat("\nGenerated files:\n")
list.files("figures", full.names = FALSE) %>%
  paste0("  - ", .) %>%
  cat(sep = "\n")
