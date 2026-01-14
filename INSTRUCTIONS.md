# LLM-Mediated Adversarial Cross-Pollination Experiment Framework

## Project Overview

A Python framework for running synthetic experiments on collective decision-making. The experiment simulates AI personas making choices across four experimental conditions to test whether cross-pollination and adversarial engagement (Socratic dialogue with opposing views) improves decision quality compared to passive exposure or simple voting.

### The Four Conditions

| Condition | Has Clarification | Has Cross-Pollination | Has Adversarial Dialogue | Final Vote |
|-----------|-------------------|----------------------|--------------------------|------------|
| **Simple Voting** | No | No | No | None (initial only) |
| **Simple Passive Cross-Pollination** | No | Yes | No | After cross-pollination |
| **Clarified Passive Cross-Pollination** | Yes | Yes | No | After cross-pollination |
| **ACP (Adversarial Cross-Pollination)** | Yes | Yes | Yes | After adversarial dialogue |

### Execution Sequence (9 Phases)

```
Phase 1: Initial Vote (all participants)
   → All participants choose one option from a list (no explanation collected)
   → Choice stored in participant.initial_choice

Phase 2: Threshold Check
   → Count votes across all participants
   → If any single option has ≥ threshold (default 90%) AND min_responses_for_threshold
     (default 50) reached, terminate experiment early
   → Otherwise continue to Phase 3

Phase 3: Clarification Q&A (600 participants: Clarified Passive + ACP)
   → Moderator LLM asks clarifying questions until satisfied (max 5 exchanges)
   → Reasoning captured through dialogue transcripts
   → Stored in participant.clarification_transcript

Phase 4: Generate Summaries & Clustering (same 600 participants)
   → Extract individual summaries from clarification transcripts using LLM
   → Calculate OpenAI embeddings for each individual summary
   → Cluster participants by voting option using K-means or Agglomerative clustering
   → Optimal cluster count (k) selected via silhouette score (max 6 per option)
   → Generate cluster descriptions using LLM
   → Calculate embeddings for cluster descriptions
   → Store clusters with descriptions and embeddings

Phase 5: Opposition Selection (300 ACP participants only)
   → For each ACP participant, identify opposing view using configured strategy
   → Primary method (cluster_embedding): Computes option-level embeddings as weighted
     mean of cluster embeddings, finds option with greatest cosine distance from
     participant's individual embedding
   → Stored in participant.opposition_view

Phase 6: Cross-Pollination (900 participants: Simple Passive + Clarified Passive + ACP)
   → Format cluster descriptions as markdown showing all viewpoints for all options
   → Passive groups (simple_passive + clarified_passive): View summaries, then make final vote
   → ACP group: View summaries only (stored in participant.cross_pollination_content),
     voting deferred to Phase 7

Phase 7: ACP Adversarial Dialogue (300 ACP participants)
   → Moderator presents opposing view using Socratic questioning
   → Multi-turn back-and-forth until moderator satisfied (max 5 exchanges)
   → Participant makes final vote after dialogue
   → Stored in participant.adversarial_transcript, participant.final_choice

Phase 8: Final Vote (Statistics Collection)
   → No actual voting occurs (voting happened in Phases 6 and 7)
   → Collects and logs final vote statistics by condition

Phase 9: Save Results
   → Write all data to JSON files in outputs/{pilot_id}/
   → Save checkpoint, participants, cluster embeddings, summary statistics
```

---

## Directory Structure

