# Figure 4: Demographic Correlates of Position Change
# Forest plot showing who is most susceptible to changing their mind

library(tidyverse)
library(broom)
source("theme_presentation.R")
source("01_load_data.R")

# Load data
data <- load_all_data()
participants <- data$participants

# Prepare data for logistic regression
model_data <- participants %>%
  filter(
    condition != "simple_voting",
    status == "complete",
    !is.na(position_changed)
  ) %>%
  mutate(
    # Convert factors for modeling
    age_group = cut(age, breaks = c(0, 30, 45, 60, 100),
                    labels = c("18-30", "31-45", "46-60", "60+")),
    education_level = factor(education,
      levels = c("High school", "Some college", "Bachelor's degree",
                 "Master's degree", "Doctorate")),
    income_level = factor(income,
      levels = c("Low income", "Lower-middle income", "Middle income",
                 "Upper-middle income", "High income")),
    political = factor(political_leaning,
      levels = c("very liberal", "liberal", "moderate",
                 "conservative", "very conservative"))
  )

# Fit logistic regression
model <- glm(
  position_changed ~ condition + age + sex + education_level + income_level + political,
  data = model_data,
  family = binomial
)

# Extract coefficients
coef_data <- tidy(model, conf.int = TRUE, exponentiate = TRUE) %>%
  filter(term != "(Intercept)") %>%
  mutate(
    term_clean = case_when(
      str_detect(term, "condition") ~ str_replace(term, "condition", ""),
      str_detect(term, "education") ~ str_replace(term, "education_level", "Edu: "),
      str_detect(term, "income") ~ str_replace(term, "income_level", "Inc: "),
      str_detect(term, "political") ~ str_replace(term, "political", "Pol: "),
      TRUE ~ term
    ),
    category = case_when(
      str_detect(term, "condition") ~ "Condition",
      str_detect(term, "education") ~ "Education",
      str_detect(term, "income") ~ "Income",
      str_detect(term, "political") ~ "Political",
      term == "age" ~ "Demographics",
      term == "sexM" ~ "Demographics",
      TRUE ~ "Other"
    ),
    significant = p.value < 0.05
  )

# Create forest plot
fig_demographics <- ggplot(coef_data, aes(x = estimate, y = reorder(term_clean, estimate))) +
  # Reference line at OR = 1
  geom_vline(xintercept = 1, linetype = "dashed", color = "gray50") +

  # Confidence intervals
  geom_errorbarh(
    aes(xmin = conf.low, xmax = conf.high),
    height = 0.2,
    linewidth = 0.8
  ) +

  # Point estimates
  geom_point(
    aes(color = significant, size = significant),
    shape = 18
  ) +

  # Facet by category
  facet_grid(category ~ ., scales = "free_y", space = "free_y") +

  # Scales
  scale_color_manual(
    values = c("TRUE" = "#E41A1C", "FALSE" = "gray40"),
    labels = c("TRUE" = "p < 0.05", "FALSE" = "p ≥ 0.05"),
    name = "Significance"
  ) +
  scale_size_manual(values = c("TRUE" = 5, "FALSE" = 3), guide = "none") +
  scale_x_log10() +

  # Labels
  labs(
    title = "Predictors of Position Change",
    subtitle = "Odds ratios from logistic regression (reference: simple_passive, baseline categories)",
    x = "Odds Ratio (log scale)",
    y = NULL,
    caption = "Error bars show 95% confidence intervals"
  ) +

  theme_presentation() +
  theme(
    strip.text.y = element_text(angle = 0, hjust = 0),
    legend.position = "bottom"
  )

# Display
print(fig_demographics)

# Save
save_presentation_figure(fig_demographics, "04_demographics_forest.png", width = 10, height = 10)

# Alternative: Simple bar chart of change rates by demographic group
# (More intuitive for presentations)

change_by_group <- model_data %>%
  pivot_longer(
    cols = c(age_group, sex, education_level, political),
    names_to = "demographic",
    values_to = "group"
  ) %>%
  filter(!is.na(group)) %>%
  group_by(demographic, group) %>%
  summarise(
    n = n(),
    change_rate = mean(position_changed, na.rm = TRUE),
    se = sqrt(change_rate * (1 - change_rate) / n),
    .groups = "drop"
  ) %>%
  mutate(
    demographic = recode(demographic,
      "age_group" = "Age",
      "sex" = "Sex",
      "education_level" = "Education",
      "political" = "Political Leaning"
    )
  )

fig_demo_bars <- ggplot(change_by_group, aes(x = group, y = change_rate, fill = group)) +
  geom_col(width = 0.7) +
  geom_errorbar(
    aes(ymin = pmax(0, change_rate - 1.96 * se),
        ymax = pmin(1, change_rate + 1.96 * se)),
    width = 0.2
  ) +
  facet_wrap(~demographic, scales = "free_x", ncol = 2) +
  scale_y_continuous(labels = scales::percent_format()) +
  scale_fill_brewer(palette = "Set2", guide = "none") +
  labs(
    title = "Position Change Rates by Demographics",
    x = NULL,
    y = "Change Rate"
  ) +
  theme_presentation() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1, size = 10))

save_presentation_figure(fig_demo_bars, "04_demographics_bars.png", width = 12, height = 10)

message("Figure 4 (Demographics) complete!")
