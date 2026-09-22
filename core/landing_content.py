"""
Static content for the landing page.

Kept in Python rather than hard-coded in templates so the templates stay
declarative. Every sentence-level "signal" here is an ILLUSTRATIVE example
written by hand to explain the interface. It is not model output, and the
page labels it that way.
"""

SAMPLE_DOCUMENT = [
    {
        "text": "My grandmother kept her recipes on the backs of electricity bills.",
        "level": "low", "level_label": "Low signal",
        "reasons": ["Concrete, personal detail", "Uncommon word pairing", "Short, uneven rhythm"],
        "note": None,
    },
    {
        "text": "In today's fast-paced world, it is important to note that food plays a vital role in shaping cultural identity.",
        "level": "high", "level_label": "High signal",
        "reasons": ["Formulaic opener (\u201cIn today's fast-paced world\u201d)",
                    "Academic framing phrase (\u201cit is important to note\u201d)",
                    "Generic abstraction with no specific referent"],
        "note": "stock opener + framing phrase",
    },
    {
        "text": "Half of them are unreadable now, stained with turmeric.",
        "level": "low", "level_label": "Low signal",
        "reasons": ["Sensory specificity", "Sentence length breaks the pattern"],
        "note": None,
    },
    {
        "text": "Furthermore, these traditions not only preserve heritage but also foster a sense of belonging across generations.",
        "level": "mid", "level_label": "Medium signal",
        "reasons": ["Transition-led sentence (\u201cFurthermore\u201d)",
                    "Balanced \u201cnot only \u2026 but also\u201d template",
                    "Semantically close to sentence 2"],
        "note": "echoes sentence 2",
    },
    {
        "text": "I still can't make her dal taste right.",
        "level": "low", "level_label": "Low signal",
        "reasons": ["First-person voice", "Informal contraction", "Specific object"],
        "note": None,
    },
]

ANALYSIS_AREAS = [
    {"icon": "whole-word", "title": "Linguistic analysis", "size": "span-2x1",
     "body": "Part-of-speech mix, lemmas and dependency structure show how each sentence is built, not just which words it uses."},
    {"icon": "fingerprint", "title": "Stylometry", "size": "",
     "body": "Measurable habits: sentence rhythm, punctuation, function words, formality."},
    {"icon": "sigma", "title": "Statistical signals", "size": "",
     "body": "Entropy, burstiness, n-gram frequency and TF-IDF weight."},
    {"icon": "waypoints", "title": "Semantic analysis", "size": "",
     "body": "Sentence embeddings reveal redundancy, coherence and how far ideas actually travel."},
    {"icon": "text-select", "title": "Sentence analysis", "size": "",
     "body": "Every sentence gets its own reading, so you can see where signals cluster."},
    {"icon": "message-square-quote", "title": "Explainability", "size": "span-2x1",
     "body": "Each score comes with the features behind it, in plain language. If the evidence is thin, the result says so."},
]

SIGNAL_FAMILIES = [
    {"name": "Linguistic", "example_score": 58, "detail": "POS balance, clause density, passive voice"},
    {"name": "Stylometric", "example_score": 44, "detail": "Rhythm, punctuation habits, formality"},
    {"name": "Statistical", "example_score": 71, "detail": "Entropy, burstiness, predictability"},
    {"name": "Semantic", "example_score": 63, "detail": "Redundancy, specificity, coherence"},
    {"name": "Structural", "example_score": 49, "detail": "Templates, transitions, paragraph shape"},
]

PROFILE_METRICS = [
    {"name": "Vocabulary diversity", "value": 72},
    {"name": "Sentence variation", "value": 61},
    {"name": "Syntax complexity", "value": 68},
    {"name": "Formality", "value": 81},
    {"name": "Repetition", "value": 29},
]

# Illustrative sentence-length histogram (bucket heights as % of the tallest).
SENTENCE_HISTOGRAM = [25, 40, 62, 88, 100, 84, 70, 52, 38, 26, 18, 10]

COMPARE_ROWS = [
    {"metric": "Words", "a": "612", "b": "548"},
    {"metric": "Mean sentence length", "a": "14.2", "b": "19.8"},
    {"metric": "Type-token ratio (MATTR)", "a": "0.71", "b": "0.63"},
    {"metric": "Transitions per 100 words", "a": "1.1", "b": "3.4"},
]

LIMITATIONS = [
    {"title": "What a result means", "icon": "eye",
     "body": "The text shares measurable characteristics with examples the model was trained on. That's all it measures."},
    {"title": "What it doesn't prove", "icon": "shield-off",
     "body": "Authorship, AI use, plagiarism, misconduct or intent. Treat a result as a prompt for conversation, never as a verdict."},
    {"title": "Probability isn't confidence", "icon": "gauge",
     "body": "Probability is the estimated signal. Confidence is how much the evidence supports that estimate. Short texts get \u201cInsufficient evidence\u201d."},
]

LANDING_CONTEXT = {
    "sample_document": SAMPLE_DOCUMENT,
    "analysis_areas": ANALYSIS_AREAS,
    "signal_families": SIGNAL_FAMILIES,
    "profile_metrics": PROFILE_METRICS,
    "compare_rows": COMPARE_ROWS,
    "sentence_histogram": SENTENCE_HISTOGRAM,
    "limitations": LIMITATIONS,
}
