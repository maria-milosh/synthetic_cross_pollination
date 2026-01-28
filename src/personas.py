"""Persona fetching and enrichment."""

import json, logging, random, requests

from .llm import call_llm

logger = logging.getLogger(__name__)

PERSONA_HUB_URL = "https://raw.githubusercontent.com/tencent-ailab/persona-hub/refs/heads/main/data/persona.jsonl"

INCOME_WEIGHTS = {"Low income": 0.30, "Middle income": 0.50, "High income": 0.20}
LOCATION_WEIGHTS = {"urban": 0.25, "suburban": 0.43, "rural": 0.30}
AGE_BUCKET_WEIGHTS = {
  "18-25": 0.20,
  "26-35": 0.23,
  "36-45": 0.21,
  "46-55": 0.19,
  "56-65": 0.17,
}
RACE_WEIGHTS = {
  "White (non-Hispanic)": 0.575,
  "Hispanic or Latino": 0.200,
  "Black or African American": 0.110,
  "Asian": 0.060,
  "Native American or Alaska Native": 0.012,
  "Native Hawaiian or Other Pacific Islander": 0.003,
  "Two or more races": 0.040,
}
EDU_WEIGHTS = {
  "Primary and secondary without high school diploma": 0.10,
  "High school": 0.30,
  "Some college": 0.28,
  "Bachelor's degree": 0.20,
  "Master's degree": 0.10,
  "Doctorate": 0.02,
}
IDEOLOGY_WEIGHTS = {
  "very liberal": 0.08,
  "liberal": 0.17,
  "moderate": 0.34,
  "conservative": 0.25,
  "very conservative": 0.12,
}

def weighted_choice(rng: random.Random, weights: dict[str, float]) -> str:
    items = list(weights.keys())
    w = list(weights.values())
    return rng.choices(items, weights=w, k=1)[0]

def generate_demographics_weighted(rng: random.Random) -> dict:
    return {
        "age_bucket": weighted_choice(rng, AGE_BUCKET_WEIGHTS),
        "sex": rng.choices(["M", "F"], weights=[0.495, 0.505], k=1)[0],
        "race": weighted_choice(rng, RACE_WEIGHTS),
        "education": weighted_choice(rng, EDU_WEIGHTS),
        "income": weighted_choice(rng, INCOME_WEIGHTS),
        "location_type": weighted_choice(rng, LOCATION_WEIGHTS),
        "political_leaning": weighted_choice(rng, IDEOLOGY_WEIGHTS),
    }


def fetch_personas(n: int, seed: int | None = None) -> list[dict]:
    """Fetch and sample personas from persona-hub.

    Args:
        n: Number of personas to sample
        seed: Random seed for reproducibility

    Returns:
        List of persona dictionaries with 'persona' key
    """
    # if seed is not None:
    #     random.seed(seed)
    rng = random.Random(seed)
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
    
    return rng.sample(personas, n)


def _is_likely_english(text: str) -> bool:
    """Simple heuristic to check if text is likely English."""
    # Check for ASCII characters being dominant
    ascii_count = sum(1 for c in text if ord(c) < 128)
    if len(text) == 0:
        return False
    return ascii_count / len(text) > 0.9

# def generate_demographics(base_persona: str, config: dict) -> dict:
#     """Generate coherent demographics for a persona using LLM.
#     Args:
#         base_persona: The base persona description
#         config: Config dict for LLM calls
#     Returns:
#         Demographics dictionary with age, sex, education, income, location_type, political_leaning
#     """
#     prompt = f"""Given this persona description, generate realistic demographics that would make sense for this person.
#     Persona: {base_persona}
#     Demographics:
#     - Age: {demographics['age']}
#     - Sex: {demographics['sex']}
#     - Race: {demographics['race']}
#     - Education: {demographics['education']}
#     - Income: {demographics['income']}
#     - Location type: {demographics['location_type']}
#     - Political leaning: {demographics['political_leaning']}
#     Return ONLY a JSON object with the same keys.
#     The demographics should reasonably flow from the persona description."""
#     messages = [{"role": "user", "content": prompt}]
#     response = call_llm(messages, config)
#     if response is None:
#         # Fallback to random demographics if LLM fails
#         logger.warning("LLM call failed for demographics, using random fallback")
#         return _random_demographics()
#     try:
#         # Clean response of markdown if present
#         cleaned = response.strip()
#         if cleaned.startswith("```"):
#             cleaned = cleaned.split("```")[1]
#             if cleaned.startswith("json"):
#                 cleaned = cleaned[4:]
#         cleaned = cleaned.strip()
#         demographics = json.loads(cleaned)
#         # Validate and fix if needed
#         return _validate_demographics(demographics)
#     except (json.JSONDecodeError, KeyError) as e:
#         logger.warning(f"Failed to parse demographics response: {e}, using fallback")
#         return _random_demographics()
# def _random_demographics() -> dict:
#     """Generate random demographics as fallback."""
#     return {
#         "age": random.randint(18, 65),
#         "sex": random.choice(["M", "F"]),
#         "education": random.choice(EDUCATION_LEVELS),
#         "income": random.choice(INCOME_LEVELS),
#         "location_type": random.choice(LOCATION_TYPES),
#         "political_leaning": random.choice(POLITICAL_LEANINGS),
#     }
# def _validate_demographics(demographics: dict) -> dict:
#     """Validate and fix demographics dict."""
#     result = {}
#     # Age
#     age = demographics.get("age", random.randint(18, 65))
#     result["age"] = max(18, min(65, int(age)))
#     # Sex
#     sex = demographics.get("sex", random.choice(["M", "F"]))
#     result["sex"] = sex if sex in ["M", "F"] else random.choice(["M", "F"])
#     # Education
#     education = demographics.get("education", "")
#     result["education"] = (
#         education if education in EDUCATION_LEVELS else random.choice(EDUCATION_LEVELS)
#     )
#     # Income
#     income = demographics.get("income", "")
#     result["income"] = income if income in INCOME_LEVELS else random.choice(INCOME_LEVELS)
#     # Location
#     location = demographics.get("location_type", "")
#     result["location_type"] = (
#         location if location in LOCATION_TYPES else random.choice(LOCATION_TYPES)
#     )
#     # Political leaning
#     political = demographics.get("political_leaning", "")
#     result["political_leaning"] = (
#         political if political in POLITICAL_LEANINGS else random.choice(POLITICAL_LEANINGS)
#     )
#     return result


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
    - Age range: {demographics['age_bucket']}
    - Sex: {demographics['sex']}
    - Race/ethnicity: {demographics['race']}
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
            f"{base_persona} This is a {sex_word} in the {demographics['age_bucket']} age range, "
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
    rng = random.Random(config.get("random_seed"))
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

        # demographics = generate_demographics(base, config)
        demographics = generate_demographics_weighted(rng)
        enriched = enrich_persona(base, demographics, config)

        prepared.append(
            {
                "base_persona": base,
                "demographics": demographics,
                "enriched_persona": enriched,
            }
        )

    return prepared
