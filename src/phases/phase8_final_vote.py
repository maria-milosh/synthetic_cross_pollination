"""Phase 8: Final Vote - Record final vote statistics.

This is a conceptual phase for clarity. Voting timing hasn't changed:
- simple_passive, clarified_passive: Vote at end of Phase 6 (after cross-pollination)
- acp: Vote at end of Phase 7 (after adversarial dialogue)

This phase logs the final vote statistics.
"""

import logging
from collections import Counter

from ..participants import Participant, get_by_conditions

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 8: Final Vote.

    This phase logs final vote statistics. Actual voting has already occurred:
    - Passive groups voted after cross-pollination (Phase 6)
    - ACP participants voted after adversarial dialogue (Phase 7)

    Args:
        participants: All participants
        config: Experiment config

    Returns:
        Dict with final vote statistics
    """
    logger.info("PHASE 8: Final Vote (recording statistics)")

    # Get vote statistics by condition
    conditions = ["simple_passive", "clarified_passive", "acp"]
    stats_by_condition = {}

    total_voted = 0
    total_changed = 0

    for condition in conditions:
        condition_participants = get_by_conditions(participants, [condition])
        completed = [p for p in condition_participants if p.status == "complete"]
        voted = [p for p in completed if p.final_choice is not None]
        changed = [p for p in voted if p.position_changed]

        # Count vote distribution
        vote_counts = Counter(p.final_choice for p in voted if p.final_choice)

        stats_by_condition[condition] = {
            "total": len(completed),
            "voted": len(voted),
            "changed": len(changed),
            "change_rate": len(changed) / len(voted) if voted else 0,
            "vote_distribution": dict(vote_counts),
        }

        total_voted += len(voted)
        total_changed += len(changed)

    # simple_voting has no final vote
    simple_voting = get_by_conditions(participants, ["simple_voting"])
    simple_voting_completed = [p for p in simple_voting if p.status == "complete"]
    stats_by_condition["simple_voting"] = {
        "total": len(simple_voting_completed),
        "voted": 0,
        "changed": 0,
        "change_rate": 0,
        "vote_distribution": {},
        "note": "simple_voting condition has no final vote",
    }

    logger.info(
        f"Phase 8: Final vote complete. {total_voted} voted, "
        f"{total_changed} changed position"
    )

    return {
        "phase": 8,
        "total_voted": total_voted,
        "total_changed": total_changed,
        "overall_change_rate": total_changed / total_voted if total_voted else 0,
        "by_condition": stats_by_condition,
    }
