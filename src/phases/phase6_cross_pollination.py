"""Phase 6: Cross-Pollination - Show cluster summaries to all exposed groups."""

import logging

from ..participants import Participant, get_by_conditions, mark_failed
from ..simulator import make_final_vote_after_summary
from ..summarizer import format_cross_pollination_content

logger = logging.getLogger(__name__)


def run(
    participants: list[Participant],
    config: dict,
    clusters_by_option: dict | None = None,
    **kwargs
) -> dict:
    """Run Phase 6: Cross-Pollination.

    Show cluster descriptions to simple_passive, clarified_passive, AND acp.
    - Passive groups (simple_passive, clarified_passive) vote after viewing
    - ACP participants view but don't vote yet (vote happens after dialogue in Phase 7)

    Args:
        participants: All participants
        config: Experiment config
        clusters_by_option: Dict mapping option -> list of ClusterInfo from Phase 4

    Returns:
        Dict with status info
    """
    topic = config["topic"]
    options = topic.get("options", [])

    if clusters_by_option is None:
        clusters_by_option = {}

    # Format cross-pollination content
    cross_pollination_content = format_cross_pollination_content(
        clusters_by_option, options, randomize=True
    )

    logger.debug(f"Phase 6: Cross-pollination content:\n{cross_pollination_content}")

    # Process passive groups (they vote after viewing)
    passive_result = _process_passive_groups(
        participants, config, topic, cross_pollination_content
    )

    # Process ACP group (they view but don't vote yet)
    acp_result = _process_acp_group(
        participants, config, cross_pollination_content
    )

    total = passive_result["total"] + acp_result["total"]

    logger.info(
        f"Phase 6: Complete. Passive: {passive_result['succeeded']} voted, "
        f"{passive_result['position_changed']} changed. "
        f"ACP: {acp_result['total']} viewed cross-pollination content."
    )

    return {
        "phase": 6,
        "total": total,
        "passive_total": passive_result["total"],
        "passive_succeeded": passive_result["succeeded"],
        "passive_failed": passive_result["failed"],
        "passive_position_changed": passive_result["position_changed"],
        "acp_total": acp_result["total"],
        "acp_viewed": acp_result["viewed"],
    }


def _process_passive_groups(
    participants: list[Participant],
    config: dict,
    topic: dict,
    content: str,
) -> dict:
    """Process passive groups: show content and get votes.

    Args:
        participants: All participants
        config: Experiment config
        topic: Topic dict
        content: Cross-pollination content string

    Returns:
        Dict with passive group results
    """
    passive = get_by_conditions(participants, ["simple_passive", "clarified_passive"])
    passive = [p for p in passive if p.status == "complete"]

    total = len(passive)
    succeeded = 0
    failed = 0
    changed = 0

    logger.info(f"Phase 6: Getting final votes from {total} passive participants")

    for i, participant in enumerate(passive):
        logger.info(f"Phase 6: Processing passive participant {i + 1}/{total}")

        final_choice = make_final_vote_after_summary(
            participant, content, topic, config
        )

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

    return {
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "position_changed": changed,
    }


def _process_acp_group(
    participants: list[Participant],
    config: dict,
    content: str,
) -> dict:
    """Process ACP group: show content (no voting yet).

    ACP participants view cross-pollination content before their adversarial
    dialogue in Phase 7. They don't vote until after the dialogue.

    Args:
        participants: All participants
        config: Experiment config
        content: Cross-pollination content string

    Returns:
        Dict with ACP group results
    """
    acp = get_by_conditions(participants, ["acp"])
    acp = [p for p in acp if p.status == "complete"]

    total = len(acp)
    viewed = 0

    logger.info(f"Phase 6: Showing cross-pollination to {total} ACP participants")

    for participant in acp:
        participant.cross_pollination_content = content
        viewed += 1

    logger.info(f"Phase 6: {viewed} ACP participants viewed cross-pollination content")

    return {
        "total": total,
        "viewed": viewed,
    }
