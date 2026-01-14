"""Phase 9: Save Results - Write all data to output files."""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

from ..participants import Participant, to_dict, get_by_condition, get_by_status
from ..clustering import ClusterInfo

logger = logging.getLogger(__name__)


def run(
    participants: list[Participant],
    config: dict,
    output_dir: str,
    clusters: list | None = None,
    terminated_early: bool = False,
    termination_reason: str | None = None,
    **kwargs,
) -> dict:
    """Run Phase 9: Save Results.

    Save config, participants, cluster embeddings, individual embeddings,
    and summary statistics to output directory.

    Args:
        participants: All participants
        config: Experiment config
        output_dir: Path to output directory
        clusters: List of ClusterInfo objects from Phase 4
        terminated_early: Whether experiment terminated early
        termination_reason: Reason for early termination

    Returns:
        Dict with file paths
    """
    output_path = Path(output_dir)

    logger.info(f"Phase 9: Saving results to {output_path}")

    # Save config
    config_path = output_path / "config.yaml"
    # Remove internal keys before saving
    config_to_save = {k: v for k, v in config.items() if not k.startswith("_")}
    with open(config_path, "w") as f:
        yaml.dump(config_to_save, f, default_flow_style=False)
    logger.info(f"Phase 9: Saved config to {config_path}")

    # Save participants
    participants_path = output_path / "participants.json"
    participants_data = {
        "pilot_id": config["pilot_id"],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "participants": [to_dict(p) for p in participants],
    }
    with open(participants_path, "w") as f:
        json.dump(participants_data, f, indent=2)
    logger.info(f"Phase 9: Saved {len(participants)} participants to {participants_path}")

    # Save cluster embeddings
    if clusters:
        clusters_path = output_path / "cluster_embeddings.json"
        clusters_data = {
            "pilot_id": config["pilot_id"],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "clusters": [
                c.to_dict() if hasattr(c, "to_dict") else _cluster_to_dict(c)
                for c in clusters
            ],
        }
        with open(clusters_path, "w") as f:
            json.dump(clusters_data, f, indent=2)
        logger.info(f"Phase 9: Saved {len(clusters)} clusters to {clusters_path}")
    else:
        clusters_path = None

    # Save individual embeddings
    individual_embeddings = [
        {
            "participant_id": p.participant_id,
            "embedding": p.individual_summary_embedding,
        }
        for p in participants
        if p.individual_summary_embedding is not None
    ]

    if individual_embeddings:
        embeddings_path = output_path / "individual_embeddings.json"
        embeddings_data = {
            "pilot_id": config["pilot_id"],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "embeddings": individual_embeddings,
        }
        with open(embeddings_path, "w") as f:
            json.dump(embeddings_data, f, indent=2)
        logger.info(
            f"Phase 9: Saved {len(individual_embeddings)} individual embeddings "
            f"to {embeddings_path}"
        )
    else:
        embeddings_path = None

    # Calculate and save summary statistics
    summary = _calculate_summary(
        participants, config, terminated_early, termination_reason
    )
    summary_path = output_path / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Phase 9: Saved summary to {summary_path}")

    return {
        "phase": 9,
        "config_path": str(config_path),
        "participants_path": str(participants_path),
        "clusters_path": str(clusters_path) if clusters_path else None,
        "embeddings_path": str(embeddings_path) if embeddings_path else None,
        "summary_path": str(summary_path),
    }


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


def _calculate_summary(
    participants: list[Participant],
    config: dict,
    terminated_early: bool,
    termination_reason: str | None,
) -> dict:
    """Calculate summary statistics."""
    conditions = ["simple_voting", "simple_passive", "clarified_passive", "acp"]

    summary = {
        "pilot_id": config["pilot_id"],
        "terminated_early": terminated_early,
        "termination_reason": termination_reason,
        "total_participants": len(participants),
        "by_condition": {},
    }

    for condition in conditions:
        group = get_by_condition(participants, condition)
        completed = [p for p in group if p.status == "complete"]
        failed = [p for p in group if p.status == "failed"]

        # Initial vote distribution
        initial_votes = Counter(p.initial_choice for p in completed if p.initial_choice)

        condition_summary = {
            "total": len(group),
            "completed": len(completed),
            "failed": len(failed),
            "initial_vote_distribution": dict(initial_votes),
        }

        # Final vote stats (for conditions with final votes)
        if condition != "simple_voting":
            final_votes = Counter(p.final_choice for p in completed if p.final_choice)
            changed = sum(1 for p in completed if p.position_changed)

            condition_summary["final_vote_distribution"] = dict(final_votes)
            condition_summary["position_changed"] = changed
            condition_summary["position_changed_rate"] = (
                changed / len(completed) if completed else 0
            )
        else:
            condition_summary["position_changed"] = None
            condition_summary["final_vote_distribution"] = None

        summary["by_condition"][condition] = condition_summary

    return summary
