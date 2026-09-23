"""
Statistical features: how predictable and how evenly distributed the text is.

- Shannon entropy over the word distribution, in bits, plus a normalised form
  (entropy divided by log2 of the vocabulary size) so lengths are comparable.
- Burstiness B = (sigma - mu) / (sigma + mu) over sentence lengths
  (Goh & Barabasi, 2008). +1 is very uneven, 0 is random-like, -1 is perfectly
  regular. Human prose usually sits slightly below 0; very regular text
  approaches -1. It is one signal among many, never evidence on its own.
- N-gram repetition: the share of bigrams and trigrams that occur more than once.
- Zipf slope: the fitted slope of log(frequency) against log(rank). Natural
  English is near -1; a flatter slope means the common words dominate less.
- Distinctive terms: TF-IDF where the inverse document frequency comes from
  wordfreq's general-English corpus, so a term stands out when it is frequent
  here but rare in ordinary English. Term frequency is sublinear (1 + log10 f),
  the standard damping: without it a common word repeated often (“useful”)
  outranks a rare, specific one (“LoRaWAN”).

Perplexity is deliberately absent: it needs a language model, which this project
does not ship. See docs/LIMITATIONS.md.
"""
from __future__ import annotations

import math
import statistics
from collections import Counter

from .lexical import zipf
from .preprocessing import ProcessedDocument

TOP_TERMS = 12
MIN_SENTENCES_FOR_BURSTINESS = 3
MAX_ZIPF = 8.0          # roughly "the"; used to turn a Zipf score into an IDF weight
MIN_TERM_LENGTH = 3


def shannon_entropy(counts: Counter) -> float | None:
    total = sum(counts.values())
    if not total:
        return None
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def normalized_entropy(counts: Counter) -> float | None:
    entropy = shannon_entropy(counts)
    if entropy is None or len(counts) < 2:
        return None
    return entropy / math.log2(len(counts))


def burstiness(values: list[int]) -> float | None:
    if len(values) < MIN_SENTENCES_FOR_BURSTINESS:
        return None
    mean = statistics.fmean(values)
    sigma = statistics.pstdev(values)
    if mean + sigma == 0:
        return None
    return (sigma - mean) / (sigma + mean)


def ngram_repeat_rate(forms: list[str], n: int) -> float | None:
    if len(forms) < n + 1:
        return None
    grams = Counter(tuple(forms[i:i + n]) for i in range(len(forms) - n + 1))
    repeated = sum(count for count in grams.values() if count > 1)
    return repeated / sum(grams.values())


def zipf_slope(counts: Counter) -> float | None:
    """Least-squares slope of log10(frequency) against log10(rank)."""
    frequencies = sorted(counts.values(), reverse=True)
    if len(frequencies) < 10:
        return None
    xs = [math.log10(rank) for rank in range(1, len(frequencies) + 1)]
    ys = [math.log10(freq) for freq in frequencies]
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if not denominator:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator


def surface_forms(words) -> dict[str, str]:
    """
    The most common form of each lemma as it actually appears, so the interface
    shows "data" and "IoT" rather than the dictionary forms "datum" and "iot".
    """
    forms: dict[str, Counter] = {}
    for word in words:
        forms.setdefault(word.lemma, Counter())[word.text] += 1
    return {lemma: counter.most_common(1)[0][0] for lemma, counter in forms.items()}


def distinctive_terms(doc: ProcessedDocument) -> list[dict]:
    """
    TF-IDF against general English: sublinear term frequency here, weighted by
    how rare the word is overall (wordfreq Zipf turned into an IDF-style weight).
    """
    words = [w for w in doc.words if w.is_alpha and not w.is_stop and len(w.lemma) >= MIN_TERM_LENGTH]
    if not words:
        return []
    counts = Counter(w.lemma for w in words)
    display = surface_forms(words)
    scored = []
    for lemma, count in counts.items():
        weight = max(MAX_ZIPF - zipf(lemma), 0.0)     # rarer in general English -> higher weight
        if weight <= 0:
            continue
        term_frequency = 1 + math.log10(count)        # sublinear damping
        scored.append({"term": display[lemma], "count": count, "score": round(term_frequency * weight, 4)})
    scored.sort(key=lambda t: (-t["score"], t["term"].lower()))
    return scored[:TOP_TERMS]


def compute_statistics(doc: ProcessedDocument) -> tuple[dict[str, float | None], dict]:
    forms = [w.norm for w in doc.words]
    counts = Counter(forms)
    lengths = [len(s.words) for s in doc.sentences]   # headings included, as in document_stats
    features = {
        "word_entropy": shannon_entropy(counts),
        "normalized_entropy": normalized_entropy(counts),
        "sentence_length_burstiness": burstiness(lengths),
        "bigram_repeat_rate": ngram_repeat_rate(forms, 2),
        "trigram_repeat_rate": ngram_repeat_rate(forms, 3),
        "zipf_slope": zipf_slope(counts),
    }
    return features, {"distinctive_terms": distinctive_terms(doc)}
