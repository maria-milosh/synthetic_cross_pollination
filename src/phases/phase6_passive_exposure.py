"""Phase 6: Passive Exposure - Show summary and get final votes."""

import logging

from ..participants import Participant, get_by_conditions, mark_failed
from ..simulator import make_final_vote_after_summary

logger = logging.getLogger(__name__)


def run(
    participants: list[Participant], config: dict, summary: str = "", **kwargs
) -> dict:
    """Run Phase 6: Passive Exposure Round 2.

    Show summary to simple_passive and clarified_passive participants,
    then get their final votes.

    Args:
        participants: All participants
        config: Experiment config
        summary: Summary string from Phase 4

    Returns:
        Dict with status info
    """
    topic = config["topic"]

    # Get passive exposure participants
    passive = get_by_conditions(participants, ["simple_passive", "clarified_passive"])
    # Filter to completed
    passive = [p for p in passive if p.status == "complete"]

    total = len(passive)
    succeeded = 0
    failed = 0
    changed = 0

    logger.info(f"Phase 6: Getting final votes from {total} passive participants")

    for i, participant in enumerate(passive):
        logger.info(f"Phase 6: Processing participant {i + 1}/{total}")

        final_choice = make_final_vote_after_summary(participant, summary, topic, config)

        if final_choice is None:
            mark_failed(participant, "Failed to get final vote")
            failed += 1
            logger.warning(f"Phase 6: Failed for {participant.participant_id}")
        else:
            participant.final_choice = final_choice
            participant.position_changed = final_choice != participant.initial_choice
            if participant.position_changed:
                changed += 1
            succeeded += 1

    logger.info(
        f"Phase 6: Complete. {succeeded} succeeded, {failed} failed, "
        f"{changed} changed position out of {total}"
    )

    return {
        "phase": 6,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "position_changed": changed,
    }
