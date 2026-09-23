"""Phase 7: the plain-language summary and the four downloads."""
import csv
import io
import json
import zipfile

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from analyzer.models import Analysis
from analyzer.services.reports.data import build_report
from analyzer.services.reports.docx_heatmap import band_for, render_docx
from analyzer.services.reports.pdf import render_pdf
from analyzer.services.reports.pdf_heatmap import band_for as pdf_band_for
from analyzer.services.reports.pdf_heatmap import mark, render_heatmap_pdf
from analyzer.services.reports.tabular import render_csv, render_json

TEXT = ("My grandmother kept her recipes on the backs of electricity bills, in pencil. "
        "Half of them are unreadable now, stained with turmeric and something like tamarind. "
        "I still can't make her dal taste right.\n\n"
        "It is important to note that recipes change as families move between cities. "
        "Nobody measured anything. A pinch meant a pinch, and a handful meant her hand. ") * 4


class ReportTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.other = User.objects.create_user("other", password="pw-123-long-enough")
        self.client.force_login(self.user)
        self.client.post(reverse("analyzer:analyze"), {"title": "Grandmother's dal", "text": TEXT})
        self.analysis = Analysis.objects.get()

    def url(self, extension):
        return reverse("analyzer:report", args=[self.analysis.pk, extension])


class SummaryTests(ReportTestCase):
    def test_summary_appears_on_the_page_in_plain_language(self):
        page = self.client.get(reverse("analyzer:detail", args=[self.analysis.pk]))
        self.assertContains(page, "In plain language")
        self.assertContains(page, "words long, in")
        self.assertContains(page, "does not prove authorship")

    def test_demo_results_say_so_in_the_summary(self):
        data = build_report(self.analysis)
        joined = " ".join(data["summary"]["paragraphs"])
        self.assertIn("demo detector", joined)
        self.assertIn("no measured accuracy", joined)


class DownloadTests(ReportTestCase):
    def test_every_format_downloads_with_sensible_filenames(self):
        expected = {
            "pdf": ("application/pdf", b"%PDF-"),
            "heatmap.pdf": ("application/pdf", b"%PDF-"),
            "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
            "json": ("application/json", b"{"),
            "csv": ("text/csv", b"\xef\xbb\xbf"),
        }
        for extension, (content_type, magic) in expected.items():
            with self.subTest(format=extension):
                response = self.client.get(self.url(extension))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], content_type)
                body = b"".join(response.streaming_content)
                self.assertTrue(body.startswith(magic))
                disposition = response["Content-Disposition"]
                self.assertIn("attachment", disposition)
                self.assertIn("grandmothers-dal", disposition)   # apostrophe dropped, not turned into a dash
                self.assertTrue(disposition.endswith(f'.{extension.split(".")[-1]}"'))
                expected_kind = "heatmap" if "heatmap" in extension or extension == "docx" else "report"
                self.assertIn(f"authentitext-{expected_kind}-", disposition)

    def test_links_are_on_the_page_after_the_original_text(self):
        page = self.client.get(reverse("analyzer:detail", args=[self.analysis.pk])).content.decode()
        self.assertIn("Text with heatmap", page)
        self.assertLess(page.index("Original text"), page.index('id="downloads-heading"'))

    def test_another_user_cannot_download(self):
        self.client.force_login(self.other)
        for extension in ("pdf", "heatmap.pdf", "docx", "json", "csv"):
            self.assertEqual(self.client.get(self.url(extension)).status_code, 404)

    def test_anonymous_is_redirected(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url("pdf")).status_code, 302)

    def test_unknown_format_is_404(self):
        self.assertEqual(self.client.get(self.url("exe")).status_code, 404)

    def test_unprocessed_analysis_has_no_report(self):
        pending = Analysis.objects.create(user=self.user, original_text="Not analyzed yet.")
        self.assertEqual(self.client.get(reverse("analyzer:report", args=[pending.pk, "pdf"])).status_code, 404)


