"""Simulated participant LLM logic."""

import json
import logging

from .llm import call_llm
from .participants import Participant

logger = logging.getLogger(__name__)


def _build_system_prompt(participant: Participant, topic: dict) -> str:
    """Build system prompt for participant simulation."""
    return f"""You are {participant.enriched_persona}

You are participating in a decision-making exercise about the following topic:

{topic['description']}

Available options:
{chr(10).join(f'- {opt}' for opt in topic['options'])}

Respond authentically based on your background, values, and experiences. Stay in character throughout."""


def make_initial_vote(
    participant: Participant, topic: dict, config: dict
) -> str | None:
    """Have participant make initial choice (without explanation).

    Args:
        participant: The participant making the vote
        topic: Topic dict with 'description' and 'options'
        config: Experiment config

    Returns:
        Chosen option string or None if failed
    """
    system_prompt = _build_system_prompt(participant, topic)
    options_list = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(topic["options"]))

    user_prompt = f"""Please make your choice from the following options.

Options:
{options_list}

Respond with ONLY the exact text of your chosen option, nothing else."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = call_llm(messages, config)
    if response is None:
        return None

    choice = response.strip()

    # Validate choice is one of the options
    if choice not in topic["options"]:
        # Try to match partially
        for opt in topic["options"]:
            if opt.lower() in choice.lower() or choice.lower() in opt.lower():
                return opt
        logger.warning(f"Invalid choice '{choice}', defaulting to first option")
        return topic["options"][0]

    return choice


def respond_to_question(
    participant: Participant,
    question: str,
    transcript: list[dict],
    topic: dict,
    config: dict,
) -> str | None:
    """Have participant respond to a clarifying question.

    Args:
        participant: The participant
        question: The moderator's question
        transcript: Previous exchanges in this conversation
        topic: Topic dict
        config: Experiment config

    Returns:
        Response string or None if failed
    """
    system_prompt = _build_system_prompt(participant, topic)
    system_prompt += f"""

You previously chose "{participant.initial_choice}".

A moderator is asking you clarifying questions to better understand your position and reasoning."""

    messages = [{"role": "system", "content": system_prompt}]

    # Add transcript history
    for entry in transcript:
        role = "assistant" if entry["role"] == "participant" else "user"
        messages.append({"role": role, "content": entry["content"]})

    # Add current question
    messages.append({"role": "user", "content": question})

    response = call_llm(messages, config)
    return response


def respond_to_challenge(
    participant: Participant,
    challenge: str,
    transcript: list[dict],
    topic: dict,
    config: dict,
) -> str | None:
    """Have participant respond to an adversarial challenge.

    Args:
        participant: The participant
        challenge: The moderator's challenge/question
        transcript: Previous exchanges in this adversarial dialogue
        topic: Topic dict
        config: Experiment config

    Returns:
        Response string or None if failed
    """
    system_prompt = _build_system_prompt(participant, topic)
    system_prompt += f"""

You previously chose "{participant.initial_choice}".

A moderator is presenting you with opposing viewpoints and challenging your reasoning using Socratic questioning. Engage thoughtfully with their arguments while staying true to your perspective and values. You may change your mind if convinced, but don't feel obligated to."""

    messages = [{"role": "system", "content": system_prompt}]

    # Add transcript history
    for entry in transcript:
        role = "assistant" if entry["role"] == "participant" else "user"
        messages.append({"role": role, "content": entry["content"]})

    # Add current challenge
    messages.append({"role": "user", "content": challenge})

    response = call_llm(messages, config)
    return response


def make_final_vote_after_summary(
    participant: Participant, summary: str, topic: dict, config: dict
) -> str | None:
    """Have participant make final choice after seeing summary of arguments.

    Args:
        participant: The participant
        summary: Summary of arguments for all options
        topic: Topic dict
        config: Experiment config

    Returns:
        Final choice string or None if failed
    """
    system_prompt = _build_system_prompt(participant, topic)
    system_prompt += f"""

You previously chose "{participant.initial_choice}".

You have now been shown a summary of positions from other participants."""

    user_prompt = f"""{summary}

Now, please make your final choice. You may stick with your original choice or change to a different option based on what you've read.

Respond with ONLY the exact text of your chosen option, nothing else."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = call_llm(messages, config)
    if response is None:
        return None

    choice = response.strip()

    # Validate choice
    if choice not in topic["options"]:
        for opt in topic["options"]:
            if opt.lower() in choice.lower() or choice.lower() in opt.lower():
                return opt
        logger.warning(f"Invalid final choice '{choice}', keeping original")
        return participant.initial_choice

    return choice


def make_final_vote_after_dialogue(
    participant: Participant, transcript: list[dict], topic: dict, config: dict
) -> str | None:
    """Have participant make final choice after adversarial dialogue.

    Args:
        participant: The participant
        transcript: The adversarial dialogue transcript
        topic: Topic dict
        config: Experiment config

    Returns:
        Final choice string or None if failed
    """
    system_prompt = _build_system_prompt(participant, topic)
    system_prompt += f"""

You previously chose "{participant.initial_choice}".

You have just completed a dialogue where a moderator challenged your position with opposing viewpoints."""

    # Build dialogue summary
    dialogue_text = "\n".join(
        f"{'Moderator' if e['role'] == 'moderator' else 'You'}: {e['content']}"
        for e in transcript
    )

    user_prompt = f"""You just had the following dialogue:

{dialogue_text}

Now, please make your final choice. You may stick with your original choice or change to a different option based on the discussion.

Respond with ONLY the exact text of your chosen option, nothing else."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    response = call_llm(messages, config)
    if response is None:
        return None

    choice = response.strip()

    # Validate choice
    if choice not in topic["options"]:
        for opt in topic["options"]:
            if opt.lower() in choice.lower() or choice.lower() in opt.lower():
                return opt
        logger.warning(f"Invalid final choice '{choice}', keeping original")
        return participant.initial_choice

    return choice
