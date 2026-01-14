"""Participant data model and management."""

import random
from dataclasses import dataclass, field, asdict
from typing import Any

CONDITIONS = ["simple_voting", "simple_passive", "clarified_passive", "acp"]


@dataclass
class Participant:
    """Data model for experiment participant."""

    participant_id: str
    condition: str  # simple_voting, simple_passive, clarified_passive, acp
    base_persona: str
    demographics: dict
    enriched_persona: str

    # Voting
    initial_choice: str | None = None
    initial_explanation: str | None = None
    final_choice: str | None = None
    position_changed: bool | None = None

    # Transcripts
    clarification_transcript: list | None = None
    adversarial_transcript: list | None = None

    # Opposition (ACP only)
    opposition_view: str | None = None
    cross_pollination_content: str | None = None

    # Summaries phase (clustering)
    individual_summary: str | None = None
    individual_summary_embedding: list | None = None
    cluster_id: str | None = None

    # Status
    status: str = "pending"  # pending, complete, failed, skipped
    error_message: str | None = None


def create_participants(
    personas: list[dict], config: dict, seed: int | None = None
) -> list[Participant]:
    """Create participants from prepared personas and assign to conditions.

    Args:
        personas: List of dicts with 'base_persona', 'demographics', 'enriched_persona'
        config: Experiment config
        seed: Random seed for reproducibility

    Returns:
        List of Participant objects assigned to conditions
    """
    if seed is not None:
        random.seed(seed)

    participants_per_condition = config["participants_per_condition"]
    total_needed = participants_per_condition * len(CONDITIONS)

    if len(personas) < total_needed:
        raise ValueError(
            f"Need {total_needed} personas but only have {len(personas)}"
        )

    # Shuffle personas for random assignment
    shuffled = personas.copy()
    random.shuffle(shuffled)

    participants = []
    idx = 0

    for condition in CONDITIONS:
        for i in range(participants_per_condition):
            persona = shuffled[idx]
            participant = Participant(
                participant_id=f"p_{idx + 1:04d}",
                condition=condition,
                base_persona=persona["base_persona"],
                demographics=persona["demographics"],
                enriched_persona=persona["enriched_persona"],
            )
            participants.append(participant)
            idx += 1

    return participants


def get_by_condition(participants: list[Participant], condition: str) -> list[Participant]:
    """Filter participants by condition.

    Args:
        participants: List of all participants
        condition: Condition to filter by

    Returns:
        List of participants in the specified condition
    """
    return [p for p in participants if p.condition == condition]


def get_by_status(participants: list[Participant], status: str) -> list[Participant]:
    """Filter participants by status.

    Args:
        participants: List of all participants
        status: Status to filter by (pending, complete, failed, skipped)

    Returns:
        List of participants with the specified status
    """
    return [p for p in participants if p.status == status]


def get_by_conditions(
    participants: list[Participant], conditions: list[str]
) -> list[Participant]:
    """Filter participants by multiple conditions.

    Args:
        participants: List of all participants
        conditions: List of conditions to include

    Returns:
        List of participants in any of the specified conditions
    """
    return [p for p in participants if p.condition in conditions]


def to_dict(participant: Participant) -> dict:
    """Convert participant to dictionary for JSON serialization.

    Args:
        participant: Participant object

    Returns:
        Dictionary representation
    """
    return asdict(participant)


def from_dict(data: dict) -> Participant:
    """Create participant from dictionary.

    Args:
        data: Dictionary with participant data

    Returns:
        Participant object
    """
    return Participant(**data)


def mark_failed(participant: Participant, error_message: str) -> None:
    """Mark a participant as failed.

    Args:
        participant: Participant to mark
        error_message: Description of the failure
    """
    participant.status = "failed"
    participant.error_message = error_message


def mark_complete(participant: Participant) -> None:
    """Mark a participant as complete.

    Args:
        participant: Participant to mark
    """
    participant.status = "complete"
