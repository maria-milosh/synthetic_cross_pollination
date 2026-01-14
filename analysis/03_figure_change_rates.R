# Figure 2: Position Change Rates by Condition (HERO FIGURE)
# Bar chart showing % of participants who changed position

library(tidyverse)
source("theme_presentation.R")
source("01_load_data.R")

# Load data
data <- load_all_data()
participants <- data$participants

# Prepare data for plotting (exclude simple_voting - no final vote)
plot_data <- participants %>%
  filter(condition != "simple_voting", status == "complete") %>%
  group_by(condition) %>%
  summarise(
    n = n(),
    n_changed = sum(position_changed, na.rm = TRUE),
    change_rate = mean(position_changed, na.rm = TRUE),
    # Bootstrap 95% CI
    se = sqrt(change_rate * (1 - change_rate) / n),
    ci_lower = pmax(0, change_rate - 1.96 * se),
    ci_upper = pmin(1, change_rate + 1.96 * se),
    .groups = "drop"
  )

# Create the hero figure
fig_change_rates <- ggplot(plot_data, aes(x = condition, y = change_rate, fill = condition)) +
  # Bar chart
  geom_col(width = 0.7, color = "white", linewidth = 0.5) +

  # Error bars
  geom_errorbar(
    aes(ymin = ci_lower, ymax = ci_upper),
    width = 0.2,
    linewidth = 0.8,
    color = "gray30"
  ) +

  # Add percentage labels on bars
  geom_text(
    aes(label = sprintf("%.1f%%", change_rate * 100)),
    vjust = -0.5,
    size = 6,
    fontface = "bold"
  ) +

  # Add sample size labels below bars
  geom_text(
    aes(y = 0, label = paste0("n=", n)),
    vjust = 1.5,
    size = 4,
    color = "gray40"
  ) +

  # Scales
  scale_fill_condition(guide = "none") +
  scale_y_continuous(
    labels = scales::percent_format(),
    limits = c(0, NA),
    expand = expansion(mult = c(0, 0.15))
  ) +
  scale_x_discrete(labels = condition_labels) +

  # Labels
  labs(
    title = "Position Change Rates by Experimental Condition",
    subtitle = "Percentage of participants who changed their vote after deliberation",
    x = NULL,
    y = "Position Change Rate",
    caption = "Error bars show 95% confidence intervals"
  ) +

  # Theme

  theme_presentation()

# Display
print(fig_change_rates)

# Save
save_presentation_figure(fig_change_rates, "02_change_rates.png", width = 10, height = 7)

# Alternative: Add significance annotations if there are differences
# (This version shows the basic comparison)

# Create version with individual points for transparency
fig_change_rates_points <- ggplot() +
  # Individual points (jittered)
  geom_jitter(
    data = participants %>%
      filter(condition != "simple_voting", status == "complete") %>%
      mutate(position_changed_num = as.numeric(position_changed)),
    aes(x = condition, y = position_changed_num, color = condition),
    width = 0.2,
    height = 0.05,
    alpha = 0.4,
    size = 2
  ) +

  # Mean bar
  stat_summary(
    data = participants %>%
      filter(condition != "simple_voting", status == "complete") %>%
      mutate(position_changed_num = as.numeric(position_changed)),
    aes(x = condition, y = position_changed_num, fill = condition),
    fun = mean,
    geom = "col",
    width = 0.5,
    alpha = 0.7
  ) +

  # Error bars
  stat_summary(
    data = participants %>%
      filter(condition != "simple_voting", status == "complete") %>%
      mutate(position_changed_num = as.numeric(position_changed)),
    aes(x = condition, y = position_changed_num),
    fun.data = mean_cl_boot,
    geom = "errorbar",
    width = 0.2,
    linewidth = 0.8
  ) +

  # Scales
  scale_fill_condition(guide = "none") +
  scale_color_condition(guide = "none") +
  scale_y_continuous(
    labels = scales::percent_format(),
    limits = c(-0.1, 1.1),
    breaks = c(0, 0.5, 1)
  ) +
  scale_x_discrete(labels = condition_labels) +

  # Labels
  labs(
    title = "Position Change Rates by Condition",
    subtitle = "Individual participants shown as points; bars show group means",
    x = NULL,
    y = "Changed Position (0 = No, 1 = Yes)"
  ) +

  theme_presentation()

# Save alternative version
save_presentation_figure(fig_change_rates_points, "02_change_rates_with_points.png", width = 10, height = 7)

message("Figure 2 (Position Change Rates) complete!")
