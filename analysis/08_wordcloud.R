# Figure 7: Word Cloud Comparison
# Visual contrast in language between conditions

library(tidyverse)
library(tidytext)
source("theme_presentation.R")
source("01_load_data.R")

# Check if ggwordcloud is available
if (!requireNamespace("ggwordcloud", quietly = TRUE)) {
  message("Installing ggwordcloud...")
  install.packages("ggwordcloud")
}
library(ggwordcloud)

# Load data
data <- load_all_data()
participants <- data$participants

# Extract text from different sources
# 1. Initial explanations (all conditions)
initial_text <- participants %>%
  filter(status == "complete", !is.na(initial_explanation)) %>%
  select(condition, text = initial_explanation) %>%
  mutate(source = "Initial Explanation")

# 2. Adversarial dialogue (ACP only)
adversarial_text <- participants %>%
  filter(condition == "acp", status == "complete") %>%
  rowwise() %>%
  mutate(
    text = if_else(
      is.null(adversarial_transcript) || length(adversarial_transcript) == 0,
      NA_character_,
      paste(sapply(
        Filter(function(x) x$role == "participant", adversarial_transcript),
        `[[`, "content"
      ), collapse = " ")
    )
  ) %>%
  ungroup() %>%
  filter(!is.na(text)) %>%
  select(condition, text) %>%
  mutate(source = "Adversarial Dialogue")

# Combine
all_text <- bind_rows(initial_text, adversarial_text)

# Tokenize and count words
word_counts <- all_text %>%
  unnest_tokens(word, text) %>%
  # Remove stop words
  anti_join(stop_words, by = "word") %>%
  # Remove numbers
  filter(!str_detect(word, "^\\d+$")) %>%
  # Count by source
  count(source, word, sort = TRUE)

# Get top words per source
top_words <- word_counts %>%
  group_by(source) %>%
  slice_max(n, n = 50) %>%
  ungroup()

# Create comparison word clouds
fig_wordcloud <- ggplot(top_words, aes(label = word, size = n, color = n)) +
  geom_text_wordcloud_area(rm_outside = TRUE) +
  scale_size_area(max_size = 15) +
  scale_color_gradient(low = "gray60", high = "darkblue") +
  facet_wrap(~source, ncol = 2) +
  labs(
    title = "Word Frequency Comparison",
    subtitle = "Most common words in initial explanations vs. adversarial dialogues"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(face = "bold", size = 20, hjust = 0.5),
    plot.subtitle = element_text(size = 14, hjust = 0.5, color = "gray40"),
    strip.text = element_text(face = "bold", size = 14),
    panel.background = element_rect(fill = "gray98", color = NA)
  )

# Save
ggsave(
  "figures/07_wordcloud_comparison.png",
  fig_wordcloud,
  width = 14,
  height = 8,
  dpi = 300,
  bg = "white"
)

# Create a comparison cloud focusing on distinctive words
# Words that are more common in one source vs the other
comparative_words <- word_counts %>%
  pivot_wider(names_from = source, values_from = n, values_fill = 0) %>%
  mutate(
    total = `Initial Explanation` + `Adversarial Dialogue`,
    ratio = (`Adversarial Dialogue` + 1) / (`Initial Explanation` + 1),
    # Log ratio: positive = more in adversarial, negative = more in initial
    log_ratio = log2(ratio),
    dominant_source = if_else(log_ratio > 0, "Adversarial", "Initial")
  ) %>%
  filter(total >= 3) %>%  # Minimum frequency
  arrange(desc(abs(log_ratio)))

# Top distinctive words for each source
distinctive_initial <- comparative_words %>%
  filter(dominant_source == "Initial") %>%
  slice_max(abs(log_ratio), n = 25) %>%
  mutate(display_size = `Initial Explanation`)

distinctive_adversarial <- comparative_words %>%
  filter(dominant_source == "Adversarial") %>%
  slice_max(abs(log_ratio), n = 25) %>%
  mutate(display_size = `Adversarial Dialogue`)

distinctive_all <- bind_rows(
  mutate(distinctive_initial, source = "More in Initial"),
  mutate(distinctive_adversarial, source = "More in Adversarial")
)

fig_distinctive <- ggplot(distinctive_all, aes(label = word, size = display_size, color = source)) +
  geom_text_wordcloud_area(rm_outside = TRUE) +
  scale_size_area(max_size = 12) +
  scale_color_manual(values = c("More in Initial" = "#E41A1C", "More in Adversarial" = "#377EB8")) +
  facet_wrap(~source, ncol = 2) +
  labs(
    title = "Distinctive Language by Context",
    subtitle = "Words that are relatively more common in each context"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(face = "bold", size = 20, hjust = 0.5),
    plot.subtitle = element_text(size = 14, hjust = 0.5, color = "gray40"),
    strip.text = element_text(face = "bold", size = 14),
    legend.position = "none"
  )

ggsave(
  "figures/07_distinctive_words.png",
  fig_distinctive,
  width = 12,
  height = 7,
  dpi = 300,
  bg = "white"
)

# Print some insights
cat("\n=== Distinctive Words Analysis ===\n")
cat("\nTop words more common in ADVERSARIAL dialogues:\n")
print(head(filter(comparative_words, dominant_source == "Adversarial"), 10))
cat("\nTop words more common in INITIAL explanations:\n")
print(head(filter(comparative_words, dominant_source == "Initial"), 10))

message("Figure 7 (Word Clouds) complete!")
