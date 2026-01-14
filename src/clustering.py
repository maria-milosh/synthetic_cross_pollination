"""Clustering algorithms for embedding-based position grouping."""

import logging
from dataclasses import dataclass, field, asdict

import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)

# Valid clustering algorithms
VALID_ALGORITHMS = ["kmeans", "agglomerative"]


@dataclass
class ClusterInfo:
    """Information about a cluster of participant positions."""

    cluster_id: str  # Unique ID, e.g., "Youth programs_cluster_0"
    option: str  # Which voting option this cluster belongs to
    description: str  # 3-sentence summary of cluster's arguments
    embedding: list = field(default_factory=list)  # Embedding of description
    member_count: int = 0  # Number of participants in this cluster
    member_ids: list = field(default_factory=list)  # Participant IDs

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ClusterInfo":
        """Create from dictionary."""
        return cls(**data)


def cluster_embeddings(
    embeddings: list[list[float]],
    max_clusters: int = 6,
    algorithm: str = "kmeans",
    min_cluster_size: int = 1,
) -> list[int]:
    """Cluster embeddings and return cluster labels.

    Automatically determines optimal number of clusters (up to max_clusters)
    using silhouette score.

    Args:
        embeddings: List of embedding vectors
        max_clusters: Maximum number of clusters (default 6)
        algorithm: Clustering algorithm ("kmeans" or "agglomerative")
        min_cluster_size: Minimum points to attempt clustering (default 1)

    Returns:
        List of cluster labels (0-indexed), same length as embeddings

    Raises:
        ValueError: If algorithm is not recognized
    """
    if algorithm not in VALID_ALGORITHMS:
        raise ValueError(
            f"Unknown clustering algorithm: {algorithm}. "
            f"Available: {VALID_ALGORITHMS}"
        )

    n_samples = len(embeddings)

    if n_samples == 0:
        return []

    if n_samples == 1:
        return [0]

    embeddings_arr = np.array(embeddings)

    # Determine optimal number of clusters
    # Can't have more clusters than samples
    max_k = min(max_clusters, n_samples)

    # Need at least 2 samples for silhouette score
    if n_samples < 2:
        return [0] * n_samples

    # If only 2 samples, just use 2 clusters
    if n_samples == 2:
        if algorithm == "kmeans":
            labels = KMeans(n_clusters=2, random_state=42, n_init=10).fit_predict(
                embeddings_arr
            )
        else:
            labels = AgglomerativeClustering(n_clusters=2).fit_predict(embeddings_arr)
        return labels.tolist()

    # Find optimal k using silhouette score
    best_k = 1
    best_score = -1
    best_labels = [0] * n_samples

    for k in range(2, max_k + 1):
        try:
            if algorithm == "kmeans":
                clusterer = KMeans(n_clusters=k, random_state=42, n_init=10)
            else:
                clusterer = AgglomerativeClustering(n_clusters=k)

            labels = clusterer.fit_predict(embeddings_arr)

            # Calculate silhouette score
            score = silhouette_score(embeddings_arr, labels)

            if score > best_score:
                best_score = score
                best_k = k
                best_labels = labels.tolist()

        except Exception as e:
            logger.warning(f"Clustering failed for k={k}: {e}")
            continue

    logger.info(
        f"Selected {best_k} clusters (silhouette score: {best_score:.3f}) "
        f"using {algorithm}"
    )

    return best_labels


def get_cluster_members(
    labels: list[int], participant_ids: list[str]
) -> dict[int, list[str]]:
    """Group participant IDs by cluster label.

    Args:
        labels: Cluster labels for each participant
        participant_ids: Participant IDs in same order as labels

    Returns:
        Dict mapping cluster label to list of participant IDs
    """
    clusters = {}
    for label, pid in zip(labels, participant_ids):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(pid)
    return clusters


def get_cluster_centroids(
    embeddings: list[list[float]], labels: list[int]
) -> dict[int, list[float]]:
    """Calculate centroid for each cluster.

    Args:
        embeddings: List of embedding vectors
        labels: Cluster labels for each embedding

    Returns:
        Dict mapping cluster label to centroid embedding
    """
    embeddings_arr = np.array(embeddings)
    labels_arr = np.array(labels)

    centroids = {}
    unique_labels = set(labels)

    for label in unique_labels:
        mask = labels_arr == label
        cluster_embeddings = embeddings_arr[mask]
        centroid = np.mean(cluster_embeddings, axis=0)
        centroids[label] = centroid.tolist()

    return centroids
