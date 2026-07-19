import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer

_clip_model = None


def load_clip_model(name: str = "clip-ViT-B-32") -> SentenceTransformer:
    global _clip_model
    if _clip_model is None:
        _clip_model = SentenceTransformer(name)
    return _clip_model


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return (vec / norm).astype(np.float32) if norm > 0 else vec.astype(np.float32)


def embed_image_clip(image_path: str, model: SentenceTransformer) -> np.ndarray:
    img = Image.open(image_path).convert("RGB")
    return _normalize(model.encode(img, convert_to_numpy=True))


def embed_query_clip(query: str, model: SentenceTransformer) -> np.ndarray:
    return _normalize(model.encode(query, convert_to_numpy=True))