```
synthetic_cross_pollination/
├── config/
│   ├── example_pilot.yaml         # Example config file
│   └── test_small.yaml            # Small test config
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Config loading and validation
│   ├── personas.py                # Persona fetching and enrichment
│   ├── persona_storage.py         # Persistent persona storage with 1.5x pool management
│   ├── participants.py            # Participant dataclass and management
│   ├── llm.py                     # OpenAI LLM API wrapper with throttling and retry
│   ├── embeddings.py              # OpenAI embeddings API wrapper with batch processing
│   ├── clustering.py              # K-means and Agglomerative clustering for position grouping
│   ├── checkpoint.py              # Checkpoint save/load for experiment resume support
│   ├── moderator.py               # Moderator LLM logic (clarification Q&A, Socratic dialogue)
│   ├── simulator.py               # Simulated participant LLM logic
│   ├── opposition.py              # Opposition selection algorithms
│   ├── summarizer.py              # Individual summary extraction and cluster description generation
│   ├── experiment.py              # Main experiment orchestration
│   └── phases/
│       ├── __init__.py
│       ├── phase1_initial_vote.py
│       ├── phase2_threshold_check.py
│       ├── phase3_clarification.py
│       ├── phase4_summaries.py         # Clustering-based summary generation
│       ├── phase5_opposition.py
│       ├── phase6_cross_pollination.py # Cross-pollination (includes ACP viewing)
│       ├── phase7_acp.py               # ACP adversarial dialogue
│       ├── phase8_final_vote.py        # Statistics collection only
│       └── phase9_save.py
├── data/
│   └── personas.json              # Persistent persona storage
├── outputs/                       # Created at runtime
│   └── {pilot_id}/
│       ├── checkpoint.json        # Resume metadata (updated each phase)
│       ├── config.yaml            # Copy of config used
│       ├── participants.json      # All participant data
│       ├── cluster_embeddings.json    # Cluster descriptions with embeddings
│       ├── individual_embeddings.json # Individual summary embeddings
│       └── summary.json           # Aggregate statistics
├── scripts/
│   ├── migrate_personas.py        # Migrate personas from existing pilots to storage
│   └── view_conversation.py       # View conversation transcripts
├── analysis/
│   ├── generate_report.R          # Generate PDF report for a pilot
│   ├── pilot_report.Rmd           # Parameterized ioslides template
│   ├── 01_load_data.R             # Data loading utilities
│   └── theme_presentation.R       # Shared ggplot2 theme
├── requirements.txt
└── README.md
```

---

## Configuration System

### Config File Format (YAML)

```yaml
pilot_id: "pilot_001"
pilot_name: "Participatory Budgeting Test"

# Topic Definition
topic:
  description: |
    Your city has $500,000 in discretionary funds to allocate.
    You must choose which area should receive the funding.
  options:
    - "Park improvements"
    - "Youth job training programs"
    - "Senior services expansion"
    - "Street safety improvements"
    - "Small business grants"

# Sample Size
participants_per_condition: 300

# Disagreement Threshold
disagreement_threshold: 0.5    # Terminate if any option gets >= this proportion
min_responses_for_threshold: 50  # Minimum votes before checking threshold

# Stopping Conditions
max_clarification_exchanges: 5
max_socratic_exchanges: 5

# Opposition Selection
opposition_method: "cluster_embedding"  # Options: "embedding", "llm_judge", "predefined",
                                        #          "highest_voted", "cluster_embedding"
# If using predefined, specify mapping:
# opposition_mapping:
#   "Park improvements": "Street safety improvements"
#   ...

# Cross-Pollination Display
include_vote_distribution: false  # Whether to show vote counts in summary
arguments_per_option: 3           # Legacy: for non-clustering summary generation

# Clustering Configuration
clustering_algorithm: "kmeans"        # Options: "kmeans", "agglomerative"
max_clusters_per_option: 6            # Maximum clusters per voting option
embedding_model: "text-embedding-3-small"  # OpenAI embedding model

# API Settings
api_sleep_seconds: 3        # Delay between API calls
model: "gpt-4o"             # LLM model
max_api_retries: 5          # Max retry attempts on rate limit
api_retry_base_seconds: 2   # Base wait for exponential backoff

# Persona Storage
use_persona_storage: true   # Use persistent persona storage (default true)
                            # Set to false to generate fresh personas each run

# Random Seed (optional, for reproducibility of persona sampling)
# random_seed: 42
```

### Config Module Requirements

- Load YAML config file
- Validate all required fields are present
- Validate opposition_method is one of the allowed values
- Provide defaults for optional fields
- Create output directory `outputs/{pilot_id}/` if it doesn't exist
- Refuse to run if output directory already exists (prevent overwriting) unless resuming

---

## Data Models

### Participant Record

Each participant is stored as a dataclass (`src/participants.py`) with the following fields:

