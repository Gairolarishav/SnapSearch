"""
Search service — score fusion logic for hybrid text + CLIP search.
"""


def fuse_scores(
    text_results: list,
    clip_results: list,
    text_weight: float = 0.4,
    clip_weight: float = 0.6,
    top_k: int = 9,
) -> list[tuple]:
    """
    Fuse text-embedding and CLIP scores into a single ranked list.

    Both score sets are independently max-normalised before being
    combined as: final = text_weight * text_score + clip_weight * clip_score.

    Args:
        text_results: List of (db_id, raw_score) from the text FAISS index.
        clip_results: List of (db_id, raw_score) from the CLIP FAISS index.
        text_weight:  Weight applied to normalised text scores (default 0.4).
        clip_weight:  Weight applied to normalised CLIP scores (default 0.6).
        top_k:        Number of top results to return.

    Returns:
        Sorted list of (db_id, fused_score) descending, capped at top_k.
    """
    scores: dict[int, float] = {}

    if text_results:
        max_t = max(s for _, s in text_results) or 1.0
        for db_id, s in text_results:
            scores[db_id] = scores.get(db_id, 0.0) + text_weight * (s / max_t)

    if clip_results:
        max_c = max(s for _, s in clip_results) or 1.0
        for db_id, s in clip_results:
            scores[db_id] = scores.get(db_id, 0.0) + clip_weight * (s / max_c)

    return sorted(scores.items(), key=lambda x: -x[1])[:top_k]
