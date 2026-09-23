# Features

Generated from `analyzer/services/features.py` by `python manage.py feature_docs --write`.
Don't edit this file by hand; change the registry and regenerate it.

## Document

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `word_count` | Words | count | Word tokens, counting contractions like “can't” once. | always available |
| `unique_word_count` | Unique words | count | Distinct word forms, ignoring case. | always available |
| `sentence_count` | Sentences | count | Sentences found by spaCy's parser, never crossing a paragraph break. | always available |
| `heading_count` | Headings | count | Short lines without sentence-ending punctuation. They are excluded from every sentence-length measure, because a heading is not a sentence. | always available |
| `paragraph_count` | Paragraphs | count | Blocks separated by blank lines, or by line breaks if there are no blank lines. | always available |
| `character_count` | Characters | count | All characters in the original text. | always available |
| `reading_minutes` | Reading time | number | Minutes at 238 words per minute, rounded up. | always available |
| `sentence_length_mean` | Mean sentence length | words | Average words per sentence, excluding headings. | always available |
| `sentence_length_median` | Median sentence length | words | The middle sentence length; less affected by one very long sentence. | always available |
| `sentence_length_std` | Sentence length spread | words | Standard deviation of sentence lengths, excluding headings. Higher means more varied rhythm. | always available |
| `sentence_length_min` | Shortest sentence | words | Words in the shortest sentence. | always available |
| `sentence_length_max` | Longest sentence | words | Words in the longest sentence. | always available |
| `sentence_length_cv` | Sentence length variation | share (0-1, shown as %) | Spread divided by the mean, so texts with long and short average sentences can be compared. Low variation is common in careful editing as well as generated text; it isn't evidence on its own. | Needs at least one sentence, excluding headings. |
| `paragraph_length_mean` | Mean paragraph length | words | Average words per paragraph. | always available |
| `avg_word_length` | Average word length | number | Average letters per word. | always available |
| `commas_per_100` | Commas | per 100 words | Commas per 100 words. | always available |
| `semicolons_per_100` | Semicolons | per 100 words | Semicolons per 100 words. | always available |
| `colons_per_100` | Colons | per 100 words | Colons per 100 words. | always available |
| `dashes_per_100` | Dashes | per 100 words | Em dashes, en dashes and spaced hyphens per 100 words. | always available |
| `questions_per_100` | Question marks | per 100 words | Question marks per 100 words. | always available |
| `exclamations_per_100` | Exclamation marks | per 100 words | Exclamation marks per 100 words. | always available |
| `parentheses_per_100` | Parentheses | per 100 words | Opening parentheses per 100 words. | always available |
| `quotes_per_100` | Quotation marks | per 100 words | Quotation marks per 100 words. | always available |
| `ellipses_per_100` | Ellipses | per 100 words | Ellipses per 100 words. | always available |

## Lexical

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `type_token_ratio` | Type-token ratio | share (0-1, shown as %) | Unique words divided by total words. Falls naturally as a text gets longer, so compare it only between texts of similar length. | always available |
| `mattr` | Moving-average TTR | share (0-1, shown as %) | Type-token ratio averaged over every 50-word window. Unlike plain TTR, it stays comparable across texts of different lengths. | always available |
| `mtld` | MTLD | number | Measure of Textual Lexical Diversity: roughly how many words it takes before vocabulary starts repeating. Higher means more varied vocabulary. Needs 50 or more words. | Needs at least 50 words. |
| `hapax_ratio` | Words used once | share (0-1, shown as %) | Share of words that appear only once in the text. | always available |
| `lexical_density` | Lexical density | share (0-1, shown as %) | Share of words that carry content (nouns, verbs, adjectives, adverbs) rather than grammar. | always available |
| `function_word_ratio` | Function words | share (0-1, shown as %) | Share of words like “the”, “of” and “and” that hold sentences together. | always available |
| `long_word_ratio` | Long words | share (0-1, shown as %) | Share of words with seven or more letters. | always available |
| `rare_word_ratio` | Rare words | share (0-1, shown as %) | Share of words used less than about once per million words in general English (Zipf score under 3). Names and numbers are excluded. | always available |
| `common_word_ratio` | Very common words | share (0-1, shown as %) | Share of words with a Zipf score of 5 or more, like “house”, “good” or “think”. | always available |
| `mean_content_zipf` | Vocabulary frequency | Zipf score | Average Zipf frequency of content words. Lower means less everyday vocabulary. Everyday English sits around 4 to 5. | always available |
| `repeated_phrase_count` | Repeated phrases | count | Distinct phrases of three or more words that appear more than once. | always available |
| `repeated_phrase_coverage` | Text in repeated phrases | share (0-1, shown as %) | Share of words that sit inside a repeated phrase of three or more words. | always available |

