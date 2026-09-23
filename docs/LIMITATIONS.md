# Limitations

AuthentiText measures characteristics of text. It does not prove authorship, AI use, plagiarism, misconduct or intent. This file lists known technical limits, and grows as the project does.

## Detection

- **The shipped detector is a demo with no measured accuracy.** Its weights and thresholds were chosen by hand, not learned from data. Treat its numbers as an illustration of the interface, not as evidence about any document.
- **No result identifies authorship.** Every signal the system measures occurs in human writing. A high score means the text shares measurable characteristics with AI-generated examples, nothing more.
- **Genre confounds everything.** Formality, personal voice and contraction use say more about register than about who wrote a text. A lab report and a diary differ far more than two authors do.
- **Adversarial editing is not handled.** A few edits to sentence lengths and connectives will move these scores substantially.
- **Rewritten text scores lower than the human original.** In testing, AI rewrites of human documents consistently scored *below* the originals, because a rewrite repeats itself less than natural writing does. Text generated from a prompt behaves differently and does score higher. See [EVALUATION.md](EVALUATION.md).

## Language

- **English only.** The pipeline uses an English spaCy model and English word frequencies. A lightweight check (the share of English function words) flags text that doesn't read as English; it isn't full language identification, and it can't judge texts under 20 words.

## Segmentation

- **Sentence-final abbreviations.** A custom rule handles common cases ("at 5 p.m. It rained"). Abbreviations outside its list, or followed by a word that isn't a typical sentence opener, may still merge two sentences.
- **Hard-wrapped text.** Text copied from a PDF arrives with a line break every 70-odd characters. AuthentiText rejoins those lines when a break falls inside a sentence (the line before lacks ending punctuation and the line after starts in lower case). Words hyphenated across a line break ("annota-\ntion") are still counted as two words, because the original text is never modified.
- **Headings** are detected as short lines (12 words or fewer) with no sentence-ending punctuation. They count as sentences in every measure and are reported separately, since they are short and pull the mean sentence length down. A short sentence that is a whole paragraph and ends without punctuation would be misread as a heading.
- **Bulleted list items** are still treated as sentences and counted in sentence-length statistics.
- **Quick counts versus analysis.** The editor's live counts use simple rules; the analysis uses spaCy. Sentence counts can differ slightly between them. The saved document uses the analysis counts.

## Syntax

- **Parser accuracy.** Part-of-speech tags and dependencies come from `en_core_web_sm`, a small statistical model. It's usually right on edited prose and less reliable on fragments, lists, very informal writing and long, heavily punctuated sentences.
- **Passive voice** is detected from parser labels, so "get"-passives ("got fired") and reduced passives ("the book, written in 1990") are usually missed.
- **Clause counts** are estimates from dependency labels, not a full grammatical analysis.

## Patterns

- **Register bias.** The library leans toward English expository and academic writing. Its "formulaic" phrases are common in human writing too: students, journalists and business writers use them all the time.
- **Matches aren't evidence.** A pattern match means a phrase appears; it says nothing about who wrote it or how. The "strength" field describes how generic a phrase is, not how likely it is to be AI-written.
- **Surface matching.** Patterns match exact word sequences, so paraphrases ("it's worth pointing out") and discontinuous templates ("not only … but also", beyond the "not only" part) aren't fully captured.

## Extraction

- **PDF layout.** Multi-column layouts, footnotes and running headers can appear in reading order imperfectly. Scanned PDFs have no text to extract; OCR isn't supported.
- **DOCX.** Tables, headers, footers, footnotes and text boxes are skipped.

## Statistical and semantic measures

- **No perplexity.** AuthentiText ships no language model, so it does not report perplexity or token-level predictability. Word entropy measures how evenly words are distributed, which is related but much weaker: it knows nothing about word order or context.
- **Default semantics are lexical.** Without `sentence-transformers` installed, sentence similarity is TF-IDF: it compares which words sentences share. Two sentences that say the same thing in different words will look unrelated, and two sentences that share rare vocabulary while making opposite claims will look similar. The document page always names the backend in use.
- **Burstiness and entropy vary with length and genre.** Short texts, lists and dialogue all shift them. Compare documents of similar length and kind.
- **Profile anchors are reference ranges,** picked by hand for ordinary English prose, not percentiles from a corpus. A score of 80 means "high within that range", not "higher than 80% of writers". Genre moves every dimension: a lab report and a diary should score differently.
- **Formality** uses the F-score, which counts parts of speech. It captures register but not politeness, tone or audience.

## Measures

- **Short texts.** Most measures are unstable on short texts. MTLD needs at least 50 words; results under about 150 words will be reported as "Insufficient evidence" once the classifier exists.
- **Word frequency** comes from wordfreq's general-English corpus. Specialist vocabulary (medical, legal, technical) will look "rare" even when it's normal for its field.
