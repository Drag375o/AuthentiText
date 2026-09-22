# Features

Generated from `analyzer/services/features.py` by `python manage.py feature_docs --write`.
Don't edit this file by hand; change the registry and regenerate it.

## Document

| Name | Label | Unit | What it measures |
|---|---|---|---|
| `word_count` | Words | count | Word tokens, counting contractions like “can't” once. |
| `unique_word_count` | Unique words | count | Distinct word forms, ignoring case. |
| `sentence_count` | Sentences | count | Sentences found by spaCy's parser, never crossing a paragraph break. |
| `paragraph_count` | Paragraphs | count | Blocks separated by blank lines, or by line breaks if there are no blank lines. |
| `character_count` | Characters | count | All characters in the original text. |
| `reading_minutes` | Reading time | number | Minutes at 238 words per minute, rounded up. |
| `sentence_length_mean` | Mean sentence length | words | Average words per sentence. |
| `sentence_length_median` | Median sentence length | words | The middle sentence length; less affected by one very long sentence. |
| `sentence_length_std` | Sentence length spread | words | Standard deviation of sentence lengths. Higher means more varied rhythm. |
| `sentence_length_min` | Shortest sentence | words | Words in the shortest sentence. |
| `sentence_length_max` | Longest sentence | words | Words in the longest sentence. |
| `sentence_length_cv` | Sentence length variation | share (0-1, shown as %) | Spread divided by the mean, so texts with long and short average sentences can be compared. Low variation is common in careful editing as well as generated text; it isn't evidence on its own. |
| `paragraph_length_mean` | Mean paragraph length | words | Average words per paragraph. |
| `avg_word_length` | Average word length | number | Average letters per word. |
| `commas_per_100` | Commas | per 100 words | Commas per 100 words. |
| `semicolons_per_100` | Semicolons | per 100 words | Semicolons per 100 words. |
| `colons_per_100` | Colons | per 100 words | Colons per 100 words. |
| `dashes_per_100` | Dashes | per 100 words | Em dashes, en dashes and spaced hyphens per 100 words. |
| `questions_per_100` | Question marks | per 100 words | Question marks per 100 words. |
| `exclamations_per_100` | Exclamation marks | per 100 words | Exclamation marks per 100 words. |
| `parentheses_per_100` | Parentheses | per 100 words | Opening parentheses per 100 words. |
| `quotes_per_100` | Quotation marks | per 100 words | Quotation marks per 100 words. |
| `ellipses_per_100` | Ellipses | per 100 words | Ellipses per 100 words. |

## Lexical

| Name | Label | Unit | What it measures |
|---|---|---|---|
| `type_token_ratio` | Type-token ratio | share (0-1, shown as %) | Unique words divided by total words. Falls naturally as a text gets longer, so compare it only between texts of similar length. |
| `mattr` | Moving-average TTR | share (0-1, shown as %) | Type-token ratio averaged over every 50-word window. Unlike plain TTR, it stays comparable across texts of different lengths. |
| `mtld` | MTLD | number | Measure of Textual Lexical Diversity: roughly how many words it takes before vocabulary starts repeating. Higher means more varied vocabulary. Needs 50 or more words. |
| `hapax_ratio` | Words used once | share (0-1, shown as %) | Share of words that appear only once in the text. |
| `lexical_density` | Lexical density | share (0-1, shown as %) | Share of words that carry content (nouns, verbs, adjectives, adverbs) rather than grammar. |
| `function_word_ratio` | Function words | share (0-1, shown as %) | Share of words like “the”, “of” and “and” that hold sentences together. |
| `long_word_ratio` | Long words | share (0-1, shown as %) | Share of words with seven or more letters. |
| `rare_word_ratio` | Rare words | share (0-1, shown as %) | Share of words used less than about once per million words in general English (Zipf score under 3). Names and numbers are excluded. |
| `common_word_ratio` | Very common words | share (0-1, shown as %) | Share of words with a Zipf score of 5 or more, like “house”, “good” or “think”. |
| `mean_content_zipf` | Vocabulary frequency | Zipf score | Average Zipf frequency of content words. Lower means less everyday vocabulary. Everyday English sits around 4 to 5. |
| `repeated_phrase_count` | Repeated phrases | count | Distinct phrases of three or more words that appear more than once. |
| `repeated_phrase_coverage` | Text in repeated phrases | share (0-1, shown as %) | Share of words that sit inside a repeated phrase of three or more words. |

