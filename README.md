# LLM-Mediated Deliberation Experiment

Python framework for running synthetic experiments on collective decision-making. Simulates AI personas making choices across four experimental conditions to test whether cross-pollination and adversarial cross-pollination (Socratic dialogue with opposing views) improves decision quality compared to passive exposure or simple voting.

## Setup

### 1. Create Conda Environment

```bash
conda create -n llm-deliberation python=3.11
conda activate llm-deliberation
pip install -r requirements.txt
```

### 2. Configure API Keys

The project uses OpenAI API. Set one or both of these environment variables:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY="sk-..."
```

By default, the experiment uses `OPENAI_API_KEY`. Use the `--key` flag to switch:

```bash
python -m src.main --config config/example_pilot.yaml --key mykey
```

### 3. R Dependencies (for analysis)

Install R packages for generating reports:

```r
install.packages(c("tidyverse", "jsonlite", "scales", "ggalluvial", "yaml", "pagedown"))
```

## Running Experiments

```bash
# Activate environment
conda activate llm-deliberation

# Run an experiment
python -m src.main --config config/example_pilot.yaml

# Resume an interrupted experiment
python -m src.main --config config/example_pilot.yaml --resume

# Enable verbose logging
python -m src.main --config config/example_pilot.yaml -v
```

## Generating Reports

```bash
# Generate PDF report for a completed pilot
Rscript analysis/generate_report.R <pilot_id>
# Output: results/<pilot_id>.pdf
```

## Project Structure

```
.
├── config/              # Experiment configuration files
├── src/                 # Python source code
│   ├── main.py          # Entry point
│   ├── experiment.py    # Experiment orchestration
│   ├── llm.py           # OpenAI API wrapper
│   ├── personas.py      # Persona generation
│   ├── moderator.py     # Clarification & adversarial dialogue
│   └── simulator.py     # Persona simulation
├── analysis/            # R analysis scripts
│   ├── generate_report.R
│   └── pilot_report.Rmd
├── outputs/             # Experiment outputs (JSON)
├── results/             # Generated PDF reports
└── data/                # Persona storage
```

## Configuration

Create a YAML config file (see `config/example_pilot.yaml`):

```yaml
pilot_name: "My Experiment"
num_participants: 100

topic:
  description: "Should we implement policy X?"
  options:
    - "Yes"
    - "No"
    - "Undecided"

model: "gpt-4o"
```
