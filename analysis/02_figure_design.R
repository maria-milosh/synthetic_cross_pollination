# Figure 1: Experiment Design Overview
# Flow diagram showing the 4 conditions and experimental phases

library(tidyverse)
library(ggtext)
source("theme_presentation.R")

# Create a manual layout for the experiment design
# Using ggplot with custom rectangles and text

# Define phases and their positions
phases <- tibble(
  phase = c("Initial\nVote", "Clarification", "Summary", "Adversarial\nDialogue", "Final\nVote"),
  x = c(1, 2, 3, 4, 5)
)

# Define conditions and which phases they include
conditions <- tibble(
  condition = c("simple_voting", "simple_passive", "clarified_passive", "acp"),
  label = c("Simple Voting\n(N=300)", "Passive Exposure\n(N=300)",
            "Clarified Passive\n(N=300)", "ACP\n(N=300)"),
  y = c(4, 3, 2, 1),
  color = condition_colors[c("simple_voting", "simple_passive", "clarified_passive", "acp")]
)

# Define which phases each condition goes through
phase_matrix <- tribble(
  ~condition, ~phase, ~included,
  "simple_voting", "Initial\nVote", TRUE,
  "simple_voting", "Clarification", FALSE,
  "simple_voting", "Summary", FALSE,
  "simple_voting", "Adversarial\nDialogue", FALSE,
  "simple_voting", "Final\nVote", FALSE,

  "simple_passive", "Initial\nVote", TRUE,
  "simple_passive", "Clarification", FALSE,
  "simple_passive", "Summary", TRUE,
  "simple_passive", "Adversarial\nDialogue", FALSE,
  "simple_passive", "Final\nVote", TRUE,

  "clarified_passive", "Initial\nVote", TRUE,
  "clarified_passive", "Clarification", TRUE,
  "clarified_passive", "Summary", TRUE,
  "clarified_passive", "Adversarial\nDialogue", FALSE,
  "clarified_passive", "Final\nVote", TRUE,

  "acp", "Initial\nVote", TRUE,
  "acp", "Clarification", TRUE,
  "acp", "Summary", TRUE,
  "acp", "Adversarial\nDialogue", TRUE,
  "acp", "Final\nVote", TRUE
)

# Combine for plotting
plot_data <- phase_matrix %>%
  left_join(phases, by = "phase") %>%
  left_join(conditions, by = "condition")

# Create the figure
fig_design <- ggplot(plot_data) +
  # Draw boxes for each phase
  geom_tile(
    aes(x = x, y = y, fill = included, color = condition),
    width = 0.85,
    height = 0.7,
    linewidth = 2
  ) +

  # Add phase labels (only for included phases)
  geom_text(
    data = filter(plot_data, included),
    aes(x = x, y = y, label = phase),
    size = 3.5,
    fontface = "bold",
    color = "white"
  ) +

  # Add condition labels on the left
  geom_text(
    data = distinct(conditions),
    aes(x = 0.2, y = y, label = label, color = condition),
    hjust = 0,
    size = 4,
    fontface = "bold"
  ) +

  # Add arrows between phases (simplified)
  geom_segment(
    data = plot_data %>%
      filter(included) %>%
      group_by(condition) %>%
      arrange(x) %>%
      mutate(x_next = lead(x)) %>%
      filter(!is.na(x_next)),
    aes(x = x + 0.45, xend = x_next - 0.45, y = y, yend = y),
    arrow = arrow(length = unit(0.15, "cm"), type = "closed"),
    color = "gray40",
    linewidth = 0.8
  ) +

  # Scales
  scale_fill_manual(
    values = c("TRUE" = "gray30", "FALSE" = "gray90"),
    guide = "none"
  ) +
  scale_color_manual(values = condition_colors, guide = "none") +
  scale_x_continuous(limits = c(-0.5, 5.8), expand = c(0, 0)) +
  scale_y_continuous(limits = c(0.3, 4.7), expand = c(0, 0)) +

  # Add phase headers at top
  annotate(
    "text",
    x = 1:5,
    y = 4.5,
    label = c("Phase 1", "Phase 3", "Phase 4", "Phase 7", "Phase 6/7"),
    size = 3,
    color = "gray50",
    fontface = "italic"
  ) +

  # Labels
  labs(
    title = "Experimental Design: Four Conditions",
    subtitle = "Each row shows the phases a participant experiences"
  ) +

  theme_void() +
  theme(
    plot.title = element_text(face = "bold", size = 20, hjust = 0.5),
    plot.subtitle = element_text(size = 14, hjust = 0.5, color = "gray40", margin = margin(b = 20)),
    plot.margin = margin(20, 20, 20, 20)
  )

# Display
print(fig_design)

# Save
save_presentation_figure(fig_design, "01_experiment_design.png", width = 14, height = 8)

message("Figure 1 (Experiment Design) complete!")