```python
@dataclass
class Participant:
    # Identity
    participant_id: str              # Format: "p_0001", "p_0002", etc.
    condition: str                   # "simple_voting", "simple_passive",
                                     # "clarified_passive", "acp"

    # Persona
    base_persona: str                # Raw persona from persona-hub
    demographics: dict               # LLM-generated demographics
    enriched_persona: str            # Full persona description for LLM prompts

    # Voting
    initial_choice: str | None       # Phase 1 vote (option name only)
    initial_explanation: str | None  # DEPRECATED - not collected (reasoning via clarification)
    final_choice: str | None         # Phase 6 (passive) or Phase 7 (acp)
    position_changed: bool | None    # True if final_choice != initial_choice

    # Transcripts
    clarification_transcript: list | None   # Phase 3: [{role, content}, ...]
    adversarial_transcript: list | None     # Phase 7: [{role, content}, ...]

    # Opposition & Cross-Pollination (ACP only)
    opposition_view: str | None             # Phase 5: opposing option selected
    cross_pollination_content: str | None   # Phase 6: formatted cluster summaries shown

    # Clustering (Phase 4)
    individual_summary: str | None              # Extracted 1-3 sentence summary
    individual_summary_embedding: list | None   # OpenAI embedding vector
    cluster_id: str | None                      # Format: "Option_cluster_N"

    # Status
    status: str                      # "pending", "complete", "failed", "skipped"
    error_message: str | None        # Error details if status is "failed"
```

### Demographics Structure

```python
{
    "age": 42,
    "sex": "F",
    "education": "Bachelor's degree",
    "income": "Middle income",
    "location_type": "suburban",
    "political_leaning": "moderate",
    "occupation": "Marketing manager"
}
```

### Transcript Format

```python
[
    {"role": "moderator", "content": "Why do you believe park improvements should be prioritized?"},
    {"role": "participant", "content": "I think green spaces are essential for..."},
    {"role": "moderator", "content": "How would you respond to someone who says..."},
    ...
]
```

### ClusterInfo Structure

```python
@dataclass
class ClusterInfo:
    cluster_id: str              # e.g., "Youth programs_cluster_0"
    option: str                  # The voting option this cluster belongs to
    description: str             # LLM-generated 3-sentence unified description
    embedding: list[float]       # OpenAI embedding of the description
    member_count: int            # Number of participants in this cluster
    member_ids: list[str]        # List of participant IDs in this cluster
```

---

## Core Modules

### `llm.py` - LLM API Wrapper

- Single class/function to make OpenAI API calls
- Uses model specified in config (default: `gpt-4o`)
- Implements throttling between calls (configurable, default 3 seconds)
- Retry logic with exponential backoff on rate limits
- Parses `Retry-After` header when available
- Special handling for quota exceeded errors (single retry after 60s)
- On final failure: log error, return None (caller marks participant as failed)
- Accepts messages in standard format: `[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]`

### `embeddings.py` - Embeddings API Wrapper

- OpenAI embeddings API wrapper with batch processing
- Model: `text-embedding-3-small` (configurable)
- Batch size: 100 texts per API request
- Throttling between batches
- Same retry logic as LLM calls
- Returns list of embedding vectors (list of floats)

### `clustering.py` - Position Clustering

- Implements K-means and Agglomerative clustering
- Groups participants by voting option, then clusters within each option
- Optimal k selection using silhouette score (tested from k=2 to max_clusters_per_option)
- Minimum cluster count: 2 (if possible given data)
- Maximum cluster count: 6 (configurable)
- Assigns `cluster_id` to each participant (format: `"Option_cluster_N"`)
- Returns `ClusterInfo` objects with descriptions and embeddings

### `persona_storage.py` - Persistent Persona Storage

- Maintains a persistent pool of enriched personas in `data/personas.json`
- Pool management: keeps 1.5x requested participants in storage
- When `get_personas(n)` is called:
  1. Load existing storage
  2. If storage < 1.5×n, generate new personas to reach 1.5×n
  3. Randomly select n personas from the pool
  4. Save updated storage
- Avoids regenerating personas for each pilot run
- Can be disabled with `use_persona_storage: false` in config

### `personas.py` - Persona Fetching and Enrichment

- Fetches personas from: `https://raw.githubusercontent.com/tencent-ailab/persona-hub/refs/heads/main/data/persona.jsonl`
- Filters to English-language personas only
- For each persona, generates demographic enrichment using LLM:
  - Demographics "reasonably flow from persona" - LLM generates plausible values
  - Age, sex, education, income, location type, political leaning, occupation
