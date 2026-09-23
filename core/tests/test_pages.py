from django.test import TestCase
from django.urls import reverse

from core.context_processors import PRIMARY_NAV
from core.landing_content import SAMPLE_DOCUMENT


class LandingPageTests(TestCase):
    def setUp(self):
        self.response = self.client.get(reverse("core:landing"))

    def test_renders(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertTemplateUsed(self.response, "landing.html")

    def test_hero_copy_and_ctas(self):
        self.assertContains(self.response, "Welcome to")
        self.assertContains(self.response, "AuthentiText.")
        self.assertContains(self.response, "Does your writing sound like AI?")
        self.assertContains(self.response, reverse("analyzer:analyze"))
        self.assertContains(self.response, 'href="#how-it-works"')

    def test_hero_field_is_decorative_and_wired(self):
        self.assertContains(self.response, 'aria-hidden="true" data-hero-field')
        self.assertContains(self.response, "data-hero-quiet")
        self.assertContains(self.response, "js/hero-field.js")

    def test_no_hero_photo_remains(self):
        self.assertNotContains(self.response, "hero.webp")
        self.assertNotContains(self.response, "Hero preview")

    def test_sample_data_is_labelled_illustrative(self):
        self.assertContains(self.response, "Illustrative example, not model output")

    def test_every_sample_sentence_is_a_focusable_mark(self):
        for sentence in SAMPLE_DOCUMENT:
            self.assertContains(self.response, sentence["text"].replace("'", "&#x27;"))
        # Two viewers (hero + main) render each sentence.
        self.assertContains(self.response, "data-sentence-index=", count=len(SAMPLE_DOCUMENT) * 2)

    def test_signal_level_is_not_colour_only(self):
        # Screen-reader text states the level for every mark.
        self.assertContains(self.response, "(High signal)")
        self.assertContains(self.response, "(Low signal)")

    def test_json_payload_is_escaped_via_json_script(self):
        self.assertContains(self.response, 'id="sample-document" type="application/json"')

    def test_never_claims_certainty(self):
        self.assertNotContains(self.response, "definitely written by AI")


class SecondaryPageTests(TestCase):
    def test_about(self):
        self.assertEqual(self.client.get(reverse("core:about")).status_code, 200)

    def test_every_navigation_link_resolves(self):
        from django.urls import reverse
        for item in PRIMARY_NAV:
            with self.subTest(item=item["label"]):
                self.assertTrue(reverse(item["url_name"]))



class CompiledCssTests(TestCase):
    """Guards against Tailwind purging classes that only appear in Python or
    are built dynamically in templates (both have bitten this project)."""

    def test_critical_classes_exist_in_built_css(self):
        from pathlib import Path
        from django.conf import settings
        css = (Path(settings.BASE_DIR) / "static" / "css" / "styles.css").read_text()
        self.assertIn("display:none!important", css.replace(" ", ""))  # [hidden] beats component styles
        for cls in [".field-input", ".sig-low", ".sig-mid", ".sig-high", ".hero-card", ".dropzone", ".btn-danger"]:
            with self.subTest(cls=cls):
                self.assertIn(cls + "{", css.replace(" {", "{"))


class TemplateHygieneTests(TestCase):
    def test_no_literal_unicode_escapes_in_templates(self):
        """Django doesn't interpret \\uXXXX in templates; they would show up on the page."""
        import re
        from pathlib import Path
        from django.conf import settings
        offenders = [str(p) for p in (Path(settings.BASE_DIR) / "templates").rglob("*.html")
                     if re.search(r"\\u[0-9a-fA-F]{4}", p.read_text(encoding="utf-8"))]
        self.assertEqual(offenders, [])


class SentenceMarkIndexTests(TestCase):
    """The viewer looks sentences up by data-sentence-index, so the landing page's
    sample must number its marks 0..n-1 even though its data has no index field."""

    def test_landing_marks_are_numbered_in_order(self):
        import re
        html = self.client.get(reverse("core:landing")).content.decode()
        indices = re.findall(r'data-sentence-index="(\d+)"', html)
        expected = [str(i) for i in range(len(SAMPLE_DOCUMENT))]
        self.assertEqual(indices, expected * 2)   # hero viewer + main viewer


class DocumentationTests(TestCase):
    """The README is the first thing a reviewer reads, so keep it truthful."""

    def readme(self) -> str:
        from pathlib import Path
        from django.conf import settings
        return (Path(settings.BASE_DIR) / "README.md").read_text(encoding="utf-8")

    def test_the_screenshot_guide_lists_every_referenced_image(self):
        """Someone replacing the screenshots should find all of them documented."""
        import re
        from pathlib import Path
        from django.conf import settings
        guide = (Path(settings.BASE_DIR) / "docs" / "screenshots" / "README.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r"docs/screenshots/([\w-]+\.png)", self.readme()))
        self.assertTrue(referenced)
        for name in referenced:
            with self.subTest(image=name):
                self.assertIn(f"`{name}`", guide)

    def test_every_linked_document_and_screenshot_exists(self):
        import re
        from pathlib import Path
        from django.conf import settings
        base = Path(settings.BASE_DIR)
        targets = re.findall(r"\]\((docs/[^)#]+)\)", self.readme())
        self.assertGreater(len(targets), 8)
        missing = [target for target in targets if not (base / target).exists()]
        self.assertEqual(missing, [])

    def test_it_does_not_claim_certainty(self):
        text = self.readme().lower()
        for phrase in ["definitely written by ai", "proves", "guaranteed", "100% accurate"]:
            self.assertNotIn(phrase, text)

    def test_it_says_the_shipped_detector_is_a_demo(self):
        self.assertIn("DEMO ANALYSIS", self.readme())
        self.assertIn("no measured accuracy", self.readme())
