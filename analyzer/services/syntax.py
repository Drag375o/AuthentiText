"""
Syntactic features from spaCy's part-of-speech tags and dependency parse.

- POS distribution: share of words in each universal POS class.
- Parse depth: the longest head chain from any word to the sentence root.
- Mean dependency distance: average |position - head position| over non-root,
  non-punctuation tokens (Liu, 2008). Longer distances are harder to process.
- Clauses: the main clause plus clausal dependents (advcl, ccomp, csubj,
  csubjpass, acl, relcl, xcomp) and verbs coordinated with another verb.
- Subordinate clauses: the finite clausal dependents (advcl, ccomp, csubj,
  csubjpass, acl, relcl).
- Passive voice: a sentence with a passive subject or passive auxiliary
  (nsubjpass / auxpass). "Get"-passives and reduced passives are missed.

The parser is statistical, so these are estimates.
"""
from __future__ import annotations

import statistics
from collections import Counter

from .preprocessing import ProcessedDocument, Sentence

POS_GROUPS = {
    "noun": {"NOUN"}, "propn": {"PROPN"}, "verb": {"VERB"}, "adj": {"ADJ"}, "adv": {"ADV"},
    "pron": {"PRON"}, "det": {"DET"}, "conj": {"CCONJ", "SCONJ"}, "adp": {"ADP"},
    "aux": {"AUX"}, "num": {"NUM"},
}
CLAUSAL_DEPS = {"advcl", "ccomp", "csubj", "csubjpass", "acl", "relcl", "xcomp"}
SUBORDINATE_DEPS = {"advcl", "ccomp", "csubj", "csubjpass", "acl", "relcl"}
PASSIVE_DEPS = {"nsubjpass", "auxpass", "csubjpass"}
VERBAL_POS = {"VERB", "AUX"}


def parse_depth(sentence: Sentence) -> int:
    by_index = {t.index: t for t in sentence.tokens}
    deepest = 0
    for token in sentence.tokens:
        depth, current, seen = 0, token, set()
        while current.head != current.index and current.head in by_index and current.index not in seen:
            seen.add(current.index)
            current = by_index[current.head]
            depth += 1
        deepest = max(deepest, depth)
    return deepest


def dependency_distances(sentence: Sentence) -> list[int]:
    return [abs(t.index - t.head) for t in sentence.tokens if t.head != t.index and not t.is_punct]


def clause_counts(sentence: Sentence) -> tuple[int, int, int]:
    """(clauses, subordinate clauses, coordinating conjunctions)."""
    by_index = {t.index: t for t in sentence.tokens}
    clausal = sum(1 for t in sentence.tokens if t.dep in CLAUSAL_DEPS)
    coordinated_verbs = sum(
        1 for t in sentence.tokens
        if t.dep == "conj" and t.pos in VERBAL_POS and by_index.get(t.head) and by_index[t.head].pos in VERBAL_POS
    )
    subordinate = sum(1 for t in sentence.tokens if t.dep in SUBORDINATE_DEPS)
    coordination = sum(1 for t in sentence.tokens if t.dep == "cc")
    return 1 + clausal + coordinated_verbs, subordinate, coordination


def is_passive(sentence: Sentence) -> bool:
    return any(t.dep in PASSIVE_DEPS for t in sentence.tokens)


def sentence_syntax(sentence: Sentence) -> dict:
    clauses, subordinate, _ = clause_counts(sentence)
    distances = dependency_distances(sentence)
    return {
        "depth": parse_depth(sentence),
        "dependency_distance": round(statistics.fmean(distances), 2) if distances else None,
        "clauses": clauses,
        "subordinate_clauses": subordinate,
        "passive": is_passive(sentence),
    }


def pos_distribution(doc: ProcessedDocument) -> dict[str, float | None]:
    words = doc.words
    counts = Counter(w.pos for w in words)
    return {
        f"pos_{name}_ratio": (sum(counts[tag] for tag in tags) / len(words)) if words else None
        for name, tags in POS_GROUPS.items()
    }


def compute_syntax(doc: ProcessedDocument) -> dict[str, float | None]:
    sentences = doc.sentences
    n = len(sentences)
    per_sentence = [clause_counts(s) for s in sentences]
    distances = [d for s in sentences for d in dependency_distances(s)]
    features = {
        "parse_depth_mean": statistics.fmean(parse_depth(s) for s in sentences) if n else None,
        "dependency_distance_mean": statistics.fmean(distances) if distances else None,
        "clauses_per_sentence": statistics.fmean(c for c, _, _ in per_sentence) if n else None,
        "subordinate_clauses_per_sentence": statistics.fmean(s for _, s, _ in per_sentence) if n else None,
        "coordination_per_sentence": statistics.fmean(c for _, _, c in per_sentence) if n else None,
        "passive_sentence_ratio": (sum(is_passive(s) for s in sentences) / n) if n else None,
    }
    features.update(pos_distribution(doc))
    return features
