"""
Semantic analysis over sentence embeddings (see embeddings.py for the adapter).

- Local coherence: average similarity between consecutive sentences. Low values
  mean the text jumps between ideas; very high values mean it circles one point.
- Paragraph coherence: how close each sentence sits to its paragraph's centre.
- Redundancy: the share of sentence pairs above the backend's near-duplicate
  threshold, plus the most similar pair found.
- Diversity: 1 minus the average similarity across all sentence pairs.
- Opening/closing similarity: how close the first and last paragraphs are.

Every measure needs at least MIN_SENTENCES sentences; below that they are None
rather than a number nobody should trust.
"""
from __future__ import annotations

import numpy as np

from .embeddings import get_embedder
from .preprocessing import ProcessedDocument

MIN_SENTENCES = 4
MAX_SIMILAR_PAIRS = 8


def _pairwise(matrix: np.ndarray) -> np.ndarray:
    return np.clip(matrix @ matrix.T, -1.0, 1.0)


def compute_semantics(doc: ProcessedDocument) -> tuple[dict[str, float | None], dict]:
    embedder = get_embedder()
    sentences = doc.sentences
    empty = dict.fromkeys(
        ["local_coherence", "paragraph_coherence", "semantic_redundancy", "semantic_diversity",
         "opening_closing_similarity", "max_sentence_similarity"], None)
    details = {
        "embedding_backend": embedder.key,
        "embedding_label": embedder.label,
        "embedding_description": embedder.description,
        "embedding_captures_paraphrase": embedder.captures_paraphrase,
        "similar_pairs": [],
    }
    if len(sentences) < MIN_SENTENCES:
        details["semantics_skipped"] = f"Semantic measures need at least {MIN_SENTENCES} sentences."
        return empty, details

    texts = [doc.text_of(s.start, s.end) for s in sentences]
    vectors = embedder.encode(texts)
    similarity = _pairwise(vectors)
    n = len(sentences)
    upper = np.triu_indices(n, k=1)
    pair_scores = similarity[upper]

    adjacent = [similarity[i, i + 1] for i in range(n - 1)]

    paragraph_scores = []
    for index in range(len(doc.paragraphs)):
        rows = [i for i, s in enumerate(sentences) if s.paragraph == index]
        if len(rows) < 2:
            continue
        centroid = vectors[rows].mean(axis=0)
        centroid /= max(np.linalg.norm(centroid), 1e-12)
        paragraph_scores.extend(float(vectors[i] @ centroid) for i in rows)

    def paragraph_centroid(index: int) -> np.ndarray | None:
        rows = [i for i, s in enumerate(sentences) if s.paragraph == index]
        if not rows:
            return None
        centroid = vectors[rows].mean(axis=0)
        return centroid / max(np.linalg.norm(centroid), 1e-12)

    opening, closing = paragraph_centroid(0), paragraph_centroid(len(doc.paragraphs) - 1)
    opening_closing = float(opening @ closing) if opening is not None and closing is not None and len(doc.paragraphs) > 1 else None

    threshold = embedder.redundancy_threshold
    features = {
        "local_coherence": float(np.mean(adjacent)) if adjacent else None,
        "paragraph_coherence": float(np.mean(paragraph_scores)) if paragraph_scores else None,
        "semantic_redundancy": float(np.mean(pair_scores >= threshold)) if pair_scores.size else None,
        "semantic_diversity": float(1 - np.mean(pair_scores)) if pair_scores.size else None,
        "opening_closing_similarity": opening_closing,
        "max_sentence_similarity": float(pair_scores.max()) if pair_scores.size else None,
    }

    order = np.argsort(pair_scores)[::-1][:MAX_SIMILAR_PAIRS]
    details["similar_pairs"] = [
        {"a": int(upper[0][k]), "b": int(upper[1][k]), "similarity": round(float(pair_scores[k]), 3),
         "near_duplicate": bool(pair_scores[k] >= threshold)}
        for k in order if pair_scores[k] > 0.3
    ]
    details["redundancy_threshold"] = threshold

    # Per-sentence: closest other sentence, for the sentence list.
    np.fill_diagonal(similarity, -1.0)
    details["sentence_similarity"] = [
        {"index": i, "closest": int(np.argmax(similarity[i])), "similarity": round(float(similarity[i].max()), 3)}
        for i in range(n)
    ]
    return features, details
