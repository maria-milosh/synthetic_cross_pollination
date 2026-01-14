"""Configuration loading and validation for experiment framework."""

import os
import yaml
from pathlib import Path

REQUIRED_FIELDS = [
    "pilot_id",
    "pilot_name",
    "topic",
    "participants_per_condition",
    "disagreement_threshold",
    "max_clarification_exchanges",
    "max_socratic_exchanges",
    "opposition_method",
    "include_vote_distribution",
    "arguments_per_option",
    "api_sleep_seconds",
    "model",
]

VALID_OPPOSITION_METHODS = [
    "embedding",
    "llm_judge",
    "predefined",
    "highest_voted",
    "cluster_embedding",
]

VALID_CLUSTERING_ALGORITHMS = ["kmeans", "agglomerative"]

DEFAULTS = {
    "api_sleep_seconds": 3,
    "arguments_per_option": 3,
    "include_vote_distribution": False,
    "max_clarification_exchanges": 5,
    "max_socratic_exchanges": 5,
    "disagreement_threshold": 0.5,
    "clustering_algorithm": "kmeans",
    "max_clusters_per_option": 6,
    "embedding_model": "text-embedding-3-small",
}


def load_config(path: str) -> dict:
    """Load and validate a YAML config file.

    Args:
        path: Path to the YAML config file

    Returns:
        Validated config dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config validation fails
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Apply defaults for missing optional fields
    for key, default_value in DEFAULTS.items():
        if key not in config:
            config[key] = default_value

    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    """Validate config has all required fields and valid values.

    Args:
        config: Config dictionary to validate

    Raises:
        ValueError: If validation fails
    """
    # Check required fields
    missing = [f for f in REQUIRED_FIELDS if f not in config]
    if missing:
        raise ValueError(f"Missing required config fields: {missing}")

    # Validate topic structure
    topic = config.get("topic", {})
    if "description" not in topic:
        raise ValueError("Config topic must have 'description'")
    if "options" not in topic or not isinstance(topic["options"], list):
        raise ValueError("Config topic must have 'options' as a list")
    if len(topic["options"]) < 2:
        raise ValueError("Topic must have at least 2 options")

    # Validate opposition method
    method = config.get("opposition_method")
    if method not in VALID_OPPOSITION_METHODS:
        raise ValueError(
            f"Invalid opposition_method '{method}'. "
            f"Must be one of: {VALID_OPPOSITION_METHODS}"
        )

    # If predefined, check for mapping
    if method == "predefined" and "opposition_mapping" not in config:
        raise ValueError(
            "opposition_method 'predefined' requires 'opposition_mapping' in config"
        )

    # Validate clustering algorithm
    clustering_alg = config.get("clustering_algorithm", "kmeans")
    if clustering_alg not in VALID_CLUSTERING_ALGORITHMS:
        raise ValueError(
            f"Invalid clustering_algorithm '{clustering_alg}'. "
            f"Must be one of: {VALID_CLUSTERING_ALGORITHMS}"
        )

    # Validate max clusters
    max_clusters = config.get("max_clusters_per_option", 6)
    if max_clusters < 1:
        raise ValueError("max_clusters_per_option must be >= 1")

    # Validate numeric ranges
    if config["participants_per_condition"] < 1:
        raise ValueError("participants_per_condition must be >= 1")
    if not 0 < config["disagreement_threshold"] <= 1:
        raise ValueError("disagreement_threshold must be between 0 and 1")
    if config["max_clarification_exchanges"] < 1:
        raise ValueError("max_clarification_exchanges must be >= 1")
    if config["max_socratic_exchanges"] < 1:
        raise ValueError("max_socratic_exchanges must be >= 1")


def setup_output_directory(
    config: dict, base_path: str = "outputs", resume: bool = False
) -> str:
    """Create output directory for this pilot run.

    Args:
        config: Config dictionary with pilot_id
        base_path: Base directory for outputs (default: "outputs")
        resume: If True, allow existing directory (for resume mode)

    Returns:
        Path to the output directory

    Raises:
        FileExistsError: If output directory already exists (and resume=False)
        FileNotFoundError: If resume=True but directory doesn't exist
    """
    pilot_id = config["pilot_id"]
    output_dir = Path(base_path) / pilot_id

    if resume:
        if not output_dir.exists():
            raise FileNotFoundError(
                f"Cannot resume: output directory not found: {output_dir}"
            )
        return str(output_dir)

    if output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists: {output_dir}. "
            "Use a different pilot_id, use --resume, or remove the existing directory."
        )

    output_dir.mkdir(parents=True)
    return str(output_dir)


def get_output_directory(config: dict, base_path: str = "outputs") -> str:
    """Get the output directory path for a pilot (without creating it).

    Args:
        config: Config dictionary with pilot_id
        base_path: Base directory for outputs (default: "outputs")

    Returns:
        Path to the output directory
    """
    pilot_id = config["pilot_id"]
    return str(Path(base_path) / pilot_id)
