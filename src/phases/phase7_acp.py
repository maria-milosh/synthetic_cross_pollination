"""Phase 7: ACP Round 2 - Adversarial dialogue and final votes."""

import logging

from ..participants import Participant, get_by_condition, mark_failed
from ..moderator import run_adversarial_dialogue
from ..simulator import make_final_vote_after_dialogue

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 7: ACP Round 2.

    Run Socratic adversarial dialogue with ACP participants,
    then get their final votes.

    Args:
        participants: All participants
        config: Experiment config

    Returns:
        Dict with status info
    """
    topic = config["topic"]

    # Get ACP participants with opposition views set
    acp = get_by_condition(participants, "acp")
    acp = [p for p in acp if p.status == "complete" and p.opposition_view]

    total = len(acp)
    succeeded = 0
    failed = 0
    changed = 0

    logger.info(f"Phase 7: Running adversarial dialogue for {total} ACP participants")

    for i, participant in enumerate(acp):
        logger.info(f"Phase 7: Processing participant {i + 1}/{total}")

        # Run adversarial dialogue
        transcript = run_adversarial_dialogue(
            participant, participant.opposition_view, topic, config,
            cross_pollination_content=participant.cross_pollination_content
        )

        if transcript is None:
            mark_failed(participant, "Failed during adversarial dialogue")
            failed += 1
            logger.warning(f"Phase 7: Dialogue failed for {participant.participant_id}")
            continue

        participant.adversarial_transcript = transcript

        # Get final vote
        final_choice = make_final_vote_after_dialogue(
            participant, transcript, topic, config
        )

        if final_choice is None:
            mark_failed(participant, "Failed to get final vote after dialogue")
            failed += 1
            logger.warning(f"Phase 7: Final vote failed for {participant.participant_id}")
        else:
            participant.final_choice = final_choice
            participant.position_changed = final_choice != participant.initial_choice
            if participant.position_changed:
                changed += 1
            succeeded += 1

    logger.info(
        f"Phase 7: Complete. {succeeded} succeeded, {failed} failed, "
        f"{changed} changed position out of {total}"
    )

    return {
        "phase": 7,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "position_changed": changed,
    }
