"""Same cases as tests/js/text-stats.test.js, so browser and server counts agree."""
import json
from pathlib import Path

from django.test import SimpleTestCase

from analyzer.services.text_stats import READING_WPM, compute_text_stats

CASES = json.loads((Path(__file__).parent / "fixtures" / "text_stats_cases.json").read_text(encoding="utf-8"))


class SharedTextStatsCases(SimpleTestCase):
    def test_all_shared_cases(self):
        for case in CASES:
            with self.subTest(case=case["name"]):
                expected = {k: v for k, v in case.items() if k not in ("name", "text")}
                self.assertEqual(compute_text_stats(case["text"]).as_dict(), expected)

    def test_reading_speed_constant(self):
        self.assertEqual(READING_WPM, 238)
