import pickle
from pathlib import Path

import faiss
import numpy as np


def build_index(dim: int) -> faiss.IndexFlatIP:
    return faiss.IndexFlatIP(dim)


def add_vector(index: faiss.IndexFlatIP, vec: np.ndarray) -> None:
    index.add(vec.reshape(1, -1))


def search(
    index: faiss.IndexFlatIP,
    id_map: list,
    query_vec: np.ndarray,
    top_k: int,
) -> list[tuple]:
    if index.ntotal == 0:
        return []
    k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vec.reshape(1, -1), k)
    return [
        (id_map[i], float(scores[0][j]))
        for j, i in enumerate(indices[0])
        if i != -1
    ]


def save_index(index, id_map: list, index_path: Path, map_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    with open(map_path, "wb") as f:
        pickle.dump(id_map, f)


def load_index(index_path: Path, map_path: Path) -> tuple:
    if not index_path.exists():
        return None, []
    index = faiss.read_index(str(index_path))
    with open(map_path, "rb") as f:
        id_map = pickle.load(f)
    return index, id_map
