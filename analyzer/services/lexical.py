"""
Lexical features: vocabulary diversity, word frequency, and repetition.

Diversity
- TTR:   types / tokens. Simple, but it falls as texts get longer.
- MATTR: mean TTR over every window of MATTR_WINDOW tokens (Covington & McFall, 2010).
- MTLD:  mean length of word runs that keep TTR above 0.72, averaged over a
         forward and a backward pass (McCarthy & Jarvis, 2010).
Frequency uses wordfreq Zipf scores: log10 of frequency per billion words.
Repetition finds maximal repeated phrases, with their spans in the original.
"""
from __future__ import annotations

import statistics
from collections import Counter
from functools import lru_cache

from .preprocessing import ProcessedDocument, Token

MATTR_WINDOW = 50
MTLD_THRESHOLD = 0.72
MTLD_MIN_TOKENS = 50
RARE_ZIPF = 3.0
COMMON_ZIPF = 5.0
LONG_WORD_LETTERS = 7
PHRASE_MIN_N, PHRASE_MAX_N = 2, 6
COVERAGE_MIN_N = 3
MAX_PHRASES = 20
TOP_WORDS = 12


@lru_cache(maxsize=50_000)
def zipf(word: str) -> float:
    from wordfreq import zipf_frequency
    return zipf_frequency(word, "en")


# ---------- Diversity ----------

def type_token_ratio(forms: list[str]) -> float | None:
    return len(set(forms)) / len(forms) if forms else None


def mattr(forms: list[str], window: int = MATTR_WINDOW) -> float | None:
    """Moving-average TTR in O(n) with a sliding counter."""
    if not forms:
        return None
    if len(forms) <= window:
        return type_token_ratio(forms)
    counts = Counter(forms[:window])
    total = len(counts)
    for i in range(window, len(forms)):
        outgoing, incoming = forms[i - window], forms[i]
        counts[outgoing] -= 1
        if counts[outgoing] == 0:
            del counts[outgoing]
        counts[incoming] += 1
        total += len(counts)
    return total / (len(forms) - window + 1) / window


def _mtld_pass(forms: list[str], threshold: float) -> float | None:
    factors, types, count, ttr = 0.0, set(), 0, 1.0
    for form in forms:
        count += 1
        types.add(form)
        ttr = len(types) / count
        if ttr <= threshold:
            factors += 1
            types, count, ttr = set(), 0, 1.0
    if count:
        factors += (1 - ttr) / (1 - threshold)   # partial factor for the leftover run
    return len(forms) / factors if factors else None


def mtld(forms: list[str], threshold: float = MTLD_THRESHOLD) -> float | None:
    if len(forms) < MTLD_MIN_TOKENS:
        return None
    forward, backward = _mtld_pass(forms, threshold), _mtld_pass(forms[::-1], threshold)
    if forward is None or backward is None:
        return None
    return (forward + backward) / 2


# ---------- Repetition ----------

def repeated_phrases(doc: ProcessedDocument) -> list[dict]:
    """
    Maximal repeated phrases. Longer phrases are chosen first; a shorter phrase is
    kept only for occurrences not already inside a chosen longer one. Phrases made
    only of function words ("of the", "it is") are ignored. Phrases never cross a
    sentence boundary.
    """
    sentences = [[w for w in s.words] for s in doc.sentences]
    candidates: dict[tuple[str, ...], list[tuple[int, int, int, int]]] = {}
    for n in range(PHRASE_MAX_N, PHRASE_MIN_N - 1, -1):
        for s_i, words in enumerate(sentences):
            for i in range(len(words) - n + 1):
                gram = words[i:i + n]
                if all(t.is_stop or t.like_num for t in gram):
                    continue
                key = tuple(t.norm for t in gram)
                candidates.setdefault(key, []).append((s_i, i, gram[0].start, gram[-1].end))

    chosen, covered = [], set()   # covered: (sentence, word index) already in a chosen phrase
    for key in sorted(candidates, key=lambda k: (-len(k), -len(candidates[k]), k)):
        n = len(key)
        free = [occ for occ in candidates[key] if not any((occ[0], occ[1] + j) in covered for j in range(n))]
        if len(free) < 2:
            continue
        for s_i, i, _, _ in free:
            covered.update((s_i, i + j) for j in range(n))
        first = free[0]
        chosen.append({
            "phrase": doc.text_of(first[2], first[3]),
            "n": n,
            "count": len(free),
            "spans": [[start, end] for _, _, start, end in free],
        })
    chosen.sort(key=lambda p: (-p["count"] * p["n"], -p["n"], p["phrase"].lower()))
    return chosen[:MAX_PHRASES]


def phrase_coverage(doc: ProcessedDocument, phrases: list[dict]) -> float | None:
    words = doc.words
    if not words:
        return None
    covered = set()
    for phrase in phrases:
        if phrase["n"] < COVERAGE_MIN_N:
            continue
        for start, end in phrase["spans"]:
            covered.update(i for i, w in enumerate(words) if start <= w.start and w.end <= end)
    return len(covered) / len(words)


# ---------- Top words ----------

def top_content_words(words: list[Token]) -> list[dict]:
    """Grouped by lemma so “recipe” and “recipes” count together, but shown
    in the form that actually appears most often in the text."""
    from .statistics_features import surface_forms

    content = [w for w in words if w.is_content and not w.is_stop and w.is_alpha and len(w.lemma) > 1]
    counts = Counter(w.lemma for w in content)
    display = surface_forms(content)
    return [{"word": display[lemma], "count": n} for lemma, n in counts.most_common(TOP_WORDS) if n > 1]


# ---------- Entry point ----------

def compute_lexical(doc: ProcessedDocument) -> tuple[dict[str, float | None], dict]:
    words = doc.words
    forms = [w.norm for w in words if w.is_alpha or not w.like_num]
    n = len(forms)
    counts = Counter(forms)
    alpha_words = [w for w in words if w.is_alpha]
    frequency_words = [w for w in alpha_words if w.pos != "PROPN"]
    content_zipfs = [zipf(w.norm) for w in frequency_words if w.is_content and not w.is_stop]

    phrases = repeated_phrases(doc)
    long_phrases = [p for p in phrases if p["n"] >= COVERAGE_MIN_N]

    features = {
        "type_token_ratio": type_token_ratio(forms),
        "mattr": mattr(forms),
        "mtld": mtld(forms),
        "hapax_ratio": (sum(1 for c in counts.values() if c == 1) / n) if n else None,
        "lexical_density": (sum(1 for w in words if w.is_content) / len(words)) if words else None,
        "function_word_ratio": (sum(1 for w in words if w.is_stop) / len(words)) if words else None,
        "long_word_ratio": (sum(1 for w in alpha_words if len(w.text) >= LONG_WORD_LETTERS) / len(alpha_words)) if alpha_words else None,
        "rare_word_ratio": (sum(1 for w in frequency_words if zipf(w.norm) < RARE_ZIPF) / len(frequency_words)) if frequency_words else None,
        "common_word_ratio": (sum(1 for w in frequency_words if zipf(w.norm) >= COMMON_ZIPF) / len(frequency_words)) if frequency_words else None,
        "mean_content_zipf": statistics.fmean(content_zipfs) if content_zipfs else None,
        "repeated_phrase_count": len(long_phrases),
        "repeated_phrase_coverage": phrase_coverage(doc, phrases),
    }
    details = {"top_words": top_content_words(words), "repeated_phrases": phrases}
    return features, details