## Syntactic

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `pos_noun_ratio` | Nouns | share (0-1, shown as %) | Share of words tagged as common nouns. | always available |
| `pos_propn_ratio` | Proper nouns | share (0-1, shown as %) | Share of words that are names of people, places or organisations. | always available |
| `pos_verb_ratio` | Verbs | share (0-1, shown as %) | Share of words tagged as main verbs. | always available |
| `pos_adj_ratio` | Adjectives | share (0-1, shown as %) | Share of words tagged as adjectives. | always available |
| `pos_adv_ratio` | Adverbs | share (0-1, shown as %) | Share of words tagged as adverbs. | always available |
| `pos_pron_ratio` | Pronouns | share (0-1, shown as %) | Share of words tagged as pronouns, such as “I”, “it” or “they”. | always available |
| `pos_det_ratio` | Determiners | share (0-1, shown as %) | Share of words like “the”, “a” and “this”. | always available |
| `pos_conj_ratio` | Conjunctions | share (0-1, shown as %) | Share of coordinating and subordinating conjunctions, such as “and” or “because”. | always available |
| `pos_adp_ratio` | Prepositions | share (0-1, shown as %) | Share of prepositions and postpositions, such as “in”, “of” or “with”. | always available |
| `pos_aux_ratio` | Auxiliaries | share (0-1, shown as %) | Share of helping verbs, such as “is”, “have” or “will”. | always available |
| `pos_num_ratio` | Numbers | share (0-1, shown as %) | Share of words that are numbers. | always available |
| `parse_depth_mean` | Parse depth | number | Average depth of each sentence's dependency tree: how many layers of structure it nests. Deeper trees usually mean more embedded phrases and clauses. | always available |
| `dependency_distance_mean` | Dependency distance | number | Average distance, in words, between each word and the word it attaches to (Liu, 2008). Longer distances are harder to process. | always available |
| `clauses_per_sentence` | Clauses per sentence | number | Main clauses plus clauses attached to them, per sentence. Estimated from the dependency parse. | always available |
| `subordinate_clauses_per_sentence` | Subordinate clauses | number | Clauses that depend on another, such as “because it rained” or “which nobody can read”, per sentence. | always available |
| `coordination_per_sentence` | Coordination | number | Coordinating conjunctions (“and”, “but”, “or”) per sentence. | always available |
| `passive_sentence_ratio` | Passive sentences | share (0-1, shown as %) | Share of sentences with a passive construction, such as “was eaten by”. “Get”-passives can be missed. | always available |

## Linguistic

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `transitions_per_100` | Transitions | per 100 words | Additive and sequencing transitions, such as “furthermore” or “in addition”, per 100 words. | always available |
| `contrast_markers_per_100` | Contrast markers | per 100 words | Words like “however” or “although”, per 100 words. | always available |
| `cause_effect_markers_per_100` | Cause and effect | per 100 words | Words like “therefore” or “because”, per 100 words. | always available |
| `conclusion_markers_per_100` | Conclusion markers | per 100 words | Phrases like “in conclusion” or “ultimately”, per 100 words. | always available |
| `emphasis_markers_per_100` | Emphasis markers | per 100 words | Words like “indeed” or “notably”, per 100 words. | always available |
| `hedges_per_100` | Hedges | per 100 words | Words that soften a claim, such as “perhaps” or “might”, per 100 words. | always available |
| `formulaic_phrases_per_100` | Formulaic phrases | per 100 words | Stock phrases from the pattern library, such as “it is important to note”, per 100 words. Common in many kinds of writing, so it's a signal to look at, not evidence. | always available |
| `marker_initial_ratio` | Sentences opening with a marker | share (0-1, shown as %) | Share of sentences that begin with a discourse marker, such as “However,” or “So”. | always available |

