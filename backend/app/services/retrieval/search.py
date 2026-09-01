from dataclasses import dataclass

import numpy as np

from app.services.retrieval.embeddings import embed_query
from app.services.retrieval.vector_store import load_index


@dataclass
class SearchResult:
    text: str
    page_numbers: list[int]
    heading: str | None
    score: float


def search(document_id: str, query: str, top_k: int = 5) -> list[SearchResult]:
    """Top-k clause search — 'find the clause that proves X' for a given
    document, e.g. locating the exact eligibility clause an officer wants to
    double-check against an extracted requirement."""
    index, meta = load_index(document_id)
    if index is None or index.ntotal == 0:
        return []

    query_vector = np.array([embed_query(query)], dtype="float32")
    scores, indices = index.search(query_vector, min(top_k, index.ntotal))

    results: list[SearchResult] = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        m = meta[idx]
        results.append(SearchResult(text=m["text"], page_numbers=m["page_numbers"], heading=m["heading"], score=float(score)))
    return results
