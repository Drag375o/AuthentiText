"""Users must never be able to see or change another user's documents."""
import uuid

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from analyzer.models import Analysis


class OwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw-owner-123!")
        self.intruder = User.objects.create_user("intruder", password="pw-intruder-123!")
        self.analysis = Analysis.objects.create(user=self.owner, title="Private essay", original_text="Secret words here.")
        self.detail = reverse("analyzer:detail", args=[self.analysis.pk])
        self.delete = reverse("analyzer:delete", args=[self.analysis.pk])

    def login(self, user):
        self.client.force_login(user)

    # Anonymous visitors
    def test_protected_pages_redirect_to_login(self):
        for url in (reverse("analyzer:dashboard"), self.detail):
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_anonymous_cannot_delete(self):
        self.client.post(self.delete)
        self.assertTrue(Analysis.objects.filter(pk=self.analysis.pk).exists())

    # Owner
    def test_owner_sees_own_analysis(self):
        self.login(self.owner)
        self.assertContains(self.client.get(self.detail), "Secret words here.")
        self.assertContains(self.client.get(reverse("analyzer:dashboard")), "Private essay")

    def test_owner_can_delete_with_post_only(self):
        self.login(self.owner)
        self.assertEqual(self.client.get(self.delete).status_code, 405)
        response = self.client.post(self.delete)
        self.assertRedirects(response, reverse("analyzer:dashboard"))
        self.assertFalse(Analysis.objects.filter(pk=self.analysis.pk).exists())

    # Another user
    def test_other_user_gets_404_not_403(self):
        self.login(self.intruder)
        self.assertEqual(self.client.get(self.detail).status_code, 404)

    def test_other_user_cannot_delete(self):
        self.login(self.intruder)
        self.assertEqual(self.client.post(self.delete).status_code, 404)
        self.assertTrue(Analysis.objects.filter(pk=self.analysis.pk).exists())

    def test_other_users_dashboard_does_not_list_it(self):
        self.login(self.intruder)
        response = self.client.get(reverse("analyzer:dashboard"))
        self.assertNotContains(response, "Private essay")
        self.assertContains(response, "No analyses yet.")

    def test_unknown_id_is_404(self):
        self.login(self.owner)
        self.assertEqual(self.client.get(reverse("analyzer:detail", args=[uuid.uuid4()])).status_code, 404)

    def test_delete_requires_csrf_token(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.delete).status_code, 403)
        self.assertTrue(Analysis.objects.filter(pk=self.analysis.pk).exists())
