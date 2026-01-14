"""Embedding generation utilities using OpenAI API."""

import logging
import time

import numpy as np
from openai import RateLimitError

from .llm import _get_client, _parse_retry_after, _is_quota_exceeded

logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_MODEL = "text-embedding-3-small"


def get_embeddings(
    texts: list[str], config: dict, batch_size: int = 100
) -> list[list[float]]:
    """Get embeddings for a list of texts.

    Args:
        texts: List of text strings to embed
        config: Experiment config with optional 'embedding_model',
                'max_api_retries', 'api_retry_base_seconds'
        batch_size: Maximum texts per API call (default 100)

    Returns:
        List of embedding vectors (each is a list of floats)

    Raises:
        RuntimeError: If embedding API fails after all retries
    """
    if not texts:
        return []

    client = _get_client()
    model = config.get("embedding_model", DEFAULT_MODEL)
    max_retries = config.get("max_api_retries", 5)
    base_wait = config.get("api_retry_base_seconds", 2)
    sleep_seconds = config.get("api_sleep_seconds", 1)
    quota_wait = 60

    all_embeddings = []

    # Process in batches
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_embeddings = _get_batch_embeddings(
            client, batch, model, max_retries, base_wait, quota_wait
        )

        if batch_embeddings is None:
            raise RuntimeError(
                f"Failed to get embeddings for batch {i // batch_size + 1}"
            )

        all_embeddings.extend(batch_embeddings)

        # Throttle between batches
        if i + batch_size < len(texts):
            time.sleep(sleep_seconds)

    return all_embeddings


def _get_batch_embeddings(
    client,
    texts: list[str],
    model: str,
    max_retries: int,
    base_wait: float,
    quota_wait: float,
) -> list[list[float]] | None:
    """Get embeddings for a single batch with retry logic.

    Args:
        client: OpenAI client
        texts: List of texts to embed
        model: Embedding model name
        max_retries: Maximum retry attempts
        base_wait: Base wait time for exponential backoff
        quota_wait: Wait time for quota exceeded errors

    Returns:
        List of embedding vectors, or None if failed
    """
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=model,
                input=texts,
            )
            return [e.embedding for e in response.data]

        except RateLimitError as e:
            is_quota = _is_quota_exceeded(e)

            if is_quota:
                if attempt == 0:
                    logger.warning(
                        f"Quota exceeded. Waiting {quota_wait}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(quota_wait)
                else:
                    logger.error(
                        "Quota exceeded after retry. Check billing at "
                        "https://platform.openai.com/account/billing"
                    )
                    return None
            else:
                if attempt < max_retries - 1:
                    parsed_wait = _parse_retry_after(e)
                    wait_time = parsed_wait if parsed_wait else (base_wait * (2**attempt))

                    logger.warning(
                        f"Rate limited. Waiting {wait_time:.1f}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries exceeded after rate limiting: {e}")
                    return None

        except Exception as e:
            logger.error(f"Embedding API call failed: {e}")
            return None

    return None


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine distance between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine distance (1 - cosine similarity), range [0, 2]
    """
    a = np.asarray(a)
    b = np.asarray(b)
    similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return 1.0 - similarity


def cosine_distances(embedding: np.ndarray, embeddings: np.ndarray) -> np.ndarray:
    """Calculate cosine distances from one embedding to many.

    Args:
        embedding: Single embedding vector
        embeddings: Matrix of embedding vectors (one per row)

    Returns:
        Array of cosine distances
    """
    embedding = np.asarray(embedding)
    embeddings = np.asarray(embeddings)

    if len(embeddings.shape) == 1:
        embeddings = embeddings.reshape(1, -1)

    # Normalize
    embedding_norm = embedding / np.linalg.norm(embedding)
    embeddings_norms = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    # Cosine similarity
    similarities = np.dot(embeddings_norms, embedding_norm)

    # Convert to distance
    return 1.0 - similarities


def weighted_mean_embedding(
    embeddings: list[list[float]], weights: list[float] | None = None
) -> list[float]:
    """Calculate weighted mean of embeddings.

    Args:
        embeddings: List of embedding vectors
        weights: Optional weights (defaults to equal weights)

    Returns:
        Weighted mean embedding vector
    """
    embeddings_arr = np.array(embeddings)

    if weights is None:
        mean = np.mean(embeddings_arr, axis=0)
    else:
        weights_arr = np.array(weights)
        weights_arr = weights_arr / weights_arr.sum()  # Normalize
        mean = np.average(embeddings_arr, axis=0, weights=weights_arr)

    return mean.tolist()
