"""Opposition selection algorithms.

To add a new strategy:
1. Create a function with signature: (participant, all_participants, config) -> str
2. Add it to the STRATEGIES dict at the bottom of this file
"""

import logging
from collections import Counter

import numpy as np

from .llm import call_llm
from .participants import Participant

logger = logging.getLogger(__name__)


def select_opposition(
    participant: Participant, all_participants: list[Participant], config: dict
) -> str:
    """Select opposing view for a participant.

    Args:
        participant: The participant needing an opposing view
        all_participants: All participants in the experiment
        config: Experiment config with 'opposition_method'

    Returns:
        The opposing option/view to present
    """
    method = config.get("opposition_method", "highest_voted")

    if method not in STRATEGIES:
        raise ValueError(
            f"Unknown opposition method: {method}. "
            f"Available: {list(STRATEGIES.keys())}"
        )

    return STRATEGIES[method](participant, all_participants, config)


def _highest_voted(
    participant: Participant, all_participants: list[Participant], config: dict
) -> str:
    """Select the highest-voted option that differs from participant's choice.

    If participant chose the most popular option, uses second-most popular.
    """
    # Count votes from completed participants
    votes = Counter()
    for p in all_participants:
        if p.status == "complete" and p.initial_choice:
            votes[p.initial_choice] += 1

    # Get options sorted by vote count (descending)
    sorted_options = votes.most_common()

    # Find highest-voted option that's not the participant's choice
    for option, count in sorted_options:
        if option != participant.initial_choice:
            return option

    # Fallback: return any option that's not the participant's choice
    topic_options = config.get("topic", {}).get("options", [])
    for opt in topic_options:
        if opt != participant.initial_choice:
            return opt

    # Last resort: return the participant's own choice (shouldn't happen)
    logger.warning(f"Could not find opposing view for {participant.participant_id}")
    return participant.initial_choice


def _embedding(
    participant: Participant, all_participants: list[Participant], config: dict
) -> str:
    """Select opposition based on embedding distance.

    Finds the participant whose explanation is most distant from this participant's,
    then returns that participant's chosen option.
    """
    try:
        from openai import OpenAI
        from .llm import API_KEY

        client = OpenAI(api_key=API_KEY)
    except ImportError:
        logger.warning("OpenAI not available for embeddings, falling back to highest_voted")
        return _highest_voted(participant, all_participants, config)

    # Get embeddings for all explanations
    explanations = []
    participants_with_explanations = []

    for p in all_participants:
        if p.status == "complete" and p.initial_explanation and p != participant:
            explanations.append(p.initial_explanation)
            participants_with_explanations.append(p)

    if not explanations:
        logger.warning("No explanations available, falling back to highest_voted")
        return _highest_voted(participant, all_participants, config)

    # Add participant's explanation first
    all_texts = [participant.initial_explanation] + explanations

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=all_texts,
        )
        embeddings = [e.embedding for e in response.data]
    except Exception as e:
        logger.warning(f"Embedding API failed: {e}, falling back to highest_voted")
        return _highest_voted(participant, all_participants, config)

    # Calculate cosine distances from participant's explanation
    participant_emb = np.array(embeddings[0])
    other_embs = np.array(embeddings[1:])

    # Cosine similarity
    norms = np.linalg.norm(other_embs, axis=1) * np.linalg.norm(participant_emb)
    similarities = np.dot(other_embs, participant_emb) / norms

    # Find most distant (lowest similarity)
    most_distant_idx = np.argmin(similarities)
    opposing_participant = participants_with_explanations[most_distant_idx]

    return opposing_participant.initial_choice


def _llm_judge(
    participant: Participant, all_participants: list[Participant], config: dict
) -> str:
    """Use LLM to identify the most opposed position."""
    # Collect sample of other positions
    other_positions = []
    for p in all_participants:
        if (
            p.status == "complete"
            and p.initial_choice
            and p.initial_choice != participant.initial_choice
        ):
            other_positions.append(
                f"Option: {p.initial_choice}\nReasoning: {p.initial_explanation}"
            )
        if len(other_positions) >= 10:  # Limit sample size
            break

    if not other_positions:
        return _highest_voted(participant, all_participants, config)

    topic = config.get("topic", {})
    options = topic.get("options", [])

    prompt = f"""You are analyzing positions in a decision-making exercise.

Topic: {topic.get('description', '')}

Options available: {', '.join(options)}

The participant chose: "{participant.initial_choice}"
Their reasoning: "{participant.initial_explanation}"

Here are some other participants' positions:

{chr(10).join(f"Position {i+1}:{chr(10)}{pos}" for i, pos in enumerate(other_positions))}

Which option represents the MOST OPPOSED viewpoint to the participant's position?
Consider both the choice itself and the underlying values/reasoning.

Respond with ONLY the exact option text, nothing else."""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages, config)

    if response is None:
        return _highest_voted(participant, all_participants, config)

    response = response.strip()

    # Validate response is a valid option
    if response in options:
        return response

    # Try to match
    for opt in options:
        if opt.lower() in response.lower() or response.lower() in opt.lower():
            return opt

    # Fallback
    return _highest_voted(participant, all_participants, config)


