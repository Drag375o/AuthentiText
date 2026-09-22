"""Phase 4: segmentation, preprocessing, document statistics, lexical features."""
import math

from django.test import SimpleTestCase

from analyzer.services.document_stats import compute_document_stats
from analyzer.services.features import BY_NAME, FEATURES
from analyzer.services.lexical import compute_lexical, mattr, mtld, repeated_phrases, type_token_ratio, zipf
from analyzer.services.pipeline import run_pipeline
from analyzer.services.preprocessing import preprocess
from analyzer.services.segmentation import paragraph_spans


def sentences(text):
    doc = preprocess(text)
    return [doc.text_of(s.start, s.end) for s in doc.sentences]


class SegmentationTests(SimpleTestCase):
    def test_paragraph_spans_slice_the_original_exactly(self):
        text = "  First para,\r\nstill first.\r\n\r\n\r\n  Second para.  \n\n***\n\nThird."
        spans = paragraph_spans(text)
        self.assertEqual([text[s:e] for s, e in spans], ["First para,\r\nstill first.", "Second para.", "Third."])

    def test_line_break_mode_without_blank_lines(self):
        self.assertEqual(len(paragraph_spans("One\nTwo\nThree")), 3)

    def test_abbreviations_inside_sentences(self):
        self.assertEqual(sentences("Dr. Rahman arrived late. It rained, e.g. all day."),
                         ["Dr. Rahman arrived late.", "It rained, e.g. all day."])
        self.assertEqual(len(sentences("Dr. Smith and Mr. Jones met Prof. Lee.")), 1)

    def test_custom_rule_splits_after_sentence_final_abbreviation(self):
        self.assertEqual(sentences("Dr. Rahman arrived at 5 p.m. It rained all day."),
                         ["Dr. Rahman arrived at 5 p.m.", "It rained all day."])
        self.assertEqual(sentences("He works at Acme Inc. The office is small."),
                         ["He works at Acme Inc.", "The office is small."])

    def test_custom_rule_leaves_mid_sentence_abbreviations(self):
        self.assertEqual(len(sentences("We met at 5 p.m. the next day.")), 1)
        self.assertEqual(len(sentences("The U.S. Army arrived early.")), 1)

    def test_sentences_never_cross_paragraphs(self):
        # A heading without a full stop must not merge with the next paragraph.
        self.assertEqual(sentences("A Heading Without A Stop\n\nThe body starts here."),
                         ["A Heading Without A Stop", "The body starts here."])


class PreprocessingTests(SimpleTestCase):
    def test_offsets_point_into_untouched_original(self):
        text = "  I can\u2019t go.\r\n\r\nCaf\u00e9s close at 9."
        doc = preprocess(text)
        self.assertEqual(doc.original_text, text)
        for token in doc.tokens:
            self.assertEqual(text[token.start:token.end], token.text)

    def test_contractions_count_as_one_word_with_normalised_forms(self):
        doc = preprocess("I can\u2019t and won't go.")
        self.assertEqual([w.norm for w in doc.words], ["i", "can", "and", "will", "go"])

    def test_pos_lemma_and_dependencies_present(self):
        token = next(t for t in preprocess("The cats were running.").tokens if t.text == "running")
        self.assertEqual((token.pos, token.lemma), ("VERB", "run"))
        self.assertTrue(token.dep)

    def test_english_check(self):
        english = preprocess(" ".join(["The cat sat on the mat and it was happy with the day."] * 3))
        other = preprocess(" ".join(["Katten satt p\u00e5 mattan och var glad \u00f6ver dagen, verkligen."] * 3))
        self.assertEqual((english.language, english.language_checked), ("en", True))
        self.assertEqual(other.language, "und")
        self.assertFalse(preprocess("Too short.").language_checked)


class DocumentStatsTests(SimpleTestCase):
    def test_sentence_length_distribution_by_hand(self):
        stats = compute_document_stats(preprocess("One two three. Four five six seven eight. Nine."))
        self.assertEqual((stats["sentence_count"], stats["word_count"]), (3, 9))
        self.assertEqual(stats["sentence_length_mean"], 3.0)
        self.assertEqual(stats["sentence_length_median"], 3)
        self.assertAlmostEqual(stats["sentence_length_std"], math.sqrt(8 / 3))   # values 3,5,1
        self.assertEqual((stats["sentence_length_min"], stats["sentence_length_max"]), (1, 5))
        self.assertAlmostEqual(stats["sentence_length_cv"], math.sqrt(8 / 3) / 3)

    def test_punctuation_rates(self):
        stats = compute_document_stats(preprocess("Well, yes; no: maybe \u2014 a well-known end? Stop! (Fine.)"))
        words = stats["word_count"]
        self.assertAlmostEqual(stats["commas_per_100"], 100 / words)
        self.assertAlmostEqual(stats["dashes_per_100"], 100 / words)       # em dash counted, hyphen in "well-known" not
        self.assertAlmostEqual(stats["parentheses_per_100"], 100 / words)

    def test_single_sentence_has_zero_spread(self):
        self.assertEqual(compute_document_stats(preprocess("Just one sentence here."))["sentence_length_std"], 0.0)


