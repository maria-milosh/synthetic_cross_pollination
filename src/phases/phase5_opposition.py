"""Phase 5: Opposition Selection - Select opposing views for ACP participants."""

import logging

from ..participants import Participant, get_by_condition, mark_failed
from ..opposition import select_opposition

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 5: Opposition Selection.

    Select opposing view for each ACP participant.

    Args:
        participants: All participants
        config: Experiment config

    Returns:
        Dict with status info
    """
    # Get ACP participants
    acp_participants = get_by_condition(participants, "acp")
    # Filter to completed
    acp_participants = [p for p in acp_participants if p.status == "complete"]

    total = len(acp_participants)
    succeeded = 0
    failed = 0

    logger.info(
        f"Phase 5: Selecting opposition for {total} ACP participants "
        f"using method '{config.get('opposition_method')}'"
    )

    for i, participant in enumerate(acp_participants):
        logger.info(f"Phase 5: Processing participant {i + 1}/{total}")

        try:
            opposition = select_opposition(participant, participants, config)
            participant.opposition_view = opposition
            succeeded += 1
            logger.debug(
                f"Phase 5: {participant.participant_id} chose '{participant.initial_choice}', "
                f"opposition: '{opposition}'"
            )
        except Exception as e:
            mark_failed(participant, f"Failed during opposition selection: {e}")
            failed += 1
            logger.warning(f"Phase 5: Failed for {participant.participant_id}: {e}")

    logger.info(
        f"Phase 5: Complete. {succeeded} succeeded, {failed} failed out of {total}"
    )

    return {
        "phase": 5,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
    }
