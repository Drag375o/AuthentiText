from django.test import TestCase
from django.urls import reverse

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

    def test_unbuilt_routes_are_honest(self):
        for name in ["compare", "profile"]:
            response = self.client.get(reverse(f"core:{name}"))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "isn't built yet")



class CompiledCssTests(TestCase):
    """Guards against Tailwind purging classes that only appear in Python or
    are built dynamically in templates (both have bitten this project)."""

    def test_critical_classes_exist_in_built_css(self):
        from pathlib import Path
        from django.conf import settings
        css = (Path(settings.BASE_DIR) / "static" / "css" / "styles.css").read_text()
        for cls in [".field-input", ".sig-low", ".sig-mid", ".sig-high", ".hero-card"]:
            with self.subTest(cls=cls):
                self.assertIn(cls + "{", css.replace(" {", "{"))