class ContentTests(ReportTestCase):
    def test_json_holds_the_whole_analysis(self):
        data = json.loads(render_json(build_report(self.analysis)))
        self.assertEqual(data["document"]["title"], "Grandmother's dal")
        self.assertTrue(data["features"] and data["sentences"] and data["signals"])
        self.assertEqual(len(data["sentences"]), self.analysis.sentences.count())
        self.assertTrue(data["result"]["is_demo"])
        self.assertTrue(any("does not prove authorship" in line for line in data["limitations"]))

    def test_csv_has_one_row_per_item_and_an_excel_safe_bom(self):
        text = render_csv(build_report(self.analysis)).decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text)))
        self.assertEqual(rows[0], ["section", "name", "value", "unit_or_detail", "notes"])
        sections = [row[0] for row in rows[1:]]
        for section in ("document", "result", "feature", "signal", "profile", "sentence", "limitation"):
            self.assertIn(section, sections)
        self.assertEqual(sections.count("sentence"), self.analysis.sentences.count())

    def test_pdf_is_multipage_and_names_the_detector(self):
        payload = render_pdf(build_report(self.analysis))
        self.assertTrue(payload.startswith(b"%PDF-"))
        self.assertGreater(payload.count(b"/Type /Page"), 1)
        self.assertGreater(len(payload), 5000)

    def test_docx_marks_sentences_and_explains_the_three_bands(self):
        payload = render_docx(build_report(self.analysis))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
        for band in ("High signal", "Medium signal", "Low signal"):
            self.assertIn(band, document)
        self.assertIn("highlight", document)        # colour
        self.assertIn("<w:u ", document)            # and underline, so colour is never the only cue
        self.assertIn("signals, not proof", document)
        self.assertIn("DEMO ANALYSIS", document)

    def test_docx_keeps_the_original_paragraph_breaks(self):
        payload = render_docx(build_report(self.analysis))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
        self.assertGreater(document.count("<w:p>"), self.analysis.paragraph_count)

    def test_band_boundaries(self):
        self.assertIsNone(band_for(None))
        self.assertEqual(band_for(0.0)["key"], "low")
        self.assertEqual(band_for(0.33)["key"], "low")
        self.assertEqual(band_for(0.34)["key"], "mid")
        self.assertEqual(band_for(0.59)["key"], "mid")
        self.assertEqual(band_for(0.60)["key"], "high")
        self.assertEqual(band_for(1.0)["key"], "high")


class SentenceScoreCalibrationTests(TestCase):
    """Regression: sentence marks contradicted the document score, marking most
    sentences of a document that scored 11% overall."""

    def test_sentence_scores_agree_with_the_document_score(self):
        from analyzer.services.pipeline import run_pipeline
        result = run_pipeline(TEXT)
        scores = [s["ai_probability"] for s in result.sentences if s["ai_probability"] is not None]
        document = result.report["detection"]["probability"]
        self.assertLess(abs(sum(scores) / len(scores) - document), 0.25)

    def test_a_plain_sentence_scores_near_zero(self):
        from analyzer.services.detector import DemoDetector
        plain = {"signals": {"words": 12, "type_token_ratio": 0.95, "rare_words": 2, "markers": [], "heading": False}}
        self.assertLess(DemoDetector().sentence_scores([plain], {})[0], 0.1)

    def test_headings_and_very_short_sentences_are_not_scored(self):
        from analyzer.services.detector import DemoDetector
        rows = [{"signals": {"words": 3, "type_token_ratio": 1.0, "rare_words": 0, "markers": [], "heading": True}},
                {"signals": {"words": 4, "type_token_ratio": 1.0, "rare_words": 0, "markers": [], "heading": False}}]
        self.assertEqual(DemoDetector().sentence_scores(rows, {}), [None, None])


class HeatmapPdfTests(ReportTestCase):
    def test_it_renders_with_the_three_point_key(self):
        payload = render_heatmap_pdf(build_report(self.analysis))
        self.assertTrue(payload.startswith(b"%PDF-"))
        self.assertGreater(len(payload), 3000)

    def test_marks_never_depend_on_colour_alone(self):
        """Each band adds a different number of underlines as well as a tint,
        so the file still reads in greyscale or in print."""
        low = mark("text", pdf_band_for(0.1))
        medium = mark("text", pdf_band_for(0.5))
        high = mark("text", pdf_band_for(0.9))
        self.assertNotIn("<u", low)
        self.assertIn('kind="single"', medium)
        self.assertIn('kind="double"', high)
        self.assertIn("backColor", medium)
        self.assertIn("backColor", high)

    def test_unscored_sentences_are_left_plain(self):
        self.assertIsNone(pdf_band_for(None))
        self.assertEqual(mark("A heading", None), "A heading")

    def test_markup_is_escaped(self):
        self.assertIn("&lt;script&gt;", mark("<script>", pdf_band_for(0.9)))

    def test_band_boundaries_match_the_website(self):
        from analyzer.views import signal_band
        for probability in (0.0, 0.33, 0.34, 0.59, 0.60, 1.0):
            with self.subTest(probability=probability):
                self.assertEqual(pdf_band_for(probability)["key"], signal_band(probability)[0])


