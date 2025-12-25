"""Vector serialization utilities for sqlite-vec."""

import numpy as np


def serialize_vector(vector: np.ndarray | list[float]) -> bytes:
    """
    Serialize a vector to bytes for storage in SQLite.

    Args:
        vector: Numpy array or list of floats

    Returns:
        Bytes representation of vector as float32
    """
    if isinstance(vector, list):
        vector = np.array(vector, dtype=np.float32)
    elif vector.dtype != np.float32:
        vector = vector.astype(np.float32)
    return vector.tobytes()