## Structural

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `repeated_opening_ratio` | Repeated openings | share (0-1, shown as %) | Share of sentences whose first two words also open another sentence. Needs at least three sentences. | Needs at least three sentences of two words or more. |
| `opening_pattern_diversity` | Opening variety | share (0-1, shown as %) | Distinct grammatical openings (the part-of-speech pattern of the first three words) divided by the number of sentences. Higher means sentences begin in more varied ways. | Needs at least three sentences of two words or more. |

## Statistical

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `word_entropy` | Word entropy | number | Shannon entropy of the word distribution, in bits: how unpredictable the next word is, given only how often each word appears. Longer texts naturally score higher. | always available |
| `normalized_entropy` | Entropy, normalised | share (0-1, shown as %) | Word entropy divided by the maximum possible for this vocabulary size, so texts of different lengths can be compared. Near 100% means words are spread evenly; lower means a few words dominate. | Needs at least two distinct words. |
| `sentence_length_burstiness` | Burstiness | number | Unevenness of sentence lengths on a scale from -1 to +1 (Goh & Barabasi, 2008). -1 is perfectly regular, 0 is random-like, and positive values mean bursts of short and long sentences. Regular rhythm alone is not evidence of anything. | Needs at least three sentences, excluding headings. |
| `bigram_repeat_rate` | Repeated word pairs | share (0-1, shown as %) | Share of two-word sequences that occur more than once. | always available |
| `trigram_repeat_rate` | Repeated word triples | share (0-1, shown as %) | Share of three-word sequences that occur more than once. | always available |
| `zipf_slope` | Frequency slope | number | Slope of word frequency against rank on a log scale. Natural English text sits near -1; a flatter slope means no small set of words dominates. | Needs at least ten distinct words. |

## Semantic

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `local_coherence` | Local coherence | share (0-1, shown as %) | Average similarity between neighbouring sentences. Very low means the text jumps between ideas; very high means consecutive sentences restate each other. | Needs at least four sentences. |
| `paragraph_coherence` | Paragraph coherence | share (0-1, shown as %) | How closely each sentence sits to the average of its own paragraph. | Needs a paragraph containing at least two sentences. |
| `semantic_redundancy` | Redundancy | share (0-1, shown as %) | Share of sentence pairs similar enough to count as near-duplicates. | Needs at least four sentences. |
| `semantic_diversity` | Semantic diversity | share (0-1, shown as %) | How much sentences differ from one another overall. Higher means the text covers more ground. | Needs at least four sentences. |
| `opening_closing_similarity` | Opening and closing | share (0-1, shown as %) | Similarity between the first and last paragraphs. High values mean the ending returns to where the text began. | Needs at least two paragraphs: a single-paragraph text has no separate opening and closing. |
| `max_sentence_similarity` | Closest sentence pair | share (0-1, shown as %) | The highest similarity between any two sentences in the text. | Needs at least four sentences. |

## Stylometric

| Name | Label | Unit | What it measures | Not measured when |
|---|---|---|---|---|
| `formality_score` | Formality (F-score) | number | Heylighen & Dewaele's F-score from part-of-speech shares: nouns, adjectives, prepositions and articles raise it; pronouns, verbs and adverbs lower it. Around 50 is neutral, academic writing runs higher, conversation lower. | Needs at least one word. |
| `first_person_ratio` | First-person pronouns | share (0-1, shown as %) | Share of words that are first-person pronouns such as “I”, “my” or “we”. | always available |
| `contraction_ratio` | Contractions | share (0-1, shown as %) | Contractions such as “can't” or “it's”, as a share of words. | always available |