## Syntactic

| Name | Label | Unit | What it measures |
|---|---|---|---|
| `pos_noun_ratio` | Nouns | share (0-1, shown as %) | Share of words tagged as common nouns. |
| `pos_propn_ratio` | Proper nouns | share (0-1, shown as %) | Share of words that are names of people, places or organisations. |
| `pos_verb_ratio` | Verbs | share (0-1, shown as %) | Share of words tagged as main verbs. |
| `pos_adj_ratio` | Adjectives | share (0-1, shown as %) | Share of words tagged as adjectives. |
| `pos_adv_ratio` | Adverbs | share (0-1, shown as %) | Share of words tagged as adverbs. |
| `pos_pron_ratio` | Pronouns | share (0-1, shown as %) | Share of words tagged as pronouns, such as “I”, “it” or “they”. |
| `pos_det_ratio` | Determiners | share (0-1, shown as %) | Share of words like “the”, “a” and “this”. |
| `pos_conj_ratio` | Conjunctions | share (0-1, shown as %) | Share of coordinating and subordinating conjunctions, such as “and” or “because”. |
| `pos_adp_ratio` | Prepositions | share (0-1, shown as %) | Share of prepositions and postpositions, such as “in”, “of” or “with”. |
| `pos_aux_ratio` | Auxiliaries | share (0-1, shown as %) | Share of helping verbs, such as “is”, “have” or “will”. |
| `pos_num_ratio` | Numbers | share (0-1, shown as %) | Share of words that are numbers. |
| `parse_depth_mean` | Parse depth | number | Average depth of each sentence's dependency tree: how many layers of structure it nests. Deeper trees usually mean more embedded phrases and clauses. |
| `dependency_distance_mean` | Dependency distance | number | Average distance, in words, between each word and the word it attaches to (Liu, 2008). Longer distances are harder to process. |
| `clauses_per_sentence` | Clauses per sentence | number | Main clauses plus clauses attached to them, per sentence. Estimated from the dependency parse. |
| `subordinate_clauses_per_sentence` | Subordinate clauses | number | Clauses that depend on another, such as “because it rained” or “which nobody can read”, per sentence. |
| `coordination_per_sentence` | Coordination | number | Coordinating conjunctions (“and”, “but”, “or”) per sentence. |
| `passive_sentence_ratio` | Passive sentences | share (0-1, shown as %) | Share of sentences with a passive construction, such as “was eaten by”. “Get”-passives can be missed. |

## Linguistic

| Name | Label | Unit | What it measures |
|---|---|---|---|
| `transitions_per_100` | Transitions | per 100 words | Additive and sequencing transitions, such as “furthermore” or “in addition”, per 100 words. |
| `contrast_markers_per_100` | Contrast markers | per 100 words | Words like “however” or “although”, per 100 words. |
| `cause_effect_markers_per_100` | Cause and effect | per 100 words | Words like “therefore” or “because”, per 100 words. |
| `conclusion_markers_per_100` | Conclusion markers | per 100 words | Phrases like “in conclusion” or “ultimately”, per 100 words. |
| `emphasis_markers_per_100` | Emphasis markers | per 100 words | Words like “indeed” or “notably”, per 100 words. |
| `hedges_per_100` | Hedges | per 100 words | Words that soften a claim, such as “perhaps” or “might”, per 100 words. |
| `formulaic_phrases_per_100` | Formulaic phrases | per 100 words | Stock phrases from the pattern library, such as “it is important to note”, per 100 words. Common in many kinds of writing, so it's a signal to look at, not evidence. |
| `marker_initial_ratio` | Sentences opening with a marker | share (0-1, shown as %) | Share of sentences that begin with a discourse marker, such as “However,” or “So”. |

## Structural

| Name | Label | Unit | What it measures |
|---|---|---|---|
| `repeated_opening_ratio` | Repeated openings | share (0-1, shown as %) | Share of sentences whose first two words also open another sentence. Needs at least three sentences. |
| `opening_pattern_diversity` | Opening variety | share (0-1, shown as %) | Distinct grammatical openings (the part-of-speech pattern of the first three words) divided by the number of sentences. Higher means sentences begin in more varied ways. |