- Creates enriched persona by asking LLM to write a fuller description combining base persona + assigned demographics + additional life details

### `checkpoint.py` - Resume Support

- Saves checkpoint after each phase to `outputs/{pilot_id}/checkpoint.json`
- Checkpoint contains:
  - `last_completed_phase`: integer (1-9)
  - `terminated_early`: boolean
  - `termination_reason`: string or null
  - `clusters`: list of ClusterInfo objects
  - `clusters_by_option`: dict mapping option to list of ClusterInfo
  - `checkpoint_time`: ISO timestamp
- Participants saved separately to `participants.json` after each phase
- Resume loads checkpoint + participants and continues from next phase

### `participants.py` - Participant Management

- Defines the `Participant` dataclass
- Creates participant records
- Assigns participants to conditions (random assignment, equal sizes)
- Tracks participant status throughout experiment
- Provides methods to query participants by condition, status, etc.
- Serialization to/from JSON

### `moderator.py` - Moderator LLM Logic

Two main functions:

**1. Clarification Q&A (`run_clarification`)**
- System prompt: Neutral moderator helping understand participant's position on topic
- Asks clarifying questions to deeply understand their reasoning
- When fully satisfied, responds with exactly "SATISFIED"
- Input: participant's initial choice (no explanation at this point)
- Output: transcript of Q&A exchanges
- Logic: Loop until moderator says "SATISFIED" or max_clarification_exchanges reached

**2. Socratic Adversarial Dialogue (`run_adversarial_dialogue`)**
- System prompt: Moderator presenting opposing viewpoint using Socratic questioning
- Includes the cross-pollination content shown earlier in context
- Challenges participant's reasoning respectfully but firmly
- When participant has thoroughly engaged, responds with exactly "SATISFIED"
- Input: participant's position, opposing view to present, cross-pollination content
- Output: transcript of dialogue
- Logic: Loop until moderator says "SATISFIED" or max_socratic_exchanges reached

### `simulator.py` - Simulated Participant LLM Logic

- System prompt: You are [enriched persona description]. Respond authentically based on your background, values, and experiences. Stay in character throughout.
- Provides functions for:
  - `make_initial_choice()`: Select option (no explanation)
  - `respond_to_question()`: Answer moderator's clarification questions
  - `respond_to_challenge()`: Engage with adversarial arguments
  - `make_final_vote_after_summary()`: Vote after seeing cross-pollination content
  - `make_final_vote_after_dialogue()`: Vote after adversarial dialogue

### `opposition.py` - Opposition Selection

Module with a common interface and multiple strategies:

**Common Interface:**
```python
def select_opposition(participant, all_participants, method, config,
                      clusters_by_option=None) -> str:
    """Returns the option to present as opposition."""
```

**Strategies:**

1. **`highest_voted`**: Find the option with the most votes that is NOT the participant's choice. If participant chose the most popular option, use second-most popular.

2. **`embedding`**:
   - Compute embeddings of all participants' individual summaries
   - Find the participant whose summary is most distant (cosine distance)
   - Return that participant's chosen option
   - (Deprecated in favor of cluster_embedding)

3. **`llm_judge`**:
   - Send this participant's position plus sample of other positions to LLM
   - Ask LLM to identify which position is "most opposed"
   - Return that position's option

4. **`predefined`**:
   - Use a mapping from config specifying which option opposes which
   - Look up opposition based on participant's choice

5. **`cluster_embedding`** (RECOMMENDED):
   - Compute option-level embeddings as weighted mean of cluster embeddings
   - Weights = member count of each cluster
   - Find option with maximum cosine distance from participant's individual_summary_embedding
   - Most semantically informed approach

### `summarizer.py` - Summary Generation

Two main functions:

**1. Extract Individual Summaries (`extract_individual_summary`)**
- Input: Participant's clarification transcript
- LLM extracts a 1-3 sentence summary of their position
- Output: Summary string stored in `participant.individual_summary`

**2. Generate Cluster Descriptions (`generate_cluster_description`)**
- Input: List of individual summaries from participants in a cluster
- LLM generates unified 3-sentence description capturing the shared perspective
- Output: Description string stored in `ClusterInfo.description`

