# Figure 5: Dialogue Depth Analysis
# Shows that ACP involves deeper engagement

library(tidyverse)
source("theme_presentation.R")
source("01_load_data.R")

# Load data
data <- load_all_data()
participants <- data$participants

# Calculate dialogue metrics
dialogue_data <- participants %>%
  filter(
    condition %in% c("clarified_passive", "acp"),
    status == "complete"
  ) %>%
  rowwise() %>%
  mutate(
    # Clarification metrics
    clar_exchanges = if_else(
      is.null(clarification_transcript) || length(clarification_transcript) == 0,
      0L,
      as.integer(length(clarification_transcript) / 2)  # Pairs of exchanges
    ),
    clar_words = if_else(
      is.null(clarification_transcript) || length(clarification_transcript) == 0,
      0L,
      sum(sapply(clarification_transcript, function(x) str_count(x$content, "\\S+")))
    ),
    clar_participant_words = if_else(
      is.null(clarification_transcript) || length(clarification_transcript) == 0,
      0L,
      sum(sapply(
        Filter(function(x) x$role == "participant", clarification_transcript),
        function(x) str_count(x$content, "\\S+")
      ))
    ),

    # Adversarial metrics (ACP only)
    adv_exchanges = if_else(
      is.null(adversarial_transcript) || length(adversarial_transcript) == 0,
      0L,
      as.integer(length(adversarial_transcript) / 2)
    ),
    adv_words = if_else(
      is.null(adversarial_transcript) || length(adversarial_transcript) == 0,
      0L,
      sum(sapply(adversarial_transcript, function(x) str_count(x$content, "\\S+")))
    ),
    adv_participant_words = if_else(
      is.null(adversarial_transcript) || length(adversarial_transcript) == 0,
      0L,
      sum(sapply(
        Filter(function(x) x$role == "participant", adversarial_transcript),
        function(x) str_count(x$content, "\\S+")
      ))
    ),

    # Total engagement
    total_exchanges = clar_exchanges + adv_exchanges,
    total_words = clar_words + adv_words,
    total_participant_words = clar_participant_words + adv_participant_words
  ) %>%
  ungroup()

# Summary statistics
engagement_summary <- dialogue_data %>%
  group_by(condition) %>%
  summarise(
    n = n(),
    mean_exchanges = mean(total_exchanges),
    mean_words = mean(total_words),
    mean_participant_words = mean(total_participant_words),
    se_exchanges = sd(total_exchanges) / sqrt(n()),
    se_words = sd(total_words) / sqrt(n()),
    .groups = "drop"
  )

# Prepare data for plotting
plot_data <- dialogue_data %>%
  select(participant_id, condition, total_exchanges, total_words, total_participant_words) %>%
  pivot_longer(
    cols = c(total_exchanges, total_words, total_participant_words),
    names_to = "metric",
    values_to = "value"
  ) %>%
  mutate(
    metric = recode(metric,
      "total_exchanges" = "Number of\nExchanges",
      "total_words" = "Total Words\nin Dialogue",
      "total_participant_words" = "Participant\nWord Count"
    )
  )

# Create violin + box plot
fig_dialogue <- ggplot(plot_data, aes(x = condition, y = value, fill = condition)) +
  geom_violin(alpha = 0.3, width = 0.8) +
  geom_boxplot(width = 0.2, outlier.shape = NA) +
  stat_summary(
    fun = mean,
    geom = "point",
    shape = 18,
    size = 4,
    color = "red"
  ) +

  facet_wrap(~metric, scales = "free_y", ncol = 3) +

  scale_fill_condition() +
  scale_x_discrete(labels = condition_labels) +

  labs(
    title = "Dialogue Engagement by Condition",
    subtitle = "Red diamonds show group means; ACP includes both clarification and adversarial phases",
    x = NULL,
    y = NULL,
    fill = "Condition"
  ) +

  theme_presentation() +
  theme(
    axis.text.x = element_text(angle = 30, hjust = 1),
    legend.position = "none"
  )

# Display
print(fig_dialogue)

# Save
save_presentation_figure(fig_dialogue, "05_dialogue_depth.png", width = 14, height = 7)

# Alternative: Simple comparison bar chart
fig_dialogue_bars <- ggplot(engagement_summary, aes(x = condition, fill = condition)) +
  geom_col(aes(y = mean_words), width = 0.6) +
  geom_errorbar(
    aes(ymin = mean_words - 1.96 * se_words,
        ymax = mean_words + 1.96 * se_words),
    width = 0.2
  ) +
  geom_text(
    aes(y = mean_words, label = round(mean_words)),
    vjust = -0.5,
    size = 5,
    fontface = "bold"
  ) +

  scale_fill_condition(guide = "none") +
  scale_x_discrete(labels = condition_labels) +
  scale_y_continuous(expand = expansion(mult = c(0, 0.15))) +

  labs(
    title = "Average Total Words in Dialogue",
    subtitle = "ACP participants engage more extensively",
    x = NULL,
    y = "Mean Word Count"
  ) +

  theme_presentation()

save_presentation_figure(fig_dialogue_bars, "05_dialogue_words_bar.png", width = 9, height = 7)

message("Figure 5 (Dialogue Depth) complete!")
