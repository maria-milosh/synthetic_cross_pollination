"""Persona fetching and enrichment."""

import json
import logging
import random
import requests

from .llm import call_llm

logger = logging.getLogger(__name__)

PERSONA_HUB_URL = "https://raw.githubusercontent.com/tencent-ailab/persona-hub/refs/heads/main/data/persona.jsonl"

EDUCATION_LEVELS = [
    "Less than high school",
    "High school",
    "Some college",
    "Bachelor's degree",
    "Master's degree",
    "Doctorate",
]

INCOME_LEVELS = [
    "Low income",
    "Lower-middle income",
    "Middle income",
    "Upper-middle income",
    "High income",
]

LOCATION_TYPES = ["urban", "suburban", "rural"]

POLITICAL_LEANINGS = [
    "very liberal",
    "liberal",
    "moderate",
    "conservative",
    "very conservative",
]


def fetch_personas(n: int, seed: int | None = None) -> list[dict]:
    """Fetch and sample personas from persona-hub.

    Args:
        n: Number of personas to sample
        seed: Random seed for reproducibility

    Returns:
        List of persona dictionaries with 'persona' key
    """
    if seed is not None:
        random.seed(seed)

    logger.info(f"Fetching personas from {PERSONA_HUB_URL}")

    response = requests.get(PERSONA_HUB_URL)
    response.raise_for_status()

    # Parse JSONL format
    personas = []
    for line in response.text.strip().split("\n"):
        if line:
            try:
                data = json.loads(line)
                # Filter to English personas (simple heuristic: check for common English words)
                persona_text = data.get("persona", "")
                if _is_likely_english(persona_text):
                    personas.append(data)
            except json.JSONDecodeError:
                continue

    logger.info(f"Found {len(personas)} English personas, sampling {n}")

    if len(personas) < n:
        logger.warning(
            f"Requested {n} personas but only {len(personas)} available. Using all."
        )
        return personas

    return random.sample(personas, n)


def _is_likely_english(text: str) -> bool:
    """Simple heuristic to check if text is likely English."""
    # Check for ASCII characters being dominant
    ascii_count = sum(1 for c in text if ord(c) < 128)
    if len(text) == 0:
        return False
    return ascii_count / len(text) > 0.9


def generate_demographics(base_persona: str, config: dict) -> dict:
    """Generate coherent demographics for a persona using LLM.

    Args:
        base_persona: The base persona description
        config: Config dict for LLM calls

    Returns:
        Demographics dictionary with age, sex, education, income, location_type, political_leaning
    """
    prompt = f"""Given this persona description, generate realistic demographics that would make sense for this person.

Persona: {base_persona}

Respond with ONLY a JSON object (no markdown, no explanation) with these exact keys:
- age: integer between 18 and 65
- sex: "M" or "F"
- education: one of {EDUCATION_LEVELS}
- income: one of {INCOME_LEVELS}
- location_type: one of {LOCATION_TYPES}
- political_leaning: one of {POLITICAL_LEANINGS}

The demographics should reasonably flow from the persona description."""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages, config)

    if response is None:
        # Fallback to random demographics if LLM fails
        logger.warning("LLM call failed for demographics, using random fallback")
        return _random_demographics()

    try:
        # Clean response of markdown if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        demographics = json.loads(cleaned)
        # Validate and fix if needed
        return _validate_demographics(demographics)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to parse demographics response: {e}, using fallback")
        return _random_demographics()


def _random_demographics() -> dict:
    """Generate random demographics as fallback."""
    return {
        "age": random.randint(18, 65),
        "sex": random.choice(["M", "F"]),
        "education": random.choice(EDUCATION_LEVELS),
        "income": random.choice(INCOME_LEVELS),
        "location_type": random.choice(LOCATION_TYPES),
        "political_leaning": random.choice(POLITICAL_LEANINGS),
    }


def _validate_demographics(demographics: dict) -> dict:
    """Validate and fix demographics dict."""
    result = {}

    # Age
    age = demographics.get("age", random.randint(18, 65))
    result["age"] = max(18, min(65, int(age)))

    # Sex
    sex = demographics.get("sex", random.choice(["M", "F"]))
    result["sex"] = sex if sex in ["M", "F"] else random.choice(["M", "F"])

    # Education
    education = demographics.get("education", "")
    result["education"] = (
        education if education in EDUCATION_LEVELS else random.choice(EDUCATION_LEVELS)
    )

    # Income
    income = demographics.get("income", "")
    result["income"] = income if income in INCOME_LEVELS else random.choice(INCOME_LEVELS)

    # Location
    location = demographics.get("location_type", "")
    result["location_type"] = (
        location if location in LOCATION_TYPES else random.choice(LOCATION_TYPES)
    )

    # Political leaning
    political = demographics.get("political_leaning", "")
    result["political_leaning"] = (
        political if political in POLITICAL_LEANINGS else random.choice(POLITICAL_LEANINGS)
    )

    return result


def enrich_persona(base_persona: str, demographics: dict, config: dict) -> str:
    """Create enriched persona description combining base + demographics.

    Args:
        base_persona: The base persona description
        demographics: Demographics dictionary
        config: Config dict for LLM calls

    Returns:
        Full enriched persona description
    """
    prompt = f"""Create a rich, detailed persona description that combines the following base persona with the given demographics. Write it as a cohesive paragraph (2-3 sentences) that a person could use to role-play this character.

Base persona: {base_persona}

Demographics:
- Age: {demographics['age']}
- Sex: {demographics['sex']}
- Education: {demographics['education']}
- Income level: {demographics['income']}
- Location type: {demographics['location_type']}
- Political leaning: {demographics['political_leaning']}

Write ONLY the persona description, no preamble or explanation."""

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages, config)

    if response is None:
        # Fallback to simple concatenation
        sex_word = "man" if demographics["sex"] == "M" else "woman"
        return (
            f"{base_persona} This is a {demographics['age']}-year-old {sex_word} "
            f"with a {demographics['education']}, {demographics['income']} level, "
            f"living in a {demographics['location_type']} area with "
            f"{demographics['political_leaning']} political views."
        )

    return response.strip()


def prepare_personas(config: dict) -> list[dict]:
    """Fetch, enrich, and prepare all personas for the experiment.

    Uses persistent storage by default. Set use_persona_storage: false in config
    to generate fresh personas for each run.

    Args:
        config: Full experiment config

    Returns:
        List of dicts with 'base_persona', 'demographics', 'enriched_persona'
    """
    n = config["participants_per_condition"] * 4  # 4 conditions
    seed = config.get("random_seed")
    use_storage = config.get("use_persona_storage", True)

    if use_storage:
        from .persona_storage import get_personas

        return get_personas(n, config, seed)

    # Legacy behavior: generate fresh personas each time
    raw_personas = fetch_personas(n, seed)
    prepared = []

    for i, persona_data in enumerate(raw_personas):
        base = persona_data.get("persona", "")
        logger.info(f"Enriching persona {i + 1}/{len(raw_personas)}")

        demographics = generate_demographics(base, config)
        enriched = enrich_persona(base, demographics, config)

        prepared.append(
            {
                "base_persona": base,
                "demographics": demographics,
                "enriched_persona": enriched,
            }
        )

    return prepared
