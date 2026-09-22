"""
The spaCy pipeline, loaded once per process and reused.

Loading a model takes around a second; processing a page takes milliseconds.
get_nlp() is cached, so every request after the first reuses the same object.
NER is excluded because no feature uses named entities, which saves time.

Custom component: abbreviation boundaries
spaCy's parser keeps "at 5 p.m. It rained" as one sentence, because the full
stop after "p.m." both ends the abbreviation and the sentence. The rule below
marks a sentence start when a known sentence-final abbreviation is followed by
a capitalised pronoun, article or common sentence opener. It runs before the
parser, which treats the preset boundary as fixed.
"""
from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from spacy.language import Language

SENTENCE_FINAL_ABBREVIATIONS = {
    "a.m.", "p.m.", "etc.", "inc.", "ltd.", "co.", "corp.", "u.s.", "u.k.", "e.u.", "b.c.", "a.d.",
}
SENTENCE_OPENERS = {
    "it", "the", "a", "an", "this", "that", "these", "those", "there", "then", "he", "she", "they",
    "we", "i", "you", "his", "her", "their", "our", "my", "its", "but", "and", "so", "however",
    "after", "later", "when", "in", "on", "at", "by", "for", "yet", "still", "meanwhile",
}
COMPONENT_NAME = "abbreviation_boundaries"


@Language.component(COMPONENT_NAME)
def abbreviation_boundaries(doc):
    for token in doc[:-1]:
        nxt = doc[token.i + 1]
        if (
            token.text.lower() in SENTENCE_FINAL_ABBREVIATIONS
            and nxt.text[:1].isupper()
            and nxt.text.lower() in SENTENCE_OPENERS
        ):
            nxt.is_sent_start = True
    return doc


@lru_cache(maxsize=1)
def get_nlp() -> Language:
    import spacy

    nlp = spacy.load(settings.SPACY_MODEL, exclude=["ner"])
    nlp.add_pipe(COMPONENT_NAME, before="parser")
    return nlp
