# Figure 3: Vote Distribution Shifts (Sankey/Alluvial Diagram)
# Shows HOW votes moved from initial to final choice

library(tidyverse)
library(ggalluvial)
source("theme_presentation.R")
source("01_load_data.R")

# Load data
data <- load_all_data()
participants <- data$participants

# Prepare alluvial data (only conditions with final votes)
alluvial_data <- participants %>%
  filter(
    condition != "simple_voting",
    status == "complete",
    !is.na(initial_choice),
    !is.na(final_choice)
  ) %>%
  count(condition, initial_choice, final_choice) %>%
  # Create readable labels
  mutate(
    initial_label = str_wrap(initial_choice, 15),
    final_label = str_wrap(final_choice, 15)
  )

# Create alluvial diagram - faceted by condition
fig_sankey <- ggplot(
  alluvial_data,
  aes(
    axis1 = initial_label,
    axis2 = final_label,
    y = n
  )
) +
  geom_alluvium(aes(fill = initial_choice), width = 1/3, alpha = 0.7) +
  geom_stratum(width = 1/3, fill = "gray90", color = "gray50") +
  geom_text(
    stat = "stratum",
    aes(label = after_stat(stratum)),
    size = 3
  ) +

  # Facet by condition
  facet_wrap(~condition, labeller = labeller(condition = condition_labels), ncol = 3) +

  # Scales
  scale_x_discrete(
    limits = c("Initial Vote", "Final Vote"),
    expand = c(0.1, 0.1)
  ) +
  scale_fill_brewer(palette = "Set2", guide = "none") +

  # Labels
  labs(
    title = "Vote Shifts from Initial to Final Choice",
    subtitle = "Flow width proportional to number of participants",
    x = NULL,
    y = "Number of Participants"
  ) +

  theme_presentation() +
  theme(
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank(),
    panel.grid = element_blank()
  )

# Display
print(fig_sankey)

# Save
save_presentation_figure(fig_sankey, "03_vote_sankey.png", width = 14, height = 8)

# Alternative: Combined view (all conditions in one plot)
alluvial_combined <- participants %>%
  filter(
    condition != "simple_voting",
    status == "complete",
    !is.na(initial_choice),
    !is.na(final_choice)
  ) %>%
  mutate(
    changed = initial_choice != final_choice,
    flow_type = if_else(changed, "Changed", "Unchanged")
  ) %>%
  count(condition, initial_choice, final_choice, flow_type)

fig_sankey_combined <- ggplot(
  alluvial_combined,
  aes(
    axis1 = condition,
    axis2 = initial_choice,
    axis3 = final_choice,
    y = n
  )
) +
  geom_alluvium(aes(fill = flow_type), width = 1/4, alpha = 0.7) +
  geom_stratum(width = 1/4, fill = "gray95", color = "gray60") +
  geom_text(
    stat = "stratum",
    aes(label = after_stat(stratum)),
    size = 2.5
  ) +

  scale_x_discrete(
    limits = c("Condition", "Initial\nChoice", "Final\nChoice"),
    expand = c(0.05, 0.05)
  ) +
  scale_fill_manual(
    values = c("Changed" = "#E41A1C", "Unchanged" = "#4DAF4A"),
    name = "Position"
  ) +

  labs(
    title = "Vote Flow Across Conditions",
    subtitle = "Tracking participant choices from condition assignment through final vote",
    x = NULL,
    y = "Number of Participants"
  ) +

  theme_presentation() +
  theme(
    axis.text.y = element_blank(),
    axis.ticks.y = element_blank(),
    panel.grid = element_blank()
  )

save_presentation_figure(fig_sankey_combined, "03_vote_flow_combined.png", width = 12, height = 9)

message("Figure 3 (Sankey Diagram) complete!")
