#!/usr/bin/env Rscript
# Generate PDF slide deck for a specific pilot
# Usage: Rscript analysis/generate_report.R <pilot_id>

# Parse command line arguments
args <- commandArgs(trailingOnly = TRUE)

if (length(args) == 0) {
  stop("Usage: Rscript analysis/generate_report.R <pilot_id>\n",
       "Example: Rscript analysis/generate_report.R test_full_001")
}

pilot_id <- args[1]

# Set working directory to analysis folder
# Try multiple methods to find the script directory
get_script_dir <- function() {
  # Method 1: commandArgs
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", cmd_args, value = TRUE)
  if (length(file_arg) > 0) {
    return(dirname(sub("^--file=", "", file_arg)))
  }

  # Method 2: Check common locations
  if (file.exists("analysis/pilot_report.Rmd")) {
    return("analysis")
  }
  if (file.exists("pilot_report.Rmd")) {
    return(".")
  }

  stop("Cannot determine script directory. Run from project root or analysis folder.")
}

script_dir <- get_script_dir()
setwd(script_dir)

# Get project root (parent of analysis/)
project_root <- normalizePath("..")

cat("========================================\n")
cat("LLM Deliberation Report Generator\n")
cat("========================================\n\n")
cat("Pilot ID:", pilot_id, "\n")

# Validate pilot exists
pilot_dir <- file.path(project_root, "outputs", pilot_id)
if (!dir.exists(pilot_dir)) {
  stop("Pilot not found: ", pilot_dir, "\n",
       "Available pilots:\n  ",
       paste(list.dirs(file.path(project_root, "outputs"),
                       recursive = FALSE, full.names = FALSE),
             collapse = "\n  "))
}

# Check for participants.json
participants_file <- file.path(pilot_dir, "participants.json")
if (!file.exists(participants_file)) {
  stop("Missing participants.json in ", pilot_dir)
}

cat("Found pilot data:", pilot_dir, "\n\n")

# Install required packages if missing
required_packages <- c(
  "rmarkdown",
  "knitr",
  "pagedown",
  "tidyverse",
  "jsonlite",
  "ggalluvial",
  "scales"
)

missing <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]
if (length(missing) > 0) {
  cat("Installing missing packages:", paste(missing, collapse = ", "), "\n")
  install.packages(missing, repos = "https://cloud.r-project.org")
}

# Create results directory
results_dir <- file.path(project_root, "results")
if (!dir.exists(results_dir)) {
  dir.create(results_dir, recursive = TRUE)
  cat("Created results directory:", results_dir, "\n")
}

# Output file path
output_pdf <- file.path(results_dir, paste0(pilot_id, ".pdf"))

cat("Rendering report...\n")

# Render the RMarkdown document
tryCatch({
  # First render to HTML
  html_file <- rmarkdown::render(
    input = "pilot_report.Rmd",
    output_format = rmarkdown::ioslides_presentation(
      widescreen = TRUE,
      self_contained = TRUE
    ),
    params = list(
      pilot_id = pilot_id,
      project_root = project_root
    ),
    output_dir = tempdir(),
    quiet = FALSE
  )

  cat("\nConverting HTML to PDF...\n")

  # Convert HTML to PDF using pagedown
  pagedown::chrome_print(
    input = html_file,
    output = output_pdf,
    wait = 10,
    timeout = 60
  )

  # Clean up HTML
  unlink(html_file)

  cat("\n========================================\n")
  cat("Report generated successfully!\n")
  cat("Output:", output_pdf, "\n")
  cat("========================================\n")

}, error = function(e) {
  cat("\nError generating report:\n")
  cat(conditionMessage(e), "\n")
  cat("\nTroubleshooting:\n")
  cat("1. Ensure Chrome/Chromium is installed for PDF conversion\n")
  cat("2. Check that all data files exist in", pilot_dir, "\n")
  cat("3. Run with verbose output: rmarkdown::render() directly\n")
  quit(status = 1)
})
