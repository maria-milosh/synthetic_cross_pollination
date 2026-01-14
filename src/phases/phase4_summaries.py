"""Phase 4: Generate Summaries - Extract individual summaries and cluster positions."""

import logging
from collections import defaultdict

from ..participants import Participant, get_by_conditions
from ..summarizer import extract_individual_summary, generate_cluster_description
from ..embeddings import get_embeddings
from ..clustering import (
    cluster_embeddings,
    get_cluster_members,
    ClusterInfo,
)

logger = logging.getLogger(__name__)


def run(participants: list[Participant], config: dict, **kwargs) -> dict:
    """Run Phase 4: Generate Summaries with Clustering.

    This phase:
    1. Extracts individual summaries from clarification transcripts
    2. Calculates embeddings for individual summaries
    3. Clusters participants by voting option
    4. Generates cluster descriptions
    5. Calculates embeddings for cluster descriptions

    Args:
        participants: All participants
        config: Experiment config

    Returns:
        Dict with clusters, clusters_by_option, and phase info
    """
    topic = config.get("topic", {})
    options = topic.get("options", [])
    max_clusters = config.get("max_clusters_per_option", 6)
    algorithm = config.get("clustering_algorithm", "kmeans")

    # Get clarified participants (clarified_passive + acp)
    clarified = get_by_conditions(participants, ["clarified_passive", "acp"])
    clarified = [p for p in clarified if p.status == "complete"]

    logger.info(f"Phase 4: Processing {len(clarified)} clarified participants")

    if not clarified:
        logger.warning("Phase 4: No clarified participants to process")
        return {
            "phase": 4,
            "participants_summarized": 0,
            "clusters": [],
            "clusters_by_option": {},
        }

    # Step 1: Extract individual summaries
    logger.info("Phase 4: Step 1 - Extracting individual summaries")
    summaries_extracted = 0
    for participant in clarified:
        summary = extract_individual_summary(participant, config)
        if summary:
            participant.individual_summary = summary
            summaries_extracted += 1
        else:
            logger.warning(
                f"Phase 4: Failed to extract summary for {participant.participant_id}"
            )

    logger.info(f"Phase 4: Extracted {summaries_extracted} individual summaries")

    # Get participants with valid summaries
    participants_with_summaries = [
        p for p in clarified if p.individual_summary is not None
    ]

    if not participants_with_summaries:
        logger.warning("Phase 4: No valid individual summaries extracted")
        return {
            "phase": 4,
            "participants_summarized": 0,
            "clusters": [],
            "clusters_by_option": {},
        }

    # Step 2: Calculate embeddings for individual summaries
    logger.info("Phase 4: Step 2 - Calculating individual summary embeddings")
    summaries = [p.individual_summary for p in participants_with_summaries]

    try:
        individual_embeddings = get_embeddings(summaries, config)
        for i, participant in enumerate(participants_with_summaries):
            participant.individual_summary_embedding = individual_embeddings[i]
        logger.info(f"Phase 4: Calculated {len(individual_embeddings)} embeddings")
    except RuntimeError as e:
        logger.error(f"Phase 4: Failed to calculate embeddings: {e}")
        return {
            "phase": 4,
            "participants_summarized": summaries_extracted,
            "clusters": [],
            "clusters_by_option": {},
            "error": str(e),
        }

    # Step 3: Cluster by option
    logger.info("Phase 4: Step 3 - Clustering participants by option")

    # Group participants by their initial choice
    participants_by_option = defaultdict(list)
    for p in participants_with_summaries:
        participants_by_option[p.initial_choice].append(p)

    all_clusters = []
    clusters_by_option = {}

    for option in options:
        option_participants = participants_by_option.get(option, [])
        if not option_participants:
            clusters_by_option[option] = []
            continue

        logger.info(
            f"Phase 4: Clustering {len(option_participants)} participants for '{option}'"
        )

        # Get embeddings for this option's participants
        option_embeddings = [
            p.individual_summary_embedding for p in option_participants
        ]
        option_ids = [p.participant_id for p in option_participants]

        # Cluster
        labels = cluster_embeddings(
            option_embeddings,
            max_clusters=max_clusters,
            algorithm=algorithm,
        )

        # Group by cluster
        cluster_members = get_cluster_members(labels, option_ids)

        # Assign cluster IDs to participants
        for label, member_ids in cluster_members.items():
            cluster_id = f"{option}_cluster_{label}"
            for p in option_participants:
                if p.participant_id in member_ids:
                    p.cluster_id = cluster_id

        # Create cluster info objects
        option_clusters = []
        for label, member_ids in cluster_members.items():
            cluster_id = f"{option}_cluster_{label}"

            # Get individual summaries for this cluster
            cluster_summaries = [
                p.individual_summary
                for p in option_participants
                if p.participant_id in member_ids
            ]

            # Generate cluster description
            description = generate_cluster_description(cluster_summaries, option, config)
            if not description:
                description = f"Participants who chose {option}."

            cluster_info = ClusterInfo(
                cluster_id=cluster_id,
                option=option,
                description=description,
                member_count=len(member_ids),
                member_ids=member_ids,
            )
            option_clusters.append(cluster_info)

        clusters_by_option[option] = option_clusters
        all_clusters.extend(option_clusters)

        logger.info(f"Phase 4: Created {len(option_clusters)} clusters for '{option}'")

    # Step 4: Calculate cluster description embeddings
    logger.info("Phase 4: Step 4 - Calculating cluster description embeddings")

    if all_clusters:
        cluster_descriptions = [c.description for c in all_clusters]
        try:
            cluster_embeddings_list = get_embeddings(cluster_descriptions, config)
            for i, cluster in enumerate(all_clusters):
                cluster.embedding = cluster_embeddings_list[i]
            logger.info(
                f"Phase 4: Calculated embeddings for {len(all_clusters)} clusters"
            )
        except RuntimeError as e:
            logger.error(f"Phase 4: Failed to calculate cluster embeddings: {e}")

    logger.info(
        f"Phase 4: Complete. {summaries_extracted} summaries, "
        f"{len(all_clusters)} clusters across {len(options)} options"
    )

    return {
        "phase": 4,
        "participants_summarized": summaries_extracted,
        "clusters": all_clusters,
        "clusters_by_option": clusters_by_option,
    }
