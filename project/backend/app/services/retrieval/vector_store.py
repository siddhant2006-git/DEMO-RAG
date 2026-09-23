import json
from pathlib import Path

import numpy as np

from app.config import get_settings
from app.core.logging import get_logger
from app.services.retrieval.chunker import Chunk
from app.services.retrieval.embeddings import EMBEDDING_DIM, embed_texts

settings = get_settings()
logger = get_logger(__name__)

try:
    import faiss

    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False
    logger.warning("faiss_unavailable_using_numpy_fallback")


class _NumpyFlatIndex:
    """Brute-force cosine-similarity index used only when the native FAISS
    extension can't load (e.g. blocked by an Application Control policy).
    Fine at this scale — one document's worth of chunks — and keeps the
    retrieval layer working everywhere without depending on a native DLL.
    """

    def __init__(self, dim: int, vectors: np.ndarray | None = None) -> None:
        self.dim = dim
        self.vectors = vectors if vectors is not None else np.zeros((0, dim), dtype="float32")

    @property
    def ntotal(self) -> int:
        return self.vectors.shape[0]

    def add(self, vectors: np.ndarray) -> None:
        self.vectors = np.vstack([self.vectors, vectors]) if self.ntotal else vectors

    def search(self, query: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        if self.ntotal == 0:
            return np.zeros((1, 0)), np.zeros((1, 0), dtype=int)
        scores = self.vectors @ query[0]
        top_k_idx = np.argsort(-scores)[:k]
        return scores[top_k_idx][None, :], top_k_idx[None, :]


def _paths(document_id: str) -> tuple[Path, Path, Path]:
    base = Path(settings.vectorstore_dir)
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{document_id}.faiss", base / f"{document_id}.npy", base / f"{document_id}.meta.json"


def build_index(document_id: str, chunks: list[Chunk]) -> None:
    """One index per document, persisted to disk so it survives a restart —
    no separate vector DB service to run."""
    faiss_path, npy_path, meta_path = _paths(document_id)
    if not chunks:
        return

    # Vectors are pre-normalized (embeddings.py), so inner product == cosine similarity.
    vectors = np.array(embed_texts([c.text for c in chunks]), dtype="float32")

    if _HAS_FAISS:
        index = faiss.IndexFlatIP(EMBEDDING_DIM)
        index.add(vectors)
        faiss.write_index(index, str(faiss_path))
    else:
        np.save(npy_path, vectors)

    meta_path.write_text(
        json.dumps([{"text": c.text, "page_numbers": c.page_numbers, "heading": c.heading} for c in chunks]),
        encoding="utf-8",
    )


def load_index(document_id: str):
    faiss_path, npy_path, meta_path = _paths(document_id)
    if not meta_path.exists():
        return None, []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if _HAS_FAISS and faiss_path.exists():
        return faiss.read_index(str(faiss_path)), meta
    if npy_path.exists():
        return _NumpyFlatIndex(EMBEDDING_DIM, np.load(npy_path)), meta
    return None, []
