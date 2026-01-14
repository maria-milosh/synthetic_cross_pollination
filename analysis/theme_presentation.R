# Custom ggplot2 theme for presentation slides
# Optimized for visual impact, larger fonts, and color-coding

library(ggplot2)

# Color palette for conditions
condition_colors <- c(
  "simple_voting" = "#CCCCCC",
  "simple_passive" = "#A6CEE3",
  "clarified_passive" = "#1F78B4",
  "acp" = "#6A3D9A"
)

# Friendly labels for conditions
condition_labels <- c(
  "simple_voting" = "Simple Voting",
  "simple_passive" = "Passive Exposure",
  "clarified_passive" = "Clarified Passive",
  "acp" = "ACP (Adversarial)"
)

# Main presentation theme
theme_presentation <- function(base_size = 18) {
  theme_minimal(base_size = base_size) +
    theme(
      # Title styling
      plot.title = element_text(
        face = "bold",
        size = rel(1.4),
        hjust = 0,
        margin = margin(b = 10)
      ),
      plot.subtitle = element_text(
        size = rel(1.0),
        color = "gray40",
        margin = margin(b = 15)
      ),
      plot.caption = element_text(
        size = rel(0.7),
        color = "gray50",
        hjust = 1
      ),

      # Axis styling
      axis.title = element_text(face = "bold", size = rel(1.0)),
      axis.title.x = element_text(margin = margin(t = 10)),
      axis.title.y = element_text(margin = margin(r = 10)),
      axis.text = element_text(size = rel(0.9)),

      # Legend styling
      legend.position = "bottom",
      legend.title = element_text(face = "bold", size = rel(0.9)),
      legend.text = element_text(size = rel(0.85)),
      legend.key.size = unit(1.2, "lines"),

      # Panel styling
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(color = "gray90", linewidth = 0.3),

      # Strip styling (for facets)
      strip.text = element_text(face = "bold", size = rel(1.0)),
      strip.background = element_rect(fill = "gray95", color = NA),

      # Plot margins
      plot.margin = margin(15, 15, 15, 15)
    )
}

# Scale for condition colors
scale_fill_condition <- function(...) {
  scale_fill_manual(
    values = condition_colors,
    labels = condition_labels,
    ...
  )
}

scale_color_condition <- function(...) {
  scale_color_manual(
    values = condition_colors,
    labels = condition_labels,
    ...
  )
}

# Helper to save figures at presentation resolution
save_presentation_figure <- function(plot, filename, width = 12, height = 8, dpi = 300) {
  ggsave(
    filename = file.path("figures", filename),
    plot = plot,
    width = width,
    height = height,
    dpi = dpi,
    bg = "white"
  )
  message(paste("Saved:", filename))
}