---

## Phase Implementations

### `phase1_initial_vote.py`

- For each of the total participants (participants_per_condition × 4):
  - Call simulator to make initial choice (option only, no explanation)
  - Store choice in `participant.initial_choice`
  - Log progress every N participants
  - On failure: mark participant as failed, continue to next

### `phase2_threshold_check.py`

- Count votes across all participants (only those with status "complete")
- Calculate proportion for each option
- If `min_responses_for_threshold` not yet reached: continue
- If any option >= `disagreement_threshold`: log message, return signal to terminate
- Otherwise: return signal to continue

### `phase3_clarification.py`

- Filter to participants in conditions: clarified_passive, acp
- For each (600 participants):
  - Run clarification Q&A via moderator
  - Store transcript in `participant.clarification_transcript`
  - On failure: mark as failed, continue

### `phase4_summaries.py`

Multi-step clustering-based summary generation:

1. **Extract Individual Summaries**
   - For each clarified participant, LLM extracts summary from transcript
   - Stored in `participant.individual_summary`

2. **Calculate Embeddings**
   - Batch process individual summaries through embeddings API
   - Stored in `participant.individual_summary_embedding`

3. **Cluster by Option**
   - Group participants by `initial_choice`
   - For each option, run clustering algorithm on embeddings
   - Select optimal k using silhouette score
   - Assign `participant.cluster_id`

4. **Generate Cluster Descriptions**
   - For each cluster, LLM generates unified description
   - Stored in `ClusterInfo.description`

5. **Calculate Cluster Embeddings**
   - Generate embeddings for cluster descriptions
   - Stored in `ClusterInfo.embedding`

Output: `clusters` list and `clusters_by_option` dict for use in later phases

### `phase5_opposition.py`

- Filter to ACP participants only (those with status "complete")
- For each:
  - Call opposition selection with configured method
  - Store the selected opposing view in `participant.opposition_view`

### `phase6_cross_pollination.py`

- Format cluster descriptions as markdown using `format_cross_pollination_content()`
- Shows summaries of all viewpoints organized by option
- **For simple_passive + clarified_passive participants:**
  - Present formatted cross-pollination content
  - Call `make_final_vote_after_summary()` to get final vote
  - Store `final_choice` and `position_changed`
- **For ACP participants:**
  - Present formatted cross-pollination content
  - Store content in `participant.cross_pollination_content`
  - Do NOT vote yet (voting happens after Phase 7)

### `phase7_acp.py`

- Filter to ACP participants (those with `opposition_view` set)
- For each:
  - Run Socratic adversarial dialogue via moderator
  - Moderator has access to cross-pollination content shown in Phase 6
  - Store transcript in `participant.adversarial_transcript`
  - Call `make_final_vote_after_dialogue()` to get final vote
  - Store `final_choice` and `position_changed`

### `phase8_final_vote.py`

- No actual voting occurs (all voting completed in Phases 6 and 7)
- Collect and log final vote statistics by condition:
  - Initial vote distribution
  - Final vote distribution (for conditions with final votes)
  - Position change counts and rates

### `phase9_save.py`

- Save copy of config to `outputs/{pilot_id}/config.yaml` (API keys removed)
- Save all participant records to `outputs/{pilot_id}/participants.json`
- Save cluster data to `outputs/{pilot_id}/cluster_embeddings.json`
- Save individual embeddings to `outputs/{pilot_id}/individual_embeddings.json`
- Calculate and save summary statistics to `outputs/{pilot_id}/summary.json`

---

## Main Entry Point (`main.py`)

```
Usage: python -m src.main --config path/to/config.yaml [--resume] [--key openaikey]
```

**Arguments:**
- `--config`: Path to YAML config file (required)
- `--resume`: Resume an interrupted experiment from checkpoint
- `--key`: API key to use

**Flow:**
1. Load config
2. Check for existing output directory
   - If exists and not resuming: error
   - If resuming: load checkpoint and participants
3. Initialize output directory (if new run)
4. Fetch and prepare personas (from storage or fresh)
5. Create participants and assign to conditions
6. Run phases 1-9 in sequence
7. Handle early termination from threshold check
8. Print summary statistics at end

