"""LLM API wrapper with throttling and retry logic."""

import logging
import os
import re
import time

from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

# API key mapping
_API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "maria": "MARIA_API_KEY",
}

_api_key = None
_client = None


def set_api_key(key_name: str) -> None:
    """Set which API key to use.

    Args:
        key_name: Either 'openai' or 'maria' (case-insensitive)

    Raises:
        ValueError: If key_name is not recognized or env var is not set
    """
    global _api_key, _client

    key_name_lower = key_name.lower()
    if key_name_lower not in _API_KEY_ENV_VARS:
        raise ValueError(f"Unknown API key: {key_name}. Must be one of: {list(_API_KEY_ENV_VARS.keys())}")

    env_var = _API_KEY_ENV_VARS[key_name_lower]
    _api_key = os.environ.get(env_var)

    if not _api_key:
        raise ValueError(f"Environment variable {env_var} is not set")

    # Reset client so it gets recreated with new key
    _client = None
    logger.info(f"Using API key: {key_name}")


def _get_client() -> OpenAI:
    """Get or create OpenAI client singleton."""
    global _client
    if _client is None:
        if _api_key is None:
            set_api_key("openai")  # Default to openai if not set
        _client = OpenAI(api_key=_api_key)
    return _client


def _parse_retry_after(error: RateLimitError) -> float | None:
    """Parse wait time from rate limit error.

    Looks for Retry-After header or "Please retry after X seconds" in message.

    Args:
        error: The RateLimitError from OpenAI

    Returns:
        Wait time in seconds, or None if not parseable
    """
    # Try to get from response headers
    if hasattr(error, "response") and error.response is not None:
        retry_after = error.response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

    # Try to parse from error message (e.g., "Please retry after 20 seconds")
    error_str = str(error)
    match = re.search(r"retry after (\d+(?:\.\d+)?)\s*(?:seconds?)?", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Try to parse "Please try again in Xms" format
    match = re.search(r"try again in (\d+(?:\.\d+)?)\s*ms", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 1000.0

    # Try to parse "Please try again in Xs" format
    match = re.search(r"try again in (\d+(?:\.\d+)?)\s*s(?:econds?)?", error_str, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return None


def _is_quota_exceeded(error: RateLimitError) -> bool:
    """Check if error is quota exceeded (billing issue) vs rate limit.

    Args:
        error: The RateLimitError from OpenAI

    Returns:
        True if this is a quota exceeded error, False if regular rate limit
    """
    error_str = str(error).lower()
    return "insufficient_quota" in error_str or "quota" in error_str


def call_llm(messages: list[dict], config: dict) -> str | None:
    """Make an OpenAI API call with throttling and retry logic.

    Handles rate limit errors with exponential backoff and Retry-After header parsing.
    For quota exceeded errors, retries once with a 60s wait before failing.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        config: Config dict containing 'model', 'api_sleep_seconds', 'max_api_retries',
                and 'api_retry_base_seconds'

    Returns:
        Response content string, or None if the call failed
    """
    client = _get_client()
    model = config.get("model", "gpt-4o")
    sleep_seconds = config.get("api_sleep_seconds", 3)
    max_retries = config.get("max_api_retries", 5)
    base_wait = config.get("api_retry_base_seconds", 2)
    quota_wait = 60  # Wait time for quota exceeded errors

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            content = response.choices[0].message.content

            # Throttle after successful call
            time.sleep(sleep_seconds)

            return content

        except RateLimitError as e:
            is_quota = _is_quota_exceeded(e)

            if is_quota:
                # Quota exceeded: retry once with longer wait
                if attempt == 0:
                    logger.warning(
                        f"Quota exceeded. Waiting {quota_wait}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(quota_wait)
                else:
                    logger.error(
                        f"Quota exceeded after retry. Check billing at "
                        "https://platform.openai.com/account/billing"
                    )
                    return None
            else:
                # Regular rate limit: exponential backoff with Retry-After
                if attempt < max_retries - 1:
                    parsed_wait = _parse_retry_after(e)
                    wait_time = parsed_wait if parsed_wait else (base_wait * (2 ** attempt))

                    logger.warning(
                        f"Rate limited. Waiting {wait_time:.1f}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries exceeded after rate limiting: {e}")
                    return None

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    return None
