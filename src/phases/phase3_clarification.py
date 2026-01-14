"""Phase 3: Clarification - Q&A for clarified_passive and ACP participants."""

import logging

from ..participants import Participant, get_by_conditions, mark_failed
from ..moderator import run_clarification

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 3: Clarification.

    Moderator asks clarifying questions to participants in
    clarified_passive and acp conditions.

    Args:
        participants: All participants
        config: Experiment config

    Returns:
        Dict with status info
    """
    topic = config["topic"]

    # Get participants needing clarification
    to_clarify = get_by_conditions(participants, ["clarified_passive", "acp"])
    # Filter to only completed participants (who have initial votes)
    to_clarify = [p for p in to_clarify if p.status == "complete"]

    total = len(to_clarify)
    succeeded = 0
    failed = 0

    logger.info(f"Phase 3: Starting clarification for {total} participants")

    for i, participant in enumerate(to_clarify):
        logger.info(f"Phase 3: Processing participant {i + 1}/{total}")

        transcript = run_clarification(participant, topic, config)

        if transcript is None:
            mark_failed(participant, "Failed during clarification")
            failed += 1
            logger.warning(f"Phase 3: Failed for {participant.participant_id}")
        else:
            participant.clarification_transcript = transcript
            succeeded += 1

    logger.info(
        f"Phase 3: Complete. {succeeded} succeeded, {failed} failed out of {total}"
    )

    return {
        "phase": 3,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
    }
