import numpy as np
from sentence_transformers import SentenceTransformer

_model = None


def load_model(name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(name)
    return _model


def embed_text(text: str, model: SentenceTransformer) -> np.ndarray:
    vec = model.encode(text, convert_to_numpy=True)
    norm = np.linalg.norm(vec)
    return (vec / norm).astype(np.float32) if norm > 0 else vec.astype(np.float32)
