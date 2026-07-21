"""
Unit tests for the search service (pure logic — no HTTP, no DB, no ML models).
"""
import pytest

from app.services.search_service import fuse_scores


# ---------------------------------------------------------------------------
# fuse_scores
# ---------------------------------------------------------------------------

def test_fuse_scores_both_empty():
    assert fuse_scores([], []) == []


def test_fuse_scores_text_only():
    text_hits = [(1, 0.9), (2, 0.5)]
    result = fuse_scores(text_hits, [], text_weight=0.4, clip_weight=0.6, top_k=5)
    # id=1 has higher raw text score so it must rank first
    assert result[0][0] == 1
    assert len(result) == 2


def test_fuse_scores_clip_only():
    clip_hits = [(3, 0.8), (4, 0.2)]
    result = fuse_scores([], clip_hits, text_weight=0.4, clip_weight=0.6, top_k=5)
    assert result[0][0] == 3


def test_fuse_scores_fusion_ordering():
    # id=2 wins in CLIP, id=1 wins in text; with default weights CLIP matters more
    text_hits = [(1, 0.9), (2, 0.3)]
    clip_hits = [(2, 0.9), (1, 0.2)]
    result = fuse_scores(text_hits, clip_hits, text_weight=0.4, clip_weight=0.6, top_k=5)
    ids = [r[0] for r in result]
    assert set(ids) == {1, 2}
    # id=2 has 0.6*1.0 + 0.4*(0.3/0.9) ≈ 0.733 > id=1 which has 0.4*1.0 + 0.6*(0.2/0.9) ≈ 0.533
    assert result[0][0] == 2


def test_fuse_scores_top_k_limit():
    text_hits = [(i, float(i)) for i in range(1, 11)]
    result = fuse_scores(text_hits, [], top_k=3)
    assert len(result) == 3


def test_fuse_scores_scores_non_negative():
    text_hits = [(1, 0.5), (2, 0.3)]
    clip_hits = [(1, 0.7), (3, 0.4)]
    result = fuse_scores(text_hits, clip_hits)
    for _, score in result:
        assert score >= 0.0


# ---------------------------------------------------------------------------
# Smoke tests for HTTP endpoints (requires running app + DB)
# ---------------------------------------------------------------------------

def test_stats_endpoint(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    assert "total_indexed" in resp.json()


def test_search_empty_query_rejected(client):
    resp = client.post("/api/search", json={"query": "  "})
    assert resp.status_code == 400


def test_search_valid_query_returns_results_key(client):
    resp = client.post("/api/search", json={"query": "screenshot"})
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body
    assert "query" in body


def test_index_status_endpoint(client):
    resp = client.get("/api/index/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "stage" in data
