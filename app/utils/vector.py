"""Vector serialization utilities for sqlite-vec."""

import numpy as np


def serialize_vector(vector: np.ndarray | list[float]) -> bytes:
    """
    Serialize a vector to bytes for storage in SQLite.

    Args:
        vector: Numpy array or list of floats

    Returns:
        Bytes representation of the vector as float32
    """
    if isinstance(vector, list):
        vector = np.array(vector, dtype=np.float32)
    elif vector.dtype != np.float32:
        vector = vector.astype(np.float32)
    return vector.tobytes()


def deserialize_vector(data: bytes, dim: int | None = None) -> np.ndarray:
    """
    Deserialize bytes back to a numpy vector.

    Args:
        data: Bytes representation of the vector
        dim: Optional dimension hint (inferred from data if not provided)

    Returns:
        Numpy array of float32
    """
    vector = np.frombuffer(data, dtype=np.float32)
    if dim is not None and len(vector) != dim:
        raise ValueError(f"Expected vector of dimension {dim}, got {len(vector)}")
    return vector


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1)
    """
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))
