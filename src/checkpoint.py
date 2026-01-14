"""Checkpoint utilities for experiment resume support."""

import json
import logging
from datetime import datetime
from pathlib import Path

from .participants import Participant, to_dict, from_dict

logger = logging.getLogger(__name__)


def save_checkpoint(
    output_dir: str,
    phase: int,
    participants: list[Participant],
    summary: str | None = None,
    clusters: list | None = None,
    clusters_by_option: dict | None = None,
    terminated_early: bool = False,
    termination_reason: str | None = None,
) -> None:
    """Save checkpoint after completing a phase.

    Saves both checkpoint metadata and full participant state to allow resume.

    Args:
        output_dir: Path to output directory
        phase: The phase number just completed (1-9)
        participants: All participants with current state
        summary: Phase 4 summary (deprecated, kept for backwards compatibility)
        clusters: List of ClusterInfo objects from Phase 4
        clusters_by_option: Dict mapping option -> list of ClusterInfo
        terminated_early: Whether experiment terminated early
        termination_reason: Reason for early termination
    """
    output_path = Path(output_dir)

    # Convert clusters to serializable format
    clusters_data = None
    if clusters:
        clusters_data = [
            c.to_dict() if hasattr(c, "to_dict") else _cluster_to_dict(c)
            for c in clusters
        ]

    clusters_by_option_data = None
    if clusters_by_option:
        clusters_by_option_data = {
            option: [
                c.to_dict() if hasattr(c, "to_dict") else _cluster_to_dict(c)
                for c in cluster_list
            ]
            for option, cluster_list in clusters_by_option.items()
        }

    # Save checkpoint metadata
    checkpoint = {
        "last_completed_phase": phase,
        "terminated_early": terminated_early,
        "termination_reason": termination_reason,
        "phase4_summary": summary,
        "clusters": clusters_data,
        "clusters_by_option": clusters_by_option_data,
        "checkpoint_time": datetime.utcnow().isoformat() + "Z",
    }

    checkpoint_path = output_path / "checkpoint.json"
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint, f, indent=2)

    # Save participants state
    save_participants(output_dir, participants)

    logger.info(f"Checkpoint saved: phase {phase} completed")


def _cluster_to_dict(cluster) -> dict:
    """Convert ClusterInfo to dict (fallback if to_dict not available)."""
    return {
        "cluster_id": cluster.cluster_id,
        "option": cluster.option,
        "description": cluster.description,
        "embedding": cluster.embedding,
        "member_count": cluster.member_count,
        "member_ids": cluster.member_ids,
    }


def save_participants(output_dir: str, participants: list[Participant]) -> None:
    """Save participants state to JSON file.

    Args:
        output_dir: Path to output directory
        participants: All participants with current state
    """
    output_path = Path(output_dir)
    participants_path = output_path / "participants.json"

    # Load existing data to preserve pilot_id if present
    pilot_id = None
    if participants_path.exists():
        with open(participants_path, "r") as f:
            existing = json.load(f)
            pilot_id = existing.get("pilot_id")

    participants_data = {
        "pilot_id": pilot_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "participants": [to_dict(p) for p in participants],
    }

    with open(participants_path, "w") as f:
        json.dump(participants_data, f, indent=2)


def load_checkpoint(output_dir: str) -> dict | None:
    """Load checkpoint data if it exists.

    Args:
        output_dir: Path to output directory

    Returns:
        Checkpoint dict with keys:
            - last_completed_phase: int
            - terminated_early: bool
            - termination_reason: str | None
            - phase4_summary: str | None (deprecated)
            - clusters: list[dict] | None
            - clusters_by_option: dict[str, list[dict]] | None
            - checkpoint_time: str
        Or None if no checkpoint exists
    """
    checkpoint_path = Path(output_dir) / "checkpoint.json"

    if not checkpoint_path.exists():
        return None

    with open(checkpoint_path, "r") as f:
        checkpoint = json.load(f)

    logger.info(
        f"Loaded checkpoint: phase {checkpoint['last_completed_phase']} "
        f"(saved at {checkpoint['checkpoint_time']})"
    )

    return checkpoint


def load_participants(output_dir: str) -> list[Participant] | None:
    """Load participants from checkpoint.

    Args:
        output_dir: Path to output directory

    Returns:
        List of Participant objects, or None if file doesn't exist
    """
    participants_path = Path(output_dir) / "participants.json"

    if not participants_path.exists():
        return None

    with open(participants_path, "r") as f:
        data = json.load(f)

    participants = [from_dict(p) for p in data["participants"]]
    logger.info(f"Loaded {len(participants)} participants from checkpoint")

    return participants


def checkpoint_exists(output_dir: str) -> bool:
    """Check if a checkpoint exists for this experiment.

    Args:
        output_dir: Path to output directory

    Returns:
        True if checkpoint.json exists
    """
    return (Path(output_dir) / "checkpoint.json").exists()
