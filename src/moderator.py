"""Moderator LLM logic for clarification and Socratic dialogue."""

import logging

from .llm import call_llm
from .participants import Participant
from .simulator import respond_to_question, respond_to_challenge

logger = logging.getLogger(__name__)


def run_clarification(
    participant: Participant, topic: dict, config: dict
) -> list[dict] | None:
    """Run clarification Q&A between moderator and participant.

    Args:
        participant: The participant to clarify
        topic: Topic dict with description and options
        config: Experiment config

    Returns:
        Transcript as list of {role, content} dicts, or None if failed
    """
    max_exchanges = config.get("max_clarification_exchanges", 5)

    system_prompt = f"""You are a neutral moderator helping understand a participant's position on the following topic:

{topic['description']}

Available options: {', '.join(topic['options'])}

The participant chose "{participant.initial_choice}".

Ask clarifying questions to deeply understand their reasoning. Focus on:
- The values and priorities driving their choice
- How they weighed different considerations
- Their understanding of alternatives

Begin by asking them to explain why they made this choice. When you fully understand their position and the reasoning behind it, respond with exactly "SATISFIED" and nothing else."""

    transcript = []
    messages = [{"role": "system", "content": system_prompt}]

    for exchange in range(max_exchanges):
        # Get moderator's question
        moderator_response = call_llm(messages, config)
        if moderator_response is None:
            logger.error(f"Moderator LLM failed for {participant.participant_id}")
            return None

        moderator_response = moderator_response.strip()

        # Check if satisfied
        if moderator_response.upper() == "SATISFIED":
            logger.info(
                f"Clarification complete for {participant.participant_id} "
                f"after {exchange} exchanges"
            )
            break

        transcript.append({"role": "moderator", "content": moderator_response})
        messages.append({"role": "assistant", "content": moderator_response})

        # Get participant's response
        participant_response = respond_to_question(
            participant, moderator_response, transcript, topic, config
        )
        if participant_response is None:
            logger.error(f"Participant LLM failed for {participant.participant_id}")
            return None

        transcript.append({"role": "participant", "content": participant_response})
        messages.append({"role": "user", "content": participant_response})

    return transcript


def run_adversarial_dialogue(
    participant: Participant, opposition_view: str, topic: dict, config: dict,
    cross_pollination_content: str | None = None
) -> list[dict] | None:
    """Run Socratic adversarial dialogue between moderator and participant.

    Args:
        participant: The participant to challenge
        opposition_view: The opposing view/option to present
        topic: Topic dict with description and options
        config: Experiment config

    Returns:
        Transcript as list of {role, content} dicts, or None if failed
    """
    max_exchanges = config.get("max_socratic_exchanges", 5)

    cross_poll_section = ""
    if cross_pollination_content:
        cross_poll_section = f"""
Before this dialogue, the participant was shown the following summary of perspectives from all groups:

{cross_pollination_content}

"""

    system_prompt = f"""You are a moderator presenting an opposing viewpoint using Socratic questioning.

Topic: {topic['description']}

Available options: {', '.join(topic['options'])}

The participant chose "{participant.initial_choice}".
{cross_poll_section}
Your goal is to help the participant deeply engage with the counterarguments. Present the opposing view: "{opposition_view}".

Challenge the participant's reasoning respectfully but firmly using Socratic questioning:
- Ask probing questions that reveal assumptions
- Present concrete scenarios where the opposing view might be better
- Explore trade-offs they may not have considered
- Push back on weak reasoning while acknowledging valid points
- Reference arguments from other perspectives shown above when relevant

When the participant has thoroughly engaged with the opposing arguments (shown genuine consideration, addressed key counterpoints), respond with exactly "SATISFIED" and nothing else."""

    transcript = []
    messages = [{"role": "system", "content": system_prompt}]

    for exchange in range(max_exchanges):
        # Get moderator's challenge
        moderator_response = call_llm(messages, config)
        if moderator_response is None:
            logger.error(
                f"Moderator LLM failed in adversarial for {participant.participant_id}"
            )
            return None

        moderator_response = moderator_response.strip()

        # Check if satisfied
        if moderator_response.upper() == "SATISFIED":
            logger.info(
                f"Adversarial dialogue complete for {participant.participant_id} "
                f"after {exchange} exchanges"
            )
            break

        transcript.append({"role": "moderator", "content": moderator_response})
        messages.append({"role": "assistant", "content": moderator_response})

        # Get participant's response
        participant_response = respond_to_challenge(
            participant, moderator_response, transcript, topic, config,
            cross_pollination_content=cross_pollination_content
        )
        if participant_response is None:
            logger.error(
                f"Participant LLM failed in adversarial for {participant.participant_id}"
            )
            return None

        transcript.append({"role": "participant", "content": participant_response})
        messages.append({"role": "user", "content": participant_response})

    return transcript
