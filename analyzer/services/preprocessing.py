"""
Preprocessing: original text -> ProcessedDocument.

The original text is never modified. spaCy runs on each paragraph separately
(so a sentence never crosses a paragraph break), and every token and sentence
keeps absolute character offsets into the original. Normalised forms (lower
case, NFC, straight apostrophes) exist only in the processed representation.

Word tokens: not punctuation or whitespace, and containing a letter or digit.
Clitics split off by spaCy ("n't", "'s", "'re" ...) are kept as tokens but not
counted as separate words, so "can't" is one word, as in the editor's counts.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from spacy.lang.en.stop_words import STOP_WORDS

from .nlp import get_nlp
from .segmentation import paragraph_spans

CLITICS = {"n't", "'s", "'re", "'ve", "'ll", "'d", "'m", "s"}
CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV"}
ENGLISH_MIN_WORDS = 20
ENGLISH_MIN_STOPWORD_RATIO = 0.2


def normalize_form(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower().replace("\u2019", "'").replace("\u2018", "'")


@dataclass(frozen=True)
class Token:
    text: str
    norm: str          # normalised form used for vocabulary counts
    lemma: str
    pos: str
    tag: str
    dep: str
    index: int         # spaCy's position within the sentence (whitespace tokens included)
    head: int          # spaCy position of the head token within the sentence
    start: int         # absolute offsets into the original text
    end: int
    is_punct: bool
    is_stop: bool
    is_alpha: bool
    like_num: bool
    is_word: bool      # counts as a word (clitics excluded)
    is_clitic: bool

    @property
    def is_content(self) -> bool:
        return self.is_word and self.pos in CONTENT_POS


@dataclass
class Sentence:
    index: int
    paragraph: int
    start: int
    end: int
    tokens: list[Token] = field(default_factory=list)

    @property
    def words(self) -> list[Token]:
        return [t for t in self.tokens if t.is_word]


@dataclass
class ProcessedDocument:
    original_text: str
    paragraphs: list[tuple[int, int]]
    sentences: list[Sentence]
    language: str              # "en", or "und" when the text doesn't read as English
    language_checked: bool     # False when too short to tell

    @property
    def tokens(self) -> list[Token]:
        return [t for s in self.sentences for t in s.tokens]

    @property
    def words(self) -> list[Token]:
        return [t for s in self.sentences for t in s.words]

    def text_of(self, start: int, end: int) -> str:
        return self.original_text[start:end]


def _make_token(tok, offset: int, sentence_start_i: int) -> Token:
    norm = normalize_form(tok.norm_ or tok.text)
    is_clitic = normalize_form(tok.text) in CLITICS and tok.i > 0 and tok.nbor(-1).whitespace_ == ""
    has_alnum = any(ch.isalnum() for ch in tok.text)
    is_word = not tok.is_punct and not tok.is_space and has_alnum and not is_clitic
    return Token(
        text=tok.text,
        norm=norm,
        lemma=normalize_form(tok.lemma_),
        pos=tok.pos_,
        tag=tok.tag_,
        dep=tok.dep_,
        index=tok.i - sentence_start_i,
        head=tok.head.i - sentence_start_i,
        start=offset + tok.idx,
        end=offset + tok.idx + len(tok.text),
        is_punct=tok.is_punct,
        is_stop=norm in STOP_WORDS,
        is_alpha=tok.is_alpha,
        like_num=tok.like_num,
        is_word=is_word,
        is_clitic=is_clitic,
    )


def detect_language(words: list[Token]) -> tuple[str, bool]:
    """A lightweight English check (share of English function words), not full language ID."""
    if len(words) < ENGLISH_MIN_WORDS:
        return "en", False
    ratio = sum(1 for w in words if w.is_stop) / len(words)
    return ("en" if ratio >= ENGLISH_MIN_STOPWORD_RATIO else "und"), True


def preprocess(text: str) -> ProcessedDocument:
    nlp = get_nlp()
    paragraphs = paragraph_spans(text)
    sentences: list[Sentence] = []
    for p_index, ((p_start, p_end), doc) in enumerate(
        zip(paragraphs, nlp.pipe(text[s:e] for s, e in paragraphs))
    ):
        for sent in doc.sents:
            tokens = [_make_token(t, p_start, sent.start) for t in sent if not t.is_space]
            if not any(t.is_word for t in tokens):
                continue
            sentences.append(Sentence(
                index=len(sentences),
                paragraph=p_index,
                start=tokens[0].start,
                end=tokens[-1].end,
                tokens=tokens,
            ))
    words = [w for s in sentences for w in s.words]
    language, checked = detect_language(words)
    return ProcessedDocument(text, paragraphs, sentences, language, checked)
