"""
Sentence embeddings behind a swappable adapter.

Two implementations:

TfidfEmbedder (default)
    scikit-learn TF-IDF over words, with no dimensionality reduction. No model
    download, deterministic, fast. It measures *wording* overlap: it sees
    "the dog ate the cake" and "the cake was eaten by the dog" as similar, but
    not "the pet consumed dessert".

    Latent semantic analysis (TruncatedSVD) was tried and removed: fitted on the
    handful of sentences in a single document it is unstable, and it reported
    unrelated sentences as almost identical. Plain TF-IDF is less clever and
    much more trustworthy at this scale.

SentenceTransformerEmbedder (optional)
    A sentence-transformers model, which does capture paraphrase. Needs the
    package and a one-time model download (a few hundred MB).

Choose with settings.EMBEDDING_BACKEND: "auto" (default; uses the transformer
if it loads, otherwise TF-IDF), "tfidf", or "sentence-transformers".
Every result records which backend produced it, so no page ever implies more
semantic understanding than was actually used.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import numpy as np
from django.conf import settings

logger = logging.getLogger("authentitext")

MAX_FEATURES = 2000   # caps memory on long documents


class BaseEmbedder:
    key: str = ""
    label: str = ""
    description: str = ""
    captures_paraphrase: bool = False
    redundancy_threshold: float = 0.8   # cosine above which two sentences are near-duplicates

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one L2-normalised row per text, so a dot product is a cosine."""
        raise NotImplementedError


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


class TfidfEmbedder(BaseEmbedder):
    key = "tfidf"
    label = "TF-IDF (wording overlap)"
    description = ("Wording-based similarity from scikit-learn TF-IDF. It compares which words two sentences "
                   "share, weighted so that words common to the whole document count for less. It spots "
                   "near-duplicates and reused vocabulary, but not paraphrase in different words.")
    captures_paraphrase = False
    redundancy_threshold = 0.5

    def encode(self, texts: list[str]) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not texts:
            return np.zeros((0, 1))
        matrix = TfidfVectorizer(sublinear_tf=True, max_features=MAX_FEATURES).fit_transform(texts)
        return _normalize(np.asarray(matrix.todense(), dtype=float))


class SentenceTransformerEmbedder(BaseEmbedder):
    key = "sentence-transformers"
    captures_paraphrase = True
    redundancy_threshold = 0.85

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer   # raises if not installed

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)            # raises if the model isn't available
        self.label = f"sentence-transformers ({model_name})"
        self.description = ("Meaning-based similarity from a sentence-transformer model, which can recognise "
                            "two sentences as similar even when they share few words.")

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 1))
        return _normalize(np.asarray(self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False), dtype=float))


@lru_cache(maxsize=1)
def get_embedder() -> BaseEmbedder:
    """Cached: building a TF-IDF embedder is cheap, but loading a transformer is not."""
    backend = getattr(settings, "EMBEDDING_BACKEND", "auto")
    model_name = getattr(settings, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    if backend in ("auto", "sentence-transformers"):
        try:
            embedder = SentenceTransformerEmbedder(model_name)
            logger.info("Embeddings: %s", embedder.label)
            return embedder
        except Exception as exc:
            if backend == "sentence-transformers":
                raise
            logger.info("sentence-transformers unavailable (%s); using TF-IDF embeddings.", exc.__class__.__name__)
    return TfidfEmbedder()
