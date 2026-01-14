"""Phase 2: Threshold Check - Check if any option has majority."""

import logging
from collections import Counter

from ..participants import Participant, get_by_status

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 2: Threshold Check.

    Count votes and check if any option reaches the disagreement threshold.
    Only terminates early if we have at least min_responses_for_threshold votes.

    Args:
        participants: All participants
        config: Experiment config with 'disagreement_threshold' and
                'min_responses_for_threshold' (default 50)

    Returns:
        Dict with 'continue' (bool) and 'vote_counts'
    """
    threshold = config.get("disagreement_threshold", 0.5)
    min_responses = config.get("min_responses_for_threshold", 50)

    # Count votes from completed participants
    completed = get_by_status(participants, "complete")
    votes = Counter(p.initial_choice for p in completed if p.initial_choice)

    total_votes = sum(votes.values())

    logger.info(f"Phase 2: Vote counts from {total_votes} participants:")
    for option, count in votes.most_common():
        pct = count / total_votes * 100 if total_votes > 0 else 0
        logger.info(f"  {option}: {count} ({pct:.1f}%)")

    # Check threshold (only if we have enough responses)
    should_terminate = False
    termination_option = None

    if total_votes < min_responses:
        logger.info(
            f"Phase 2: Only {total_votes} votes, need at least {min_responses} "
            f"before checking threshold. Continuing."
        )
    else:
        for option, count in votes.items():
            proportion = count / total_votes if total_votes > 0 else 0
            if proportion >= threshold:
                should_terminate = True
                termination_option = option
                logger.warning(
                    f"Phase 2: '{option}' has {proportion:.1%} of votes "
                    f"({total_votes} responses), exceeding threshold of {threshold:.1%}. "
                    f"Experiment will terminate."
                )
                break

        if not should_terminate:
            logger.info(
                f"Phase 2: No option exceeds {threshold:.1%} threshold. Continuing."
            )

    return {
        "phase": 2,
        "continue": not should_terminate,
        "vote_counts": dict(votes),
        "total_votes": total_votes,
        "threshold": threshold,
        "termination_option": termination_option,
    }
