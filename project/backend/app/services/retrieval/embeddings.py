from functools import lru_cache

from sentence_transformers import SentenceTransformer

# All-MiniLM-L6-v2: 384-dim, small and fast on CPU — plenty for matching a
# query like "turnover requirement" against a page of tender text.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache
def _get_model() -> SentenceTransformer:
    # Loaded once per process and cached — the several-hundred-ms load cost
    # would otherwise repeat on every embed_texts() call.
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
