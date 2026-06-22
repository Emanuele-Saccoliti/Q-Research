from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

FloatMatrix = NDArray[np.float64]


def normalize_rows(values: FloatMatrix) -> FloatMatrix:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return values / norms


def cosine(vector_a: NDArray[np.float64], vector_b: NDArray[np.float64]) -> float:
    denominator = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / denominator)


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> FloatMatrix: ...


class HashingEmbedder:
    """Stateless, stable baseline using hashed unigram and bigram features."""

    name = "HashingVectorizer"

    def __init__(self, dimensions: int = 512):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.vectorizer = HashingVectorizer(
            n_features=dimensions,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
            stop_words="english",
        )

    def encode(self, texts: list[str]) -> FloatMatrix:
        if not texts:
            return np.empty((0, self.vectorizer.n_features), dtype=np.float64)
        return self.vectorizer.transform(texts).toarray().astype(np.float64)


class SentenceTransformerEmbedder:
    name = "SentenceTransformer"

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install `.[transformers]` to use sentence-transformer embeddings."
            ) from exc
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> FloatMatrix:
        values = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(values, dtype=np.float64)


def build_embedder(provider: str, model_name: str, dimensions: int) -> Embedder:
    if provider == "sentence-transformer":
        return SentenceTransformerEmbedder(model_name)
    return HashingEmbedder(dimensions=dimensions)