class SignalBreakdownTests(ReportTestCase):
    def test_each_family_explains_what_it_means(self):
        from analyzer.services.signals import FAMILIES, FAMILY_DESCRIPTIONS
        self.assertEqual(set(FAMILIES), set(FAMILY_DESCRIPTIONS))
        page = self.client.get(reverse("analyzer:detail", args=[self.analysis.pk]))
        for description in FAMILY_DESCRIPTIONS.values():
            self.assertContains(page, description[:50])


class SummaryLayoutTests(ReportTestCase):
    def test_summary_is_shown_as_labelled_points(self):
        page = self.client.get(reverse("analyzer:detail", args=[self.analysis.pk]))
        for label in ("The document", "The result", "What stands out", "What this is not"):
            self.assertContains(page, label)
        self.assertContains(page, "text-justify")        # justified, filling the card
        self.assertNotContains(page, "lg:columns-2")     # not split into narrow columns

    def test_points_and_paragraphs_carry_the_same_text(self):
        summary = build_report(self.analysis)["summary"]
        self.assertEqual([point["text"] for point in summary["points"]], summary["paragraphs"])


class TypographyTests(ReportTestCase):
    """Times New Roman everywhere in the exports, and Word headings in plain bold black."""

    def test_pdfs_use_times_for_every_style(self):
        from pathlib import Path
        from analyzer.services.reports import pdf, pdf_heatmap

        for module in (pdf, pdf_heatmap):
            with self.subTest(module=module.__name__):
                source = Path(module.__file__).read_text(encoding="utf-8")
                self.assertNotIn("Helvetica", source)
                self.assertIn("Times-Roman", source)
        for render in (render_pdf, render_heatmap_pdf):
            payload = render(build_report(self.analysis))
            self.assertIn(b"/Times-Roman", payload)
            self.assertIn(b"/Times-Bold", payload)

    def test_docx_sets_times_new_roman_on_every_run(self):
        payload = render_docx(build_report(self.analysis))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
            styles = archive.read("word/styles.xml").decode("utf-8")
        self.assertIn('w:ascii="Times New Roman"', document)
        self.assertIn('w:ascii="Times New Roman"', styles)
        self.assertNotIn("Georgia", document + styles)

    def test_docx_headings_are_black_and_bold_not_word_blue(self):
        payload = render_docx(build_report(self.analysis))
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            styles = archive.read("word/styles.xml").decode("utf-8")
        for name in ("Heading 1", "Heading 2"):
            self.assertIn(name, styles)
        self.assertIn('w:val="000000"', styles)          # black headings
        self.assertNotIn('w:val="2F5496"', styles)       # Word's default heading blue


class SummaryPointsTests(ReportTestCase):
    """The summary is a set of labelled points, so the page and the PDF agree."""

    def test_points_carry_labels_and_text(self):
        summary = build_report(self.analysis)["summary"]
        labels = [point["label"] for point in summary["points"]]
        self.assertEqual(labels[:3], ["The document", "The result", "What stands out"])
        self.assertEqual(labels[-1], "What this is not")
        for point in summary["points"]:
            self.assertTrue(point["text"].strip())
        self.assertEqual(summary["paragraphs"], [point["text"] for point in summary["points"]])

    def test_page_shows_the_labels(self):
        page = self.client.get(reverse("analyzer:detail", args=[self.analysis.pk]))
        for label in ("The document", "The result", "What stands out", "What this is not"):
            self.assertContains(page, label)


class DocxTypographyTests(ReportTestCase):
    """Times New Roman everywhere; headings bold and black, not Word's blue."""

    def read_xml(self, name="word/document.xml"):
        with zipfile.ZipFile(io.BytesIO(render_docx(build_report(self.analysis)))) as archive:
            return archive.read(name).decode("utf-8")

    def test_body_and_styles_use_times_new_roman(self):
        styles = self.read_xml("word/styles.xml")
        self.assertIn('w:ascii="Times New Roman"', styles)
        self.assertNotIn("Georgia", styles)
        self.assertNotIn('w:ascii="Calibri"', self.read_xml())

    def test_headings_are_black(self):
        styles = self.read_xml("word/styles.xml")
        for heading in ("Heading1", "Heading2"):
            block = styles.split(f'w:styleId="{heading}"')[1][:800]
            self.assertIn('w:color w:val="000000"', block)
            self.assertNotIn('w:val="2F5496"', block)   # Word's default heading blue

    def test_no_coloured_text_outside_the_marks(self):
        document = self.read_xml()
        for colour in ("8E3B46", "2F5496", "4472C4"):
            self.assertNotIn(colour, document)