---

## Output Format

### `participants.json`

```json
{
    "pilot_id": "pilot_001",
    "generated_at": "2025-01-07T14:30:00Z",
    "participants": [
        {
            "participant_id": "p_0001",
            "condition": "acp",
            "base_persona": "A retired school teacher...",
            "demographics": {
                "age": 42,
                "sex": "F",
                "education": "Bachelor's degree",
                "income": "Middle income",
                "location_type": "suburban",
                "political_leaning": "moderate"
            },
            "enriched_persona": "...",
            "initial_choice": "Park improvements",
            "final_choice": "Youth job training programs",
            "position_changed": true,
            "clarification_transcript": [...],
            "adversarial_transcript": [...],
            "individual_summary": "Believes parks are essential...",
            "individual_summary_embedding": [0.123, -0.456, ...],
            "cluster_id": "Park improvements_cluster_0",
            "opposition_view": "Youth job training programs",
            "cross_pollination_content": "## Summary of All Viewpoints...",
            "status": "complete",
            "error_message": null
        },
        ...
    ]
}
```

### `cluster_embeddings.json`

```json
{
    "pilot_id": "pilot_001",
    "generated_at": "2025-01-07T14:30:00Z",
    "clusters": [
        {
            "cluster_id": "Park improvements_cluster_0",
            "option": "Park improvements",
            "description": "This group believes that parks provide essential...",
            "embedding": [0.123, -0.456, ...],
            "member_count": 45,
            "member_ids": ["p_0001", "p_0023", ...]
        },
        ...
    ]
}
```

### `summary.json`

```json
{
    "pilot_id": "pilot_001",
    "terminated_early": false,
    "termination_reason": null,
    "total_participants": 1200,
    "by_condition": {
        "simple_voting": {
            "total": 300,
            "completed": 298,
            "failed": 2,
            "position_changed": null,
            "position_changed_rate": null,
            "initial_vote_distribution": {
                "Park improvements": 45,
                "Youth job training programs": 62,
                ...
            },
            "final_vote_distribution": null
        },
        "simple_passive": {
            "total": 300,
            "completed": 295,
            "failed": 5,
            "position_changed": 47,
            "position_changed_rate": 0.159,
            "initial_vote_distribution": { ... },
            "final_vote_distribution": { ... }
        },
        "clarified_passive": { ... },
        "acp": { ... }
    }
}
```

### `checkpoint.json`

```json
{
    "last_completed_phase": 6,
    "terminated_early": false,
    "termination_reason": null,
    "clusters": [...],
    "clusters_by_option": {
        "Park improvements": [...],
        ...
    },
    "checkpoint_time": "2025-01-07T14:30:00Z"
}
```

---

## Requirements

```
openai
pyyaml
requests
numpy
scikit-learn
```

---

## Additional Notes

1. **Logging**: Uses Python's logging module. Logs to both console and a file in the output directory. Includes timestamps. Logs each phase start/end and participant processing progress.

2. **Reproducibility**: If `random_seed` is specified in config, it seeds all random operations (persona sampling, demographic assignment, condition assignment, clustering).

3. **Modularity for opposition selection**: `opposition.py` is structured so adding a new selection method requires only adding a new function and registering it in a dispatch dictionary.

4. **Error handling**: On API failure: retry with exponential backoff for rate limits (parses Retry-After header). Quota exceeded errors retry once with 60s wait. After max retries: log error with participant ID, mark participant as failed, continue.

5. **Progress feedback**: Regular progress updates to console since experiments make thousands of API calls.

6. **Checkpoint/Resume**: Checkpoints saved after each phase. Resume with `--resume` flag to continue from last completed phase.

7. **Persona Storage**: Persistent storage in `data/personas.json` avoids regenerating personas for each run. Migration script (`scripts/migrate_personas.py`) extracts personas from completed pilots.

---

## Example Commands

```bash
# Activate conda environment
conda activate llm-deliberation

# Run a pilot
python -m src.main --config config/example_pilot.yaml

# Run with specific API key
python -m src.main --config config/example_pilot.yaml --key mykey

# Resume an interrupted experiment
python -m src.main --config config/example_pilot.yaml --resume

# Migrate personas from existing pilots to storage
python scripts/migrate_personas.py

# Generate PDF report for completed pilot
Rscript analysis/generate_report.R <pilot_id>

# Output will be in outputs/{pilot_id}/
```