def _predefined(
    participant: Participant, all_participants: list[Participant], config: dict
) -> str:
    """Use predefined opposition mapping from config."""
    mapping = config.get("opposition_mapping", {})

    if participant.initial_choice in mapping:
        return mapping[participant.initial_choice]

    # Fallback if mapping incomplete
    logger.warning(
        f"No predefined opposition for '{participant.initial_choice}', "
        "falling back to highest_voted"
    )
    return _highest_voted(participant, all_participants, config)


def _cluster_embedding(
    participant: Participant,
    all_participants: list[Participant],
    config: dict,
    clusters_by_option: dict | None = None,
) -> str:
    """Select opposition based on cluster embedding distance.

    Computes option-level embeddings (weighted mean of cluster embeddings)
    and finds the option most distant from the participant's individual embedding.

    Args:
        participant: The participant needing an opposing view
        all_participants: All participants in the experiment
        config: Experiment config
        clusters_by_option: Dict mapping option -> list of ClusterInfo
            (passed via config['_clusters_by_option'] if not provided)

    Returns:
        The opposing option with greatest semantic distance
    """
    # Get clusters from config if not passed directly
    if clusters_by_option is None:
        clusters_by_option = config.get("_clusters_by_option", {})

    if not clusters_by_option:
        logger.warning("No cluster data available, falling back to highest_voted")
        return _highest_voted(participant, all_participants, config)

    # Check if participant has individual embedding
    if participant.individual_summary_embedding is None:
        logger.warning(
            f"No embedding for {participant.participant_id}, falling back to highest_voted"
        )
        return _highest_voted(participant, all_participants, config)

    topic = config.get("topic", {})
    options = topic.get("options", [])

    # Compute option-level embeddings (weighted mean of cluster embeddings)
    option_embeddings = {}

    for option in options:
        clusters = clusters_by_option.get(option, [])
        if not clusters:
            continue

        # Get cluster embeddings and weights
        cluster_embs = []
        weights = []

        for cluster in clusters:
            if cluster.embedding:
                cluster_embs.append(cluster.embedding)
                weights.append(cluster.member_count)

        if not cluster_embs:
            continue

        # Compute weighted mean
        total_weight = sum(weights)
        if total_weight == 0:
            continue

        normalized_weights = [w / total_weight for w in weights]
        weighted_mean = np.zeros(len(cluster_embs[0]))
        for emb, weight in zip(cluster_embs, normalized_weights):
            weighted_mean += np.array(emb) * weight

        option_embeddings[option] = weighted_mean

    if not option_embeddings:
        logger.warning("No valid option embeddings, falling back to highest_voted")
        return _highest_voted(participant, all_participants, config)

    # Calculate distance from participant to each option
    participant_emb = np.array(participant.individual_summary_embedding)
    participant_norm = np.linalg.norm(participant_emb)

    if participant_norm == 0:
        logger.warning(
            f"Zero norm embedding for {participant.participant_id}, falling back to highest_voted"
        )
        return _highest_voted(participant, all_participants, config)

    max_distance = -1
    furthest_option = None

    for option, opt_emb in option_embeddings.items():
        # Skip participant's own choice
        if option == participant.initial_choice:
            continue

        # Cosine distance
        opt_norm = np.linalg.norm(opt_emb)
        if opt_norm == 0:
            continue

        similarity = np.dot(participant_emb, opt_emb) / (participant_norm * opt_norm)
        distance = 1.0 - similarity

        if distance > max_distance:
            max_distance = distance
            furthest_option = option

    if furthest_option is None:
        logger.warning(
            f"Could not find distant option for {participant.participant_id}, "
            "falling back to highest_voted"
        )
        return _highest_voted(participant, all_participants, config)

    logger.debug(
        f"Selected opposition '{furthest_option}' for {participant.participant_id} "
        f"(distance: {max_distance:.3f})"
    )
    return furthest_option


# Strategy dispatch dictionary
# To add a new strategy, add it here
STRATEGIES = {
    "highest_voted": _highest_voted,
    "embedding": _embedding,
    "llm_judge": _llm_judge,
    "predefined": _predefined,
    "cluster_embedding": _cluster_embedding,
}
