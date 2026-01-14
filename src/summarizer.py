"""Summary generation for individual positions and clusters."""

import logging

from .llm import call_llm
from .participants import Participant

logger = logging.getLogger(__name__)


def extract_individual_summary(
    participant: Participant, config: dict
) -> str | None:
    """Extract individual summary from participant's clarification transcript.

    Args:
        participant: Participant with clarification_transcript
        config: Experiment config

    Returns:
        1-3 sentence summary of participant's position, or None if failed
    """
    if not participant.clarification_transcript:
        logger.warning(
            f"No clarification transcript for {participant.participant_id}"
        )
        return None

    # Build dialogue text focusing on participant's responses
    dialogue_parts = []
    for entry in participant.clarification_transcript:
        role_label = "Moderator" if entry["role"] == "moderator" else "Participant"
        dialogue_parts.append(f"{role_label}: {entry['content']}")
    dialogue_text = "\n\n".join(dialogue_parts)

    prompt = f"""You are analyzing a dialogue between a moderator and a participant about their decision.

The participant chose: "{participant.initial_choice}"

Here is their clarification dialogue:

{dialogue_text}

Summarize the participant's position and key arguments in 1-3 sentences.
Focus ONLY on the participant's stance and reasoning (not the moderator's questions).
Capture the core values, priorities, and reasoning behind their choice.

Respond with ONLY the summary, no other text."""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages, config)

    if response is None:
        logger.warning(
            f"Failed to extract summary for {participant.participant_id}"
        )
        return None

    return response.strip()


def generate_cluster_description(
    individual_summaries: list[str], option: str, config: dict
) -> str | None:
    """Generate cluster description from individual summaries.

    Args:
        individual_summaries: List of individual position summaries in this cluster
        option: The voting option this cluster belongs to
        config: Experiment config

    Returns:
        3-sentence description of the cluster's arguments, or None if failed
    """
    if not individual_summaries:
        return None

    # Format summaries for prompt
    summaries_text = "\n\n".join(
        f"Position {i+1}: {summary}"
        for i, summary in enumerate(individual_summaries[:20])  # Limit input
    )

    prompt = f"""You are analyzing a group of participants who all chose "{option}" in a decision-making exercise.

Here are summaries of their individual positions:

{summaries_text}

These participants share similar reasoning patterns. Create a unified description of this cluster's position in exactly 3 sentences:
1. The core argument or value driving this group's choice
2. The key reasoning or evidence they emphasize
3. What distinguishes this perspective from others who made the same choice

Respond with ONLY the 3-sentence description, no numbering or other text."""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages, config)

    if response is None:
        logger.warning(f"Failed to generate cluster description for {option}")
        return None

    return response.strip()


def format_cross_pollination_content(
    clusters_by_option: dict, options: list[str], randomize: bool = True
) -> str:
    """Format cluster descriptions for cross-pollination display.

    Args:
        clusters_by_option: Dict mapping option -> list of ClusterInfo
        options: List of all voting options
        randomize: Whether to randomize option order (default True)

    Returns:
        Formatted markdown string with cluster descriptions
    """
    import random

    intro = (
        "Here is a summary of the positions that other participants have "
        "expressed on the issue and their key arguments."
    )

    display_options = options.copy()
    if randomize:
        random.shuffle(display_options)

    sections = [intro, ""]

    for option in display_options:
        clusters = clusters_by_option.get(option, [])
        if not clusters:
            continue

        sections.append(f"## {option}")
        sections.append("")

        for i, cluster in enumerate(clusters, 1):
            sections.append(f"Position {i}: {cluster.description}")
            sections.append("")

    return "\n".join(sections)


# Keep legacy function for backwards compatibility during transition
def generate_summary(participants: list[Participant], config: dict) -> str:
    """Generate summary of strongest arguments for each option.

    DEPRECATED: This function is kept for backwards compatibility.
    Use extract_individual_summary + generate_cluster_description instead.

    Args:
        participants: List of participants (typically clarified_passive + acp)
        config: Experiment config

    Returns:
        Formatted summary string
    """
    from collections import defaultdict

    topic = config.get("topic", {})
    options = topic.get("options", [])
    n_arguments = config.get("arguments_per_option", 3)
    include_votes = config.get("include_vote_distribution", False)

    # Group explanations by choice
    explanations_by_option = defaultdict(list)
    vote_counts = defaultdict(int)

    for p in participants:
        if p.status == "complete" and p.initial_choice and p.initial_explanation:
            explanations_by_option[p.initial_choice].append(p.initial_explanation)
            vote_counts[p.initial_choice] += 1

    # Build summary for each option
    summary_parts = []

    for option in options:
        explanations = explanations_by_option.get(option, [])

        if not explanations:
            continue

        # Extract top arguments using LLM
        top_arguments = _extract_arguments(explanations, option, n_arguments, config)

        # Format option section
        section = f"## {option}"
        if include_votes:
            total = sum(vote_counts.values())
            pct = (vote_counts[option] / total * 100) if total > 0 else 0
            section += f" ({vote_counts[option]} votes, {pct:.1f}%)"
        section += "\n"

        if top_arguments:
            for i, arg in enumerate(top_arguments, 1):
                section += f"{i}. {arg}\n"
        else:
            section += "No arguments available.\n"

        summary_parts.append(section)

    if not summary_parts:
        return "No arguments were submitted."

    return "\n".join(summary_parts)


def _extract_arguments(
    explanations: list[str], option: str, n: int, config: dict
) -> list[str]:
    """Extract top N strongest arguments from explanations.

    Args:
        explanations: List of explanation strings for this option
        option: The option these explanations support
        n: Number of arguments to extract
        config: Experiment config

    Returns:
        List of top argument strings
    """
    if not explanations:
        return []

    # If few explanations, just return them
    if len(explanations) <= n:
        return explanations

    # Use LLM to extract strongest arguments
    explanations_text = "\n\n".join(
        f"Argument {i+1}: {exp}" for i, exp in enumerate(explanations[:20])  # Limit input
    )

    prompt = f"""You are analyzing arguments in favor of "{option}" in a decision-making exercise.

Here are the arguments submitted by participants:

{explanations_text}

Identify the {n} STRONGEST and most compelling arguments for choosing "{option}".
For each argument, write a clear, concise summary (1-2 sentences) that captures the key point.

Respond with exactly {n} arguments, one per line, numbered 1-{n}. Do not include any other text."""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages, config)

    if response is None:
        # Fallback: return first n explanations
        return explanations[:n]

    # Parse response
    arguments = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if line:
            # Remove numbering if present
            if line[0].isdigit() and (line[1] == "." or line[1] == ")"):
                line = line[2:].strip()
            elif line[0].isdigit() and line[1].isdigit() and line[2] in ".)":
                line = line[3:].strip()
            if line:
                arguments.append(line)

    return arguments[:n] if arguments else explanations[:n]
