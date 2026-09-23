"""Phase 7: comparing two documents."""
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from analyzer.models import Analysis
from analyzer.services.compare import align_sentences, build_comparison, sentence_similarity, word_diff
from analyzer.services.compare import Side

# Identical in both documents, so these rows stay unchanged and both texts clear
# the 150-word minimum the detector needs before it reports a result.
SHARED = (
    "The kitchen window faced the road, and in summer the curtains stayed shut until evening. "
    "She cooked by smell more than by sight, leaning over the pot with her eyes half closed. "
    "Rice went in first, then the lentils, then whatever the garden had given up that week. "
    "My cousins remember the same meals differently, which tells you something about memory. "
    "There was a tin of cardamom pods that nobody ever refilled and nobody ever finished. "
    "On winter mornings the whole flat smelled of ginger and burnt sugar for hours afterwards. "
    "I learned to cook from watching, never from asking, and that turned out to be a mistake. "
    "The measurements existed only in her hands, and her hands were not mine to inherit."
)
DRAFT = ("My grandmother kept her recipes on the backs of electricity bills. "
         "Half of them are unreadable now. I still can't make her dal taste right. "
         "Nobody measured anything in that kitchen. A pinch meant a pinch, and a handful meant her hand. " + SHARED)
REVISION = ("My grandmother kept her recipes on the backs of electricity bills. "
            "Most of them are unreadable today. I still can't make her dal taste right. "
            "It is important to note that nobody measured anything in that kitchen, which underscores the difficulty. "
            "A pinch meant a pinch, and a handful meant her hand. She never wrote any of it down. " + SHARED)


def side(sentences):
    """A Side built by hand, for the alignment tests."""
    return Side(analysis=None, values={}, sentences=sentences, vocabulary=set())


class WordDiffTests(SimpleTestCase):
    def test_marks_only_what_changed(self):
        left, right = word_diff("the cat sat down", "the dog sat down")
        self.assertEqual([run["text"] for run in left if run["change"] == "removed"], ["cat"])
        self.assertEqual([run["text"] for run in right if run["change"] == "added"], ["dog"])
        self.assertEqual("".join(run["text"] for run in left), "the cat sat down")
        self.assertEqual("".join(run["text"] for run in right), "the dog sat down")

    def test_identical_text_has_no_marks(self):
        left, right = word_diff("same words here", "same words here")
        self.assertEqual({run["change"] for run in left + right}, {"same"})


class AlignmentTests(SimpleTestCase):
    def test_unchanged_changed_added_and_removed(self):
        rows = align_sentences(side(["One stays.", "Two is edited slightly.", "Three goes away."]),
                               side(["One stays.", "Two is edited a lot more.", "Four arrives."]))
        kinds = [row["kind"] for row in rows]
        self.assertEqual(kinds[0], "unchanged")
        self.assertIn("changed", kinds)
        self.assertTrue({"added", "removed"} & set(kinds))

    def test_whitespace_only_difference_is_not_a_change(self):
        rows = align_sentences(side(["The  rain   stopped."]), side(["The rain stopped."]))
        self.assertEqual([row["kind"] for row in rows], ["unchanged"])

    def test_a_rewrite_is_flagged_as_such(self):
        rows = align_sentences(side(["The cat sat on the mat."]),
                               side(["The cat was sitting on a mat, apparently."]))
        self.assertEqual(rows[0]["kind"], "changed")
        self.assertTrue(rows[0]["rewritten"])

    def test_unrelated_sentences_are_a_removal_and_an_addition(self):
        """Pairing them as an "edit" would invent a relationship that isn't there."""
        rows = align_sentences(side(["Three goes away."]), side(["Rhubarb arrives, unexpectedly."]))
        self.assertEqual([row["kind"] for row in rows], ["removed", "added"])

    def test_similarity_is_measured_over_words_not_characters(self):
        """Unrelated English sentences share many letters but no words."""
        self.assertEqual(sentence_similarity("The cat sat on the mat.",
                                             "Feline occupancy of floor coverings remains widespread."), 0.0)
        self.assertGreater(sentence_similarity("The cat sat on the mat.", "The cat sat on the rug."), 0.8)

    def test_a_small_edit_is_not_a_rewrite(self):
        rows = align_sentences(side(["The cat sat on the mat."]), side(["The cat sat on the rug."]))
        self.assertFalse(rows[0]["rewritten"])


class ComparePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.other = User.objects.create_user("other", password="pw-123-long-enough")
        self.client.force_login(self.user)
        self.a = self.analyze("Draft", DRAFT)
        self.b = self.analyze("Revision", REVISION)

    def analyze(self, title, text):
        self.client.post(reverse("analyzer:analyze"), {"title": title, "text": text})
        return Analysis.objects.get(title=title)

    def url(self, a=None, b=None):
        base = reverse("analyzer:compare")
        if a is None and b is None:
            return base
        return f"{base}?a={a or ''}&b={b or ''}"

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url())
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('analyzer:compare')}")

    def test_empty_state_asks_for_two_documents(self):
        self.assertContains(self.client.get(self.url()), "Choose two documents to compare.")

    def test_comparison_renders_both_documents(self):
        response = self.client.get(self.url(self.a.pk, self.b.pk))
        self.assertContains(response, "What changed")
        self.assertContains(response, "How the numbers moved")
        self.assertContains(response, "Draft")
        self.assertContains(response, "Revision")
        self.assertContains(response, "underscores the difficulty")     # the added sentence

    def test_same_document_twice_is_refused(self):
        self.assertContains(self.client.get(self.url(self.a.pk, self.a.pk)), "Choose two different documents.")

    def test_another_users_document_is_not_found(self):
        self.client.force_login(self.other)
        their = Analysis.objects.create(user=self.other, title="Theirs", original_text=DRAFT)
        response = self.client.get(self.url(self.a.pk, their.pk))
        self.assertContains(response, "could not be found in your account")
        self.assertNotContains(response, "grandmother")

    def test_a_malformed_id_does_not_error(self):
        self.assertEqual(self.client.get(self.url("not-a-uuid", self.b.pk)).status_code, 200)

    def test_picker_lists_only_analyzed_documents_of_this_user(self):
        Analysis.objects.create(user=self.user, title="Never analyzed", original_text="x")
        Analysis.objects.create(user=self.other, title="Someone else's", original_text=DRAFT)
        response = self.client.get(self.url())
        self.assertContains(response, "Draft")
        self.assertNotContains(response, "Never analyzed")
        self.assertNotContains(response, "Someone else&#x27;s")


class ComparisonContentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayesha", password="pw-123-long-enough")
        self.client.force_login(self.user)
        for title, text in (("Draft", DRAFT), ("Revision", REVISION)):
            self.client.post(reverse("analyzer:analyze"), {"title": title, "text": text})
        self.comparison = build_comparison(Analysis.objects.get(title="Draft"),
                                           Analysis.objects.get(title="Revision"))

    def test_counts_add_up_to_the_rows(self):
        self.assertEqual(sum(self.comparison["counts"].values()), len(self.comparison["rows"]))
        self.assertGreater(self.comparison["counts"]["unchanged"], 0)
        self.assertGreater(self.comparison["counts"]["added"], 0)

    def test_features_carry_both_values_and_a_delta(self):
        row = next(r for r in self.comparison["features"] if r["spec"].name == "word_count")
        self.assertGreater(row["b"], row["a"])
        self.assertAlmostEqual(row["delta"], row["b"] - row["a"])
        self.assertEqual(row["direction"], "up")

    def test_vocabulary_difference_is_reported_both_ways(self):
        vocabulary = self.comparison["vocabulary"]
        self.assertIn("underscores", vocabulary["added"])
        self.assertIn("now", vocabulary["removed"])          # "Half ... unreadable now" became "Most ... today"
        self.assertGreater(vocabulary["shared"], 10)

    def test_profile_and_families_pair_up(self):
        self.assertTrue(self.comparison["profile"])
        for row in self.comparison["profile"]:
            self.assertIn("a", row)
            self.assertIn("b", row)
        self.assertEqual(len(self.comparison["detection"]["families"]), 5)


class PickerStylingTests(ComparePageTests):
    def test_selects_use_the_custom_arrow_with_room_for_it(self):
        """The browser's own arrow sits flush against the border."""
        page = self.client.get(self.url()).content.decode()
        self.assertEqual(page.count('class="field-select mt-2"'), 2)
        self.assertNotIn('name="a" class="field-input', page)
