"""Persistent persona storage management.

Provides unified storage for enriched personas to avoid regenerating them for every pilot.
Maintains 1.5x requested participants in storage for efficient sampling.
"""

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_PATH = Path(__file__).parent.parent / "data" / "personas.json"


def load_storage(path: Path | None = None) -> list[dict]:
    """Load personas from storage file.

    Args:
        path: Path to storage file. Uses default if None.

    Returns:
        List of persona dicts with base_persona, demographics, enriched_persona
    """
    storage_path = path or DEFAULT_STORAGE_PATH

    if not storage_path.exists():
        logger.info(f"No persona storage found at {storage_path}")
        return []

    with open(storage_path) as f:
        data = json.load(f)

    personas = data.get("personas", [])
    logger.info(f"Loaded {len(personas)} personas from storage")
    return personas


def save_storage(personas: list[dict], path: Path | None = None) -> None:
    """Save personas to storage file.

    Args:
        personas: List of persona dicts
        path: Path to storage file. Uses default if None.
    """
    storage_path = path or DEFAULT_STORAGE_PATH

    # Ensure directory exists
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    data = {"personas": personas}

    with open(storage_path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved {len(personas)} personas to storage")


def add_personas(new_personas: list[dict], path: Path | None = None) -> int:
    """Add new personas to storage, avoiding duplicates.

    Args:
        new_personas: List of persona dicts to add
        path: Path to storage file

    Returns:
        Number of personas added
    """
    existing = load_storage(path)

    # Create set of existing base_personas for deduplication
    existing_bases = {p["base_persona"] for p in existing}

    added = 0
    for persona in new_personas:
        if persona["base_persona"] not in existing_bases:
            existing.append(persona)
            existing_bases.add(persona["base_persona"])
            added += 1

    if added > 0:
        save_storage(existing, path)
        logger.info(f"Added {added} new personas to storage")

    return added


def get_personas(
    n: int,
    config: dict,
    seed: int | None = None,
    path: Path | None = None,
) -> list[dict]:
    """Get personas from storage, generating more if needed.

    Implements the 1.5x logic:
    - If storage has < 1.5x needed personas, generate new ones to reach 1.5x
    - Randomly select n personas from storage

    Args:
        n: Number of personas needed
        config: Experiment config (for generating new personas if needed)
        seed: Random seed for reproducibility
        path: Path to storage file

    Returns:
        List of n persona dicts
    """
    from .personas import fetch_personas, generate_demographics, enrich_persona

    if seed is not None:
        random.seed(seed)

    target = int(n * 1.5)
    storage = load_storage(path)
    current_count = len(storage)

    logger.info(f"Need {n} personas, target storage is {target}, have {current_count}")

    # Generate more if below target
    if current_count < target:
        to_generate = target - current_count
        logger.info(f"Generating {to_generate} new personas to reach 1.5x target")

        # Fetch raw personas
        raw_personas = fetch_personas(to_generate, seed)

        new_personas = []
        for i, persona_data in enumerate(raw_personas):
            base = persona_data.get("persona", "")

            # Skip if already in storage
            if any(p["base_persona"] == base for p in storage):
                continue

            logger.info(f"Enriching new persona {i + 1}/{len(raw_personas)}")
            demographics = generate_demographics(base, config)
            enriched = enrich_persona(base, demographics, config)

            new_personas.append(
                {
                    "base_persona": base,
                    "demographics": demographics,
                    "enriched_persona": enriched,
                }
            )

        add_personas(new_personas, path)
        storage = load_storage(path)

    # Select n random personas
    if len(storage) < n:
        logger.warning(f"Storage has only {len(storage)} personas, need {n}")
        return storage

    selected = random.sample(storage, n)
    logger.info(f"Selected {n} personas from storage pool of {len(storage)}")
    return selected


def migrate_from_outputs(outputs_dir: Path | None = None, path: Path | None = None) -> int:
    """Migrate personas from existing pilot outputs to storage.

    Extracts base_persona, demographics, and enriched_persona from
    participants.json files in outputs directory.

    Args:
        outputs_dir: Path to outputs directory. Uses default if None.
        path: Path to storage file

    Returns:
        Number of personas migrated
    """
    if outputs_dir is None:
        outputs_dir = Path(__file__).parent.parent / "outputs"

    if not outputs_dir.exists():
        logger.warning(f"Outputs directory not found: {outputs_dir}")
        return 0

    migrated_personas = []

    for pilot_dir in outputs_dir.iterdir():
        if not pilot_dir.is_dir():
            continue

        participants_file = pilot_dir / "participants.json"
        if not participants_file.exists():
            continue

        logger.info(f"Migrating personas from {pilot_dir.name}")

        with open(participants_file) as f:
            data = json.load(f)

        for participant in data.get("participants", []):
            # Extract only persona-related fields
            persona = {
                "base_persona": participant.get("base_persona", ""),
                "demographics": participant.get("demographics", {}),
                "enriched_persona": participant.get("enriched_persona", ""),
            }

            # Skip invalid entries
            if not persona["base_persona"] or not persona["enriched_persona"]:
                continue

            migrated_personas.append(persona)

    if migrated_personas:
        added = add_personas(migrated_personas, path)
        logger.info(f"Migration complete: {added} new personas added from {len(migrated_personas)} total")
        return added

    return 0
