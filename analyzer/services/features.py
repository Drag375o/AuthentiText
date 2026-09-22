"""
Feature registry: the single source of truth for every stored feature.

The document page, reports and docs/FEATURES.md read labels and explanations
from here, so an explanation can't drift away from the number it describes.
Units control display: count, words, ratio (shown as %), per100, zipf, number.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    category: str      # matches Feature.Category
    label: str
    unit: str
    description: str


FEATURES: list[FeatureSpec] = [
    # ---- Document ----
    FeatureSpec("word_count", "document", "Words", "count", "Word tokens, counting contractions like \u201ccan't\u201d once."),
    FeatureSpec("unique_word_count", "document", "Unique words", "count", "Distinct word forms, ignoring case."),
    FeatureSpec("sentence_count", "document", "Sentences", "count", "Sentences found by spaCy's parser, never crossing a paragraph break."),
    FeatureSpec("paragraph_count", "document", "Paragraphs", "count", "Blocks separated by blank lines, or by line breaks if there are no blank lines."),
    FeatureSpec("character_count", "document", "Characters", "count", "All characters in the original text."),
    FeatureSpec("reading_minutes", "document", "Reading time", "number", "Minutes at 238 words per minute, rounded up."),
    FeatureSpec("sentence_length_mean", "document", "Mean sentence length", "words", "Average words per sentence."),
    FeatureSpec("sentence_length_median", "document", "Median sentence length", "words", "The middle sentence length; less affected by one very long sentence."),
    FeatureSpec("sentence_length_std", "document", "Sentence length spread", "words", "Standard deviation of sentence lengths. Higher means more varied rhythm."),
    FeatureSpec("sentence_length_min", "document", "Shortest sentence", "words", "Words in the shortest sentence."),
    FeatureSpec("sentence_length_max", "document", "Longest sentence", "words", "Words in the longest sentence."),
    FeatureSpec("sentence_length_cv", "document", "Sentence length variation", "ratio",
                "Spread divided by the mean, so texts with long and short average sentences can be compared. Low variation is common in careful editing as well as generated text; it isn't evidence on its own."),
    FeatureSpec("paragraph_length_mean", "document", "Mean paragraph length", "words", "Average words per paragraph."),
    FeatureSpec("avg_word_length", "document", "Average word length", "number", "Average letters per word."),
    FeatureSpec("commas_per_100", "document", "Commas", "per100", "Commas per 100 words."),
    FeatureSpec("semicolons_per_100", "document", "Semicolons", "per100", "Semicolons per 100 words."),
    FeatureSpec("colons_per_100", "document", "Colons", "per100", "Colons per 100 words."),
    FeatureSpec("dashes_per_100", "document", "Dashes", "per100", "Em dashes, en dashes and spaced hyphens per 100 words."),
    FeatureSpec("questions_per_100", "document", "Question marks", "per100", "Question marks per 100 words."),
    FeatureSpec("exclamations_per_100", "document", "Exclamation marks", "per100", "Exclamation marks per 100 words."),
    FeatureSpec("parentheses_per_100", "document", "Parentheses", "per100", "Opening parentheses per 100 words."),
    FeatureSpec("quotes_per_100", "document", "Quotation marks", "per100", "Quotation marks per 100 words."),
    FeatureSpec("ellipses_per_100", "document", "Ellipses", "per100", "Ellipses per 100 words."),
    # ---- Lexical ----
    FeatureSpec("type_token_ratio", "lexical", "Type-token ratio", "ratio",
                "Unique words divided by total words. Falls naturally as a text gets longer, so compare it only between texts of similar length."),
    FeatureSpec("mattr", "lexical", "Moving-average TTR", "ratio",
                "Type-token ratio averaged over every 50-word window. Unlike plain TTR, it stays comparable across texts of different lengths."),
    FeatureSpec("mtld", "lexical", "MTLD", "number",
                "Measure of Textual Lexical Diversity: roughly how many words it takes before vocabulary starts repeating. Higher means more varied vocabulary. Needs 50 or more words."),
    FeatureSpec("hapax_ratio", "lexical", "Words used once", "ratio", "Share of words that appear only once in the text."),
    FeatureSpec("lexical_density", "lexical", "Lexical density", "ratio", "Share of words that carry content (nouns, verbs, adjectives, adverbs) rather than grammar."),
    FeatureSpec("function_word_ratio", "lexical", "Function words", "ratio", "Share of words like \u201cthe\u201d, \u201cof\u201d and \u201cand\u201d that hold sentences together."),
    FeatureSpec("long_word_ratio", "lexical", "Long words", "ratio", "Share of words with seven or more letters."),
    FeatureSpec("rare_word_ratio", "lexical", "Rare words", "ratio",
                "Share of words used less than about once per million words in general English (Zipf score under 3). Names and numbers are excluded."),
    FeatureSpec("common_word_ratio", "lexical", "Very common words", "ratio", "Share of words with a Zipf score of 5 or more, like \u201chouse\u201d, \u201cgood\u201d or \u201cthink\u201d."),
    FeatureSpec("mean_content_zipf", "lexical", "Vocabulary frequency", "zipf",
                "Average Zipf frequency of content words. Lower means less everyday vocabulary. Everyday English sits around 4 to 5."),
    FeatureSpec("repeated_phrase_count", "lexical", "Repeated phrases", "count", "Distinct phrases of three or more words that appear more than once."),
    FeatureSpec("repeated_phrase_coverage", "lexical", "Text in repeated phrases", "ratio", "Share of words that sit inside a repeated phrase of three or more words."),
]

BY_NAME: dict[str, FeatureSpec] = {f.name: f for f in FEATURES}
