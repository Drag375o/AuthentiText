# Limitations

AuthentiText measures characteristics of text. It does not prove authorship, AI use, plagiarism, misconduct or intent. This file lists known technical limits, and grows as the project does.

## Language

- **English only.** The pipeline uses an English spaCy model and English word frequencies. A lightweight check (the share of English function words) flags text that doesn't read as English; it isn't full language identification, and it can't judge texts under 20 words.

## Segmentation

- **Sentence-final abbreviations.** A custom rule handles common cases ("at 5 p.m. It rained"). Abbreviations outside its list, or followed by a word that isn't a typical sentence opener, may still merge two sentences.
- **Lists and headings.** Bulleted lists and headings without punctuation are treated as sentences if they sit on their own line or paragraph. They count toward sentence-length statistics.
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

## Measures

- **Short texts.** Most measures are unstable on short texts. MTLD needs at least 50 words; results under about 150 words will be reported as "Insufficient evidence" once the classifier exists.
- **Word frequency** comes from wordfreq's general-English corpus. Specialist vocabulary (medical, legal, technical) will look "rare" even when it's normal for its field.
