# Figure 6: Qualitative Transcript Showcase
# Display compelling dialogues from position changers

library(tidyverse)
library(ggtext)
source("theme_presentation.R")
source("01_load_data.R")

# Load data
data <- load_all_data()
participants <- data$participants

# Find position changers (prioritize these)
changers <- participants %>%
  filter(
    condition == "acp",
    status == "complete",
    position_changed == TRUE
  )

# If no changers, find best examples from ACP condition
if (nrow(changers) == 0) {
  message("No position changers found. Selecting best adversarial dialogues...")
  changers <- participants %>%
    filter(
      condition == "acp",
      status == "complete",
      !is.null(adversarial_transcript)
    ) %>%
    rowwise() %>%
    mutate(
      dialogue_length = if_else(
        is.null(adversarial_transcript),
        0L,
        length(adversarial_transcript)
      )
    ) %>%
    ungroup() %>%
    arrange(desc(dialogue_length)) %>%
    head(3)
}

# Function to format a single transcript for display
format_transcript <- function(participant) {
  # Extract key info
  persona <- participant$enriched_persona
  initial <- participant$initial_choice
 final <- participant$final_choice
  changed <- participant$position_changed
  transcript <- participant$adversarial_transcript[[1]]

  # Format persona summary (first sentence)
  persona_short <- str_extract(persona, "^[^.]+\\.") %>%
    str_trunc(100)

  # Build formatted output
  output <- list(
    participant_id = participant$participant_id,
    persona = persona_short,
    initial_choice = initial,
    final_choice = final,
    changed = changed,
    exchanges = lapply(transcript, function(x) {
      list(role = x$role, content = str_trunc(x$content, 400))
    })
  )

  return(output)
}

# Format top examples
formatted_examples <- changers %>%
  head(3) %>%
  rowwise() %>%
  mutate(formatted = list(format_transcript(cur_data()))) %>%
  pull(formatted)

# Create a text-based visualization for each example
create_quote_card <- function(example, card_num) {
  changed_text <- if_else(
    example$changed,
    paste0("**Changed:** ", example$initial_choice, " → ", example$final_choice),
    paste0("**Maintained:** ", example$initial_choice)
  )

  # Build the card content
  card_content <- paste0(
    "### Example ", card_num, "\n\n",
    "**Persona:** ", example$persona, "\n\n",
    changed_text, "\n\n",
    "---\n\n"
  )

  # Add exchanges
  for (i in seq_along(example$exchanges)) {
    ex <- example$exchanges[[i]]
    role_label <- if_else(ex$role == "moderator", "🎯 **Moderator:**", "👤 **Participant:**")
    card_content <- paste0(
      card_content,
      role_label, " ", ex$content, "\n\n"
    )
  }

  return(card_content)
}

# Generate markdown output for all examples
all_cards <- map2_chr(formatted_examples, seq_along(formatted_examples), create_quote_card)

# Write to a markdown file for easy presentation inclusion
writeLines(
  c(
    "# Qualitative Transcript Examples",
    "",
    "Selected adversarial dialogues from participants who changed their position.",
    "",
    all_cards
  ),
  "figures/06_transcript_examples.md"
)

message("Transcript examples written to figures/06_transcript_examples.md")

# Create a simple ggplot visualization of the dialogue structure
if (nrow(changers) > 0) {
  # Visualize first example as a timeline
  example <- changers[1, ]

  if (!is.null(example$adversarial_transcript[[1]])) {
    transcript_df <- tibble(
      exchange_num = seq_along(example$adversarial_transcript[[1]]),
      role = sapply(example$adversarial_transcript[[1]], `[[`, "role"),
      content = sapply(example$adversarial_transcript[[1]], `[[`, "content"),
      word_count = str_count(content, "\\S+")
    )

    fig_dialogue_timeline <- ggplot(transcript_df, aes(x = exchange_num, y = word_count, fill = role)) +
      geom_col(width = 0.7) +
      geom_text(aes(label = word_count), vjust = -0.3, size = 4) +

      scale_fill_manual(
        values = c("moderator" = "#1F78B4", "participant" = "#33A02C"),
        labels = c("moderator" = "Moderator", "participant" = "Participant")
      ) +
      scale_x_continuous(breaks = transcript_df$exchange_num) +

      labs(
        title = paste0("Dialogue Structure: ", example$participant_id),
        subtitle = paste0(
          "Initial: ", example$initial_choice, " → Final: ", example$final_choice,
          if_else(example$position_changed, " (CHANGED)", " (unchanged)")
        ),
        x = "Turn Number",
        y = "Word Count",
        fill = "Speaker"
      ) +

      theme_presentation()

    save_presentation_figure(fig_dialogue_timeline, "06_dialogue_timeline.png", width = 10, height = 6)
  }
}

# Print summary
cat("\n=== Qualitative Examples Summary ===\n")
cat("Position changers found:", nrow(changers), "\n")
cat("Examples formatted:", length(formatted_examples), "\n")
cat("Output file: figures/06_transcript_examples.md\n")

message("Figure 6 (Qualitative) complete!")