---

## System and Moderator Prompts by Condition and Phase

This section documents the exact prompts used for each experimental condition at each phase. Variables in `{braces}` are filled in dynamically from config and participant data.

### Participant Base System Prompt (All Conditions)

Used as the foundation for all participant LLM interactions:

```
You are {participant.enriched_persona}

You are participating in a decision-making exercise about the following topic:

{topic['description']}

Available options:
- {option_1}
- {option_2}
- ...

Respond authentically based on your background, values, and experiences. Stay in character throughout.
```

---

### Phase 1: Initial Vote (All Conditions)

**Participant System Prompt:** Base system prompt (above)

**Participant User Prompt:**
```
Please make your choice from the following options.

Options:
1. {option_1}
2. {option_2}
...

Respond with ONLY the exact text of your chosen option, nothing else.
```

---

### Phase 3: Clarification Q&A (Clarified Passive + ACP)

**Moderator System Prompt:**
```
You are a neutral moderator helping understand a participant's position on the following topic:

{topic['description']}

Available options: {options_comma_separated}

The participant chose "{participant.initial_choice}".

Ask clarifying questions to deeply understand their reasoning. Focus on:
- The values and priorities driving their choice
- How they weighed different considerations
- Their understanding of alternatives

Begin by asking them to explain why they made this choice. When you fully understand their position and the reasoning behind it, respond with exactly "SATISFIED" and nothing else.
```

**Participant System Prompt (responding to questions):**
```
{base_system_prompt}

You previously chose "{participant.initial_choice}".

A moderator is asking you clarifying questions to better understand your position and reasoning.
```

---

### Phase 4: Summary Generation (Clarified Passive + ACP)

#### 4a. Extract Individual Summary

**Prompt:**
```
You are analyzing a dialogue between a moderator and a participant about their decision.

The participant chose: "{participant.initial_choice}"

Here is their clarification dialogue:

Moderator: {moderator_message_1}

Participant: {participant_message_1}

Moderator: {moderator_message_2}

Participant: {participant_message_2}
...

Summarize the participant's position and key arguments in 1-3 sentences.
Focus ONLY on the participant's stance and reasoning (not the moderator's questions).
Capture the core values, priorities, and reasoning behind their choice.

Respond with ONLY the summary, no other text.
```

#### 4b. Generate Cluster Description

**Prompt:**
```
You are analyzing a group of participants who all chose "{option}" in a decision-making exercise.

Here are summaries of their individual positions:

Position 1: {individual_summary_1}

Position 2: {individual_summary_2}

Position 3: {individual_summary_3}
...

These participants share similar reasoning patterns. Create a unified description of this cluster's position in exactly 3 sentences:
1. The core argument or value driving this group's choice
2. The key reasoning or evidence they emphasize
3. What distinguishes this perspective from others who made the same choice

Respond with ONLY the 3-sentence description, no numbering or other text.
```

---

### Phase 5: Opposition Selection (ACP Only)

Opposition is selected algorithmically (no LLM prompt) for the default `cluster_embedding` method. However, the `llm_judge` method uses:

**LLM Judge Prompt (if using `opposition_method: llm_judge`):**
```
You are analyzing positions in a decision-making exercise.

Topic: {topic['description']}

Options available: {options_comma_separated}

The participant chose: "{participant.initial_choice}"
Their reasoning: "{participant.initial_explanation}"

Here are some other participants' positions:

Position 1:
Option: {other_choice_1}
Reasoning: {other_reasoning_1}

Position 2:
Option: {other_choice_2}
Reasoning: {other_reasoning_2}
...

Which option represents the MOST OPPOSED viewpoint to the participant's position?
Consider both the choice itself and the underlying values/reasoning.

Respond with ONLY the exact option text, nothing else.
```

---

### Phase 6: Cross-Pollination (Simple Passive + Clarified Passive + ACP)

**Cross-Pollination Content Format** (shown to participant):
```
Here is a summary of the positions that other participants have expressed on the issue and their key arguments.

## {option_1}

Position 1: {cluster_1_description}

Position 2: {cluster_2_description}

## {option_2}

Position 1: {cluster_1_description}

Position 2: {cluster_2_description}

...
```

