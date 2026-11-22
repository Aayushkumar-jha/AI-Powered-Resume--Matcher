"""Sentence-embedding service (all-MiniLM-L6-v2) with a TF-IDF fallback.

all-MiniLM-L6-v2 maps text to a 384-dimensional vector; semantically similar texts have a
high cosine similarity even when they share few words ("built REST services with Flask"
vs "API development in Python"). If the model cannot be loaded (e.g. no internet on the
first run), the service transparently falls back to scikit-learn TF-IDF vectors, and
reports that through `backend_name`.
"""
import logging
import threading

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import get_settings

log = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str, backend: str = "sentence-transformers"):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()
        self._cache: dict[str, np.ndarray] = {}
        self.backend_name = "tfidf" if backend == "tfidf" else "pending"

    def _load(self) -> None:
        if self.backend_name != "pending":
            return
        with self._lock:
            if self.backend_name != "pending":
                return
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name, device="cpu")
                self.backend_name = f"sentence-transformers/{self.model_name}"
                log.info("Loaded embedding model %s", self.model_name)
            except Exception as exc:  # pragma: no cover - depends on environment
                log.warning("Could not load %s (%s); falling back to TF-IDF", self.model_name, exc)
                self.backend_name = "tfidf"

    @property
    def uses_transformer(self) -> bool:
        self._load()
        return self._model is not None

    def encode(self, texts: list[str]) -> np.ndarray:
        """L2-normalized embeddings (transformer backend only), cached per text."""
        self._load()
        if self._model is None:
            raise RuntimeError("encode() requires the transformer backend")
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            vecs = self._model.encode(missing, batch_size=32, normalize_embeddings=True,
                                      show_progress_bar=False, convert_to_numpy=True)
            if len(self._cache) > 20_000:
                self._cache.clear()
            self._cache.update(zip(missing, vecs))
        return np.vstack([self._cache[t] for t in texts])

    def similarity(self, a: list[str], b: list[str]) -> np.ndarray:
        """Cosine-similarity matrix of shape (len(a), len(b))."""
        if not a or not b:
            return np.zeros((len(a), len(b)))
        if self.uses_transformer:
            return np.clip(self.encode(a) @ self.encode(b).T, -1.0, 1.0)
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        try:
            m = vec.fit_transform(a + b)
        except ValueError:  # empty vocabulary
            return np.zeros((len(a), len(b)))
        return cosine_similarity(m[: len(a)], m[len(a):])


_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _service
    if _service is None:
        s = get_settings()
        _service = EmbeddingService(s.embedding_model, s.embedding_backend)
    return _service
