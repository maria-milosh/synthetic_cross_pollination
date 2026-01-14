"""Phase 1: Initial Vote - All participants make their initial choice."""

import logging

from ..participants import Participant, mark_failed, mark_complete
from ..simulator import make_initial_vote

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 1: Initial Vote.

    All participants choose one option (without explanation).
    Reasoning is captured later in the clarification phase.

    Args:
        participants: All participants
        config: Experiment config

    Returns:
        Dict with status info
    """
    topic = config["topic"]
    total = len(participants)
    completed = 0
    failed = 0

    logger.info(f"Phase 1: Starting initial vote for {total} participants")

    for i, participant in enumerate(participants):
        logger.info(f"Phase 1: Processing participant {i + 1}/{total}")

        choice = make_initial_vote(participant, topic, config)

        if choice is None:
            mark_failed(participant, "Failed to get initial vote from LLM")
            failed += 1
            logger.warning(f"Phase 1: Failed for {participant.participant_id}")
        else:
            participant.initial_choice = choice
            # Note: initial_explanation is no longer collected here.
            # Reasoning is extracted from clarification dialogue in Phase 4.
            mark_complete(participant)
            completed += 1

    logger.info(
        f"Phase 1: Complete. {completed} succeeded, {failed} failed out of {total}"
    )

    return {
        "phase": 1,
        "total": total,
        "completed": completed,
        "failed": failed,
    }
