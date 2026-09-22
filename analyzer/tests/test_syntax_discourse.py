"""Phase 4b: syntax, discourse markers, pattern library, sentence openings."""
import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from analyzer.services import discourse
from analyzer.services.discourse import PatternLibraryError, compute_discourse, find_patterns, validate_library
from analyzer.services.preprocessing import preprocess
from analyzer.services.syntax import compute_syntax, dependency_distances, parse_depth, sentence_syntax


def first_sentence(text):
    return preprocess(text).sentences[0]


class SyntaxTests(SimpleTestCase):
    def test_active_and_passive(self):
        self.assertFalse(sentence_syntax(first_sentence("The dog ate the cake."))["passive"])
        self.assertTrue(sentence_syntax(first_sentence("The cake was eaten by the dog."))["passive"])

    def test_clauses_subordination_and_coordination(self):
        s = sentence_syntax(first_sentence("I left because it rained, and she stayed home."))
        self.assertEqual((s["clauses"], s["subordinate_clauses"]), (3, 1))
        rich = sentence_syntax(first_sentence("The recipe that my grandmother wrote, which nobody can read, was lost when we moved."))
        self.assertEqual(rich["subordinate_clauses"], 3)

    def test_depth_and_distance_on_a_simple_sentence(self):
        s = first_sentence("The dog ate the cake.")
        # ate(root) <- dog <- The ; ate <- cake <- the : depth 2
        self.assertEqual(parse_depth(s), 2)
        # The->dog 1, dog->ate 1, the->cake 1, cake->ate 2 ; punctuation excluded
        self.assertEqual(sorted(dependency_distances(s)), [1, 1, 1, 2])

    def test_whitespace_tokens_do_not_break_head_positions(self):
        s = preprocess("Intro.\n\nThe cake was eaten\n  by the dog.").sentences[1]
        by_index = {t.index: t for t in s.tokens}
        self.assertTrue(all(t.head in by_index for t in s.tokens))
        self.assertTrue(sentence_syntax(s)["passive"])

    def test_pos_ratios_are_shares_of_words(self):
        f = compute_syntax(preprocess("The small dog quickly ate the cake."))
        self.assertAlmostEqual(f["pos_noun_ratio"], 2 / 7)
        self.assertAlmostEqual(f["pos_adj_ratio"], 1 / 7)
        self.assertAlmostEqual(f["pos_det_ratio"], 2 / 7)
        self.assertLessEqual(sum(v for k, v in f.items() if k.startswith("pos_")), 1.0 + 1e-9)

    def test_passive_ratio(self):
        f = compute_syntax(preprocess("The cake was eaten. The dog slept. The door was opened by Sam. We left."))
        self.assertEqual(f["passive_sentence_ratio"], 0.5)


class PatternMatchingTests(SimpleTestCase):
    def matched(self, text):
        return [(m["pattern"], text[m["start"]:m["end"]]) for m in find_patterns(preprocess(text))]

    def test_case_curly_apostrophes_and_longest_match(self):
        text = "In today\u2019s fast-paced world, food matters."
        self.assertEqual(self.matched(text), [("in today's fast-paced world", "In today\u2019s fast-paced world")])

    def test_start_only_patterns(self):
        self.assertIn(("so", "So"), self.matched("So we adapted."))
        self.assertNotIn("so", [p for p, _ in self.matched("I think so.")])

    def test_part_of_speech_constraint(self):
        found = [p for p, _ in self.matched("It may rain in May.")]
        self.assertEqual(found.count("may"), 1)

    def test_rates_per_100_words_and_initial_markers(self):
        doc = preprocess("However, it rained. We stayed. Therefore we read. Books were fine.")
        f, details = compute_discourse(doc)
        words = len(doc.words)
        self.assertAlmostEqual(f["contrast_markers_per_100"], 100 / words)
        self.assertAlmostEqual(f["cause_effect_markers_per_100"], 100 / words)
        self.assertEqual(f["marker_initial_ratio"], 0.5)
        self.assertEqual(details["category_counts"], {"contrast": 1, "cause_effect": 1})

    def test_repeated_openings(self):
        f, details = compute_discourse(preprocess("It is late. It is dark. We left. It is over."))
        self.assertEqual(f["repeated_opening_ratio"], 0.75)
        self.assertEqual(details["repeated_openings"][0], {"opening": "it is", "count": 3, "sentences": [0, 1, 3]})

    def test_openings_need_three_sentences(self):
        f, _ = compute_discourse(preprocess("One sentence. Two sentences."))
        self.assertIsNone(f["repeated_opening_ratio"])


class PatternLibraryTests(SimpleTestCase):
    def setUp(self):
        discourse.load_library.cache_clear()
        self.addCleanup(discourse.load_library.cache_clear)

    def test_shipped_library_is_valid(self):
        data = json.loads(discourse.library_path().read_text(encoding="utf-8"))
        validate_library(data)
        self.assertGreater(len(data["patterns"]), 50)

    def test_invalid_libraries_are_rejected_with_a_clear_message(self):
        base = {"categories": {"hedging": "Hedging"}}
        cases = [
            ({**base, "patterns": [{"pattern": "maybe", "category": "nope", "description": "d", "strength": "low"}]}, "unknown category"),
            ({**base, "patterns": [{"pattern": "maybe", "category": "hedging", "description": "d", "strength": "huge"}]}, "strength"),
            ({**base, "patterns": [{"pattern": "maybe", "category": "hedging", "description": "", "strength": "low"}]}, "missing 'description'"),
            ({**base, "patterns": [{"pattern": "maybe", "category": "hedging", "description": "d", "strength": "low"}] * 2}, "duplicate"),
        ]
        for data, message in cases:
            with self.subTest(message=message), self.assertRaisesMessage(PatternLibraryError, message):
                validate_library(data)

    def test_custom_library_path_setting(self):
        custom = {"version": 1, "categories": {"hedging": "Hedging"},
                  "patterns": [{"pattern": "kinda", "category": "hedging", "description": "Informal hedge.", "strength": "low"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "patterns.json"
            path.write_text(json.dumps(custom), encoding="utf-8")
            with override_settings(PATTERN_LIBRARY_PATH=str(path)):
                discourse.load_library.cache_clear()
                self.assertEqual([m["pattern"] for m in find_patterns(preprocess("It was kinda fine, however."))], ["kinda"])