#### Final Vote After Summary (Simple Passive + Clarified Passive)

**Participant System Prompt:**
```
{base_system_prompt}

You previously chose "{participant.initial_choice}".

You have now been shown a summary of positions from other participants.
```

**Participant User Prompt:**
```
{cross_pollination_content}

Now, please make your final choice. You may stick with your original choice or change to a different option based on what you've read.

Respond with ONLY the exact text of your chosen option, nothing else.
```

---

### Phase 7: Adversarial Dialogue (ACP Only)

**Moderator System Prompt:**
```
You are a moderator presenting an opposing viewpoint using Socratic questioning.

Topic: {topic['description']}

Available options: {options_comma_separated}

The participant chose "{participant.initial_choice}".

Before this dialogue, the participant was shown the following summary of perspectives from all groups:

{cross_pollination_content}

Your goal is to help the participant deeply engage with the counterarguments. Present the opposing view: "{opposition_view}".

Challenge the participant's reasoning respectfully but firmly using Socratic questioning:
- Ask probing questions that reveal assumptions
- Present concrete scenarios where the opposing view might be better
- Explore trade-offs they may not have considered
- Push back on weak reasoning while acknowledging valid points
- Reference arguments from other perspectives shown above when relevant

When the participant has thoroughly engaged with the opposing arguments (shown genuine consideration, addressed key counterpoints), respond with exactly "SATISFIED" and nothing else.
```

**Participant System Prompt (responding to challenges):**
```
{base_system_prompt}

You previously chose "{participant.initial_choice}".

A moderator is presenting you with opposing viewpoints and challenging your reasoning using Socratic questioning. Engage thoughtfully with their arguments while staying true to your perspective and values. You may change your mind if convinced, but don't feel obligated to.
```

#### Final Vote After Dialogue (ACP)

**Participant System Prompt:**
```
{base_system_prompt}

You previously chose "{participant.initial_choice}".

You have just completed a dialogue where a moderator challenged your position with opposing viewpoints.
```

**Participant User Prompt:**
```
You just had the following dialogue:

Moderator: {moderator_message_1}
You: {participant_response_1}
Moderator: {moderator_message_2}
You: {participant_response_2}
...

Now, please make your final choice. You may stick with your original choice or change to a different option based on the discussion.

Respond with ONLY the exact text of your chosen option, nothing else.
```

---

### Persona Enrichment Prompts (Setup Phase)

#### Generate Demographics

**Prompt:**
```
Given this persona description, generate realistic demographics that would make sense for this person.

Persona: {base_persona}

Respond with ONLY a JSON object (no markdown, no explanation) with these exact keys:
- age: integer between 18 and 65
- sex: "M" or "F"
- education: one of ["High school", "Some college", "Bachelor's degree", "Master's degree", "Doctorate"]
- income: one of ["Low income", "Lower-middle income", "Middle income", "Upper-middle income", "High income"]
- location_type: one of ["urban", "suburban", "rural"]
- political_leaning: one of ["very liberal", "liberal", "moderate", "conservative", "very conservative"]

The demographics should reasonably flow from the persona description.
```

#### Enrich Persona

**Prompt:**
```
Create a rich, detailed persona description that combines the following base persona with the given demographics. Write it as a cohesive paragraph (2-3 sentences) that a person could use to role-play this character.

Base persona: {base_persona}

Demographics:
- Age: {age}
- Sex: {sex}
- Education: {education}
- Income level: {income}
- Location type: {location_type}
- Political leaning: {political_leaning}

Write ONLY the persona description, no preamble or explanation.
```

---

### Prompt Flow Summary by Condition

| Condition | Phase 1 | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 |
|-----------|---------|---------|---------|---------|---------|---------|
| **Simple Voting** | Initial vote | - | - | - | - | - |
| **Simple Passive** | Initial vote | - | - | - | View summaries + Final vote | - |
| **Clarified Passive** | Initial vote | Clarification Q&A | Summary extraction | - | View summaries + Final vote | - |
| **ACP** | Initial vote | Clarification Q&A | Summary extraction | Opposition selection | View summaries (no vote) | Adversarial dialogue + Final vote |