class LexicalTests(SimpleTestCase):
    def test_ttr_and_mattr_by_hand(self):
        forms = ["a", "b", "a", "c"]
        self.assertEqual(type_token_ratio(forms), 0.75)
        self.assertEqual(mattr(forms, window=2), (1 + 1 + 1) / 3)          # windows ab, ba, ac
        self.assertEqual(mattr(["a", "a", "b"], window=2), (0.5 + 1) / 2)
        self.assertEqual(mattr(forms, window=10), 0.75)                    # shorter than window: plain TTR

    def test_mtld_extremes(self):
        self.assertIsNone(mtld(["w"] * 49))                                # too short
        repetitive = mtld(["the", "cat"] * 50)
        varied = mtld([f"w{i}" for i in range(60)] + [f"w{i}" for i in range(40)])
        self.assertLess(repetitive, 5)
        self.assertGreater(varied, repetitive * 5)

    def test_mtld_forward_and_backward_average_on_a_known_sequence(self):
        forms = (["a", "b", "c", "a"] * 20)
        from analyzer.services.lexical import _mtld_pass
        self.assertAlmostEqual(mtld(forms), (_mtld_pass(forms, 0.72) + _mtld_pass(forms[::-1], 0.72)) / 2)

    def test_zipf_scale(self):
        self.assertGreater(zipf("the"), 7)
        self.assertLess(zipf("sesquipedalian"), 3)

    def test_repeated_phrases_are_maximal_with_exact_spans(self):
        text = ("It is important to note that food matters. Furthermore, it is important to note that "
                "recipes change. The food matters too.")
        doc = preprocess(text)
        phrases = repeated_phrases(doc)
        top = phrases[0]
        self.assertEqual((top["n"], top["count"]), (6, 2))
        self.assertEqual([text[s:e].lower() for s, e in top["spans"]], ["it is important to note that"] * 2)
        self.assertNotIn("important to note", [p["phrase"].lower() for p in phrases])   # sub-phrase not repeated
        self.assertIn("food matters", [p["phrase"].lower() for p in phrases])

    def test_function_word_only_phrases_ignored(self):
        doc = preprocess("It is in the box. It is in the car.")
        self.assertNotIn("it is in the", [p["phrase"].lower() for p in repeated_phrases(doc)])

    def test_rare_and_top_words(self):
        features, details = compute_lexical(preprocess(
            "The recipe used turmeric. Another recipe used tamarind. My recipes were simple."))
        self.assertGreater(features["rare_word_ratio"], 0)
        self.assertEqual(details["top_words"][0], {"word": "recipe", "count": 3})


class PipelineTests(SimpleTestCase):
    def test_every_feature_is_registered_with_an_explanation(self):
        result = run_pipeline("A short text. It has two sentences.")
        self.assertTrue(set(result.features) <= set(BY_NAME))
        for spec in FEATURES:
            self.assertTrue(spec.description.endswith("."), spec.name)

    def test_sentence_rows_match_original(self):
        text = "First sentence here.\n\nSecond one, with a comma."
        result = run_pipeline(text)
        self.assertEqual([text[s["start"]:s["end"]] for s in result.sentences], [s["text"] for s in result.sentences])
        self.assertEqual(result.sentences[1]["signals"]["paragraph"], 1)
        self.assertEqual(result.report["sentence_lengths"], [3, 5])

    def test_non_english_note(self):
        result = run_pipeline(" ".join(["Katten satt p\u00e5 mattan och var glad \u00f6ver dagen, verkligen."] * 3))
        self.assertTrue(result.report["notes"])


class FeatureDocsTests(SimpleTestCase):
    def test_features_md_is_up_to_date(self):
        """docs/FEATURES.md must match the registry. Regenerate with: python manage.py feature_docs --write"""
        from io import StringIO
        from pathlib import Path
        from django.conf import settings
        from django.core.management import call_command
        out = StringIO()
        call_command("feature_docs", stdout=out)
        on_disk = (Path(settings.BASE_DIR) / "docs" / "FEATURES.md").read_text(encoding="utf-8")
        self.assertEqual(on_disk.strip(), out.getvalue().strip())
