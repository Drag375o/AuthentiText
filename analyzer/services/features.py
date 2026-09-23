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
    # Why this feature is sometimes not measurable. Shown instead of a blank
    # value, so an empty cell never looks like a broken page.
    unavailable: str = ""


FEATURES: list[FeatureSpec] = [
    # ---- Document ----
    FeatureSpec("word_count", "document", "Words", "count", "Word tokens, counting contractions like \u201ccan't\u201d once."),
    FeatureSpec("unique_word_count", "document", "Unique words", "count", "Distinct word forms, ignoring case."),
    FeatureSpec("sentence_count", "document", "Sentences", "count", "Sentences found by spaCy's parser, never crossing a paragraph break."),
    FeatureSpec("heading_count", "document", "Headings", "count",
                "Short lines without sentence-ending punctuation. They are excluded from every sentence-length measure, because a heading is not a sentence."),
    FeatureSpec("paragraph_count", "document", "Paragraphs", "count", "Blocks separated by blank lines, or by line breaks if there are no blank lines."),
    FeatureSpec("character_count", "document", "Characters", "count", "All characters in the original text."),
    FeatureSpec("reading_minutes", "document", "Reading time", "number", "Minutes at 238 words per minute, rounded up."),
    FeatureSpec("sentence_length_mean", "document", "Mean sentence length", "words", "Average words per sentence, excluding headings."),
    FeatureSpec("sentence_length_median", "document", "Median sentence length", "words", "The middle sentence length; less affected by one very long sentence."),
    FeatureSpec("sentence_length_std", "document", "Sentence length spread", "words", "Standard deviation of sentence lengths, excluding headings. Higher means more varied rhythm."),
    FeatureSpec("sentence_length_min", "document", "Shortest sentence", "words", "Words in the shortest sentence."),
    FeatureSpec("sentence_length_max", "document", "Longest sentence", "words", "Words in the longest sentence."),
    FeatureSpec("sentence_length_cv", "document", "Sentence length variation", "ratio",
                "Spread divided by the mean, so texts with long and short average sentences can be compared. Low variation is common in careful editing as well as generated text; it isn't evidence on its own.", unavailable="Needs at least one sentence, excluding headings."),
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
                "Measure of Textual Lexical Diversity: roughly how many words it takes before vocabulary starts repeating. Higher means more varied vocabulary. Needs 50 or more words.", unavailable="Needs at least 50 words."),
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
    # ---- Syntactic ----
    FeatureSpec("pos_noun_ratio", "syntactic", "Nouns", "ratio", "Share of words tagged as common nouns."),
    FeatureSpec("pos_propn_ratio", "syntactic", "Proper nouns", "ratio", "Share of words that are names of people, places or organisations."),
    FeatureSpec("pos_verb_ratio", "syntactic", "Verbs", "ratio", "Share of words tagged as main verbs."),
    FeatureSpec("pos_adj_ratio", "syntactic", "Adjectives", "ratio", "Share of words tagged as adjectives."),
    FeatureSpec("pos_adv_ratio", "syntactic", "Adverbs", "ratio", "Share of words tagged as adverbs."),
    FeatureSpec("pos_pron_ratio", "syntactic", "Pronouns", "ratio", "Share of words tagged as pronouns, such as \u201cI\u201d, \u201cit\u201d or \u201cthey\u201d."),
    FeatureSpec("pos_det_ratio", "syntactic", "Determiners", "ratio", "Share of words like \u201cthe\u201d, \u201ca\u201d and \u201cthis\u201d."),
    FeatureSpec("pos_conj_ratio", "syntactic", "Conjunctions", "ratio", "Share of coordinating and subordinating conjunctions, such as \u201cand\u201d or \u201cbecause\u201d."),
    FeatureSpec("pos_adp_ratio", "syntactic", "Prepositions", "ratio", "Share of prepositions and postpositions, such as \u201cin\u201d, \u201cof\u201d or \u201cwith\u201d."),
    FeatureSpec("pos_aux_ratio", "syntactic", "Auxiliaries", "ratio", "Share of helping verbs, such as \u201cis\u201d, \u201chave\u201d or \u201cwill\u201d."),
    FeatureSpec("pos_num_ratio", "syntactic", "Numbers", "ratio", "Share of words that are numbers."),
    FeatureSpec("parse_depth_mean", "syntactic", "Parse depth", "number",
                "Average depth of each sentence's dependency tree: how many layers of structure it nests. Deeper trees usually mean more embedded phrases and clauses."),
    FeatureSpec("dependency_distance_mean", "syntactic", "Dependency distance", "number",
                "Average distance, in words, between each word and the word it attaches to (Liu, 2008). Longer distances are harder to process."),
    FeatureSpec("clauses_per_sentence", "syntactic", "Clauses per sentence", "number",
                "Main clauses plus clauses attached to them, per sentence. Estimated from the dependency parse."),
    FeatureSpec("subordinate_clauses_per_sentence", "syntactic", "Subordinate clauses", "number",
                "Clauses that depend on another, such as \u201cbecause it rained\u201d or \u201cwhich nobody can read\u201d, per sentence."),
    FeatureSpec("coordination_per_sentence", "syntactic", "Coordination", "number", "Coordinating conjunctions (\u201cand\u201d, \u201cbut\u201d, \u201cor\u201d) per sentence."),
    FeatureSpec("passive_sentence_ratio", "syntactic", "Passive sentences", "ratio",
                "Share of sentences with a passive construction, such as \u201cwas eaten by\u201d. \u201cGet\u201d-passives can be missed."),
    # ---- Linguistic (discourse) ----
    FeatureSpec("transitions_per_100", "linguistic", "Transitions", "per100", "Additive and sequencing transitions, such as \u201cfurthermore\u201d or \u201cin addition\u201d, per 100 words."),
    FeatureSpec("contrast_markers_per_100", "linguistic", "Contrast markers", "per100", "Words like \u201chowever\u201d or \u201calthough\u201d, per 100 words."),
    FeatureSpec("cause_effect_markers_per_100", "linguistic", "Cause and effect", "per100", "Words like \u201ctherefore\u201d or \u201cbecause\u201d, per 100 words."),
    FeatureSpec("conclusion_markers_per_100", "linguistic", "Conclusion markers", "per100", "Phrases like \u201cin conclusion\u201d or \u201cultimately\u201d, per 100 words."),
    FeatureSpec("emphasis_markers_per_100", "linguistic", "Emphasis markers", "per100", "Words like \u201cindeed\u201d or \u201cnotably\u201d, per 100 words."),
    FeatureSpec("hedges_per_100", "linguistic", "Hedges", "per100", "Words that soften a claim, such as \u201cperhaps\u201d or \u201cmight\u201d, per 100 words."),
    FeatureSpec("formulaic_phrases_per_100", "linguistic", "Formulaic phrases", "per100",
                "Stock phrases from the pattern library, such as \u201cit is important to note\u201d, per 100 words. Common in many kinds of writing, so it's a signal to look at, not evidence."),
    FeatureSpec("marker_initial_ratio", "linguistic", "Sentences opening with a marker", "ratio", "Share of sentences that begin with a discourse marker, such as \u201cHowever,\u201d or \u201cSo\u201d."),
    # ---- Structural ----
    FeatureSpec("repeated_opening_ratio", "structural", "Repeated openings", "ratio", "Share of sentences whose first two words also open another sentence. Needs at least three sentences.", unavailable="Needs at least three sentences of two words or more."),
    # ---- Statistical ----
    FeatureSpec("word_entropy", "statistical", "Word entropy", "number",
                "Shannon entropy of the word distribution, in bits: how unpredictable the next word is, given only how often each word appears. Longer texts naturally score higher."),
    FeatureSpec("normalized_entropy", "statistical", "Entropy, normalised", "ratio",
                "Word entropy divided by the maximum possible for this vocabulary size, so texts of different lengths can be compared. Near 100% means words are spread evenly; lower means a few words dominate.", unavailable="Needs at least two distinct words."),
    FeatureSpec("sentence_length_burstiness", "statistical", "Burstiness", "number",
                "Unevenness of sentence lengths on a scale from -1 to +1 (Goh & Barabasi, 2008). -1 is perfectly regular, 0 is random-like, and positive values mean bursts of short and long sentences. Regular rhythm alone is not evidence of anything.", unavailable="Needs at least three sentences, excluding headings."),
    FeatureSpec("bigram_repeat_rate", "statistical", "Repeated word pairs", "ratio", "Share of two-word sequences that occur more than once."),
    FeatureSpec("trigram_repeat_rate", "statistical", "Repeated word triples", "ratio", "Share of three-word sequences that occur more than once."),
    FeatureSpec("zipf_slope", "statistical", "Frequency slope", "number",
                "Slope of word frequency against rank on a log scale. Natural English text sits near -1; a flatter slope means no small set of words dominates.", unavailable="Needs at least ten distinct words."),
    # ---- Semantic ----
    FeatureSpec("local_coherence", "semantic", "Local coherence", "ratio",
                "Average similarity between neighbouring sentences. Very low means the text jumps between ideas; very high means consecutive sentences restate each other.", unavailable="Needs at least four sentences."),
    FeatureSpec("paragraph_coherence", "semantic", "Paragraph coherence", "ratio", "How closely each sentence sits to the average of its own paragraph.", unavailable="Needs a paragraph containing at least two sentences."),
    FeatureSpec("semantic_redundancy", "semantic", "Redundancy", "ratio", "Share of sentence pairs similar enough to count as near-duplicates.", unavailable="Needs at least four sentences."),
    FeatureSpec("semantic_diversity", "semantic", "Semantic diversity", "ratio", "How much sentences differ from one another overall. Higher means the text covers more ground.", unavailable="Needs at least four sentences."),
    FeatureSpec("opening_closing_similarity", "semantic", "Opening and closing", "ratio", "Similarity between the first and last paragraphs. High values mean the ending returns to where the text began.", unavailable="Needs at least two paragraphs: a single-paragraph text has no separate opening and closing."),
    FeatureSpec("max_sentence_similarity", "semantic", "Closest sentence pair", "ratio", "The highest similarity between any two sentences in the text.", unavailable="Needs at least four sentences."),
    # ---- Stylometric ----
    FeatureSpec("formality_score", "stylometric", "Formality (F-score)", "number",
                "Heylighen & Dewaele's F-score from part-of-speech shares: nouns, adjectives, prepositions and articles raise it; pronouns, verbs and adverbs lower it. Around 50 is neutral, academic writing runs higher, conversation lower.", unavailable="Needs at least one word."),
    FeatureSpec("first_person_ratio", "stylometric", "First-person pronouns", "ratio", "Share of words that are first-person pronouns such as \u201cI\u201d, \u201cmy\u201d or \u201cwe\u201d."),
    FeatureSpec("contraction_ratio", "stylometric", "Contractions", "ratio", "Contractions such as \u201ccan't\u201d or \u201cit's\u201d, as a share of words."),
    FeatureSpec("opening_pattern_diversity", "structural", "Opening variety", "ratio",
                "Distinct grammatical openings (the part-of-speech pattern of the first three words) divided by the number of sentences. Higher means sentences begin in more varied ways.", unavailable="Needs at least three sentences of two words or more."),
]

BY_NAME: dict[str, FeatureSpec] = {f.name: f for f in FEATURES}
