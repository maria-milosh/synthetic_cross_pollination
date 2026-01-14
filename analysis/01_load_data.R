# Load and prepare experiment data for visualization
# Run this script first to load data into the environment

library(tidyverse)
library(jsonlite)

# Configuration - set the pilot to analyze
PILOT_DIR <- "../outputs/test_full_001"  # Change this for different pilots

# Load participants data
load_participants <- function(pilot_dir = PILOT_DIR) {
  participants_path <- file.path(pilot_dir, "participants.json")

  if (!file.exists(participants_path)) {
    stop(paste("Participants file not found:", participants_path))
  }

  raw <- fromJSON(participants_path, flatten = TRUE)

  # Extract participants and convert to tibble
  participants <- as_tibble(raw$participants)

  # Clean up column names (flatten nested demographics)
  participants <- participants %>%
    rename_with(~ str_replace(., "demographics\\.", ""), starts_with("demographics."))

  # Convert condition to ordered factor
  participants <- participants %>%
    mutate(
      condition = factor(
        condition,
        levels = c("simple_voting", "simple_passive", "clarified_passive", "acp"),
        ordered = TRUE
      ),
      # Ensure boolean columns are logical
      position_changed = as.logical(position_changed)
    )

  # Add metadata
  attr(participants, "pilot_id") <- raw$pilot_id
  attr(participants, "generated_at") <- raw$generated_at

  return(participants)
}

# Load summary statistics
load_summary <- function(pilot_dir = PILOT_DIR) {
  summary_path <- file.path(pilot_dir, "summary.json")

  if (!file.exists(summary_path)) {
    stop(paste("Summary file not found:", summary_path))
  }

  fromJSON(summary_path)
}

# Compute additional metrics
compute_metrics <- function(participants) {
  # Position change rates by condition
  change_rates <- participants %>%
    filter(!is.na(position_changed)) %>%
    group_by(condition) %>%
    summarise(
      n = n(),
      n_changed = sum(position_changed, na.rm = TRUE),
      change_rate = mean(position_changed, na.rm = TRUE),
      .groups = "drop"
    )

  # Vote distributions
  initial_votes <- participants %>%
    filter(status == "complete", !is.na(initial_choice)) %>%
    count(condition, initial_choice, name = "count") %>%
    group_by(condition) %>%
    mutate(prop = count / sum(count)) %>%
    ungroup()

  final_votes <- participants %>%
    filter(status == "complete", !is.na(final_choice)) %>%
    count(condition, final_choice, name = "count") %>%
    group_by(condition) %>%
    mutate(prop = count / sum(count)) %>%
    ungroup()

  # Dialogue metrics (for conditions with transcripts)
  dialogue_metrics <- participants %>%
    filter(!is.na(clarification_transcript) | !is.na(adversarial_transcript)) %>%
    rowwise() %>%
    mutate(
      clarification_exchanges = if_else(
        is.null(clarification_transcript),
        0L,
        length(clarification_transcript)
      ),
      adversarial_exchanges = if_else(
        is.null(adversarial_transcript),
        0L,
        length(adversarial_transcript)
      ),
      clarification_words = if_else(
        is.null(clarification_transcript),
        0L,
        sum(str_count(sapply(clarification_transcript, `[[`, "content"), "\\S+"))
      ),
      adversarial_words = if_else(
        is.null(adversarial_transcript),
        0L,
        sum(str_count(sapply(adversarial_transcript, `[[`, "content"), "\\S+"))
      )
    ) %>%
    ungroup() %>%
    select(participant_id, condition, starts_with("clarification_"), starts_with("adversarial_"))

  list(
    change_rates = change_rates,
    initial_votes = initial_votes,
    final_votes = final_votes,
    dialogue_metrics = dialogue_metrics
  )
}

# Main loading function
load_all_data <- function(pilot_dir = PILOT_DIR) {
  message(paste("Loading data from:", pilot_dir))

  participants <- load_participants(pilot_dir)
  summary_stats <- load_summary(pilot_dir)
  metrics <- compute_metrics(participants)

  message(paste("Loaded", nrow(participants), "participants"))
  message(paste("Pilot ID:", attr(participants, "pilot_id")))

  list(
    participants = participants,
    summary = summary_stats,
    metrics = metrics
  )
}

# Auto-load if running interactively
if (interactive()) {
  data <- load_all_data()
  participants <- data$participants
  summary_stats <- data$summary
  metrics <- data$metrics
  message("Data loaded into: participants, summary_stats, metrics")
}
