from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

PASSWORD = "a-long-test-passphrase-42"


class RegistrationTests(TestCase):
    url = reverse("accounts:register")

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create your account")

    def test_register_creates_user_and_signs_in(self):
        response = self.client.post(self.url, {"username": "ayesha", "email": "", "password1": PASSWORD, "password2": PASSWORD})
        self.assertRedirects(response, reverse("analyzer:dashboard"))
        self.assertTrue(User.objects.filter(username="ayesha").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(username="ayesha").pk)

    def test_password_is_hashed(self):
        self.client.post(self.url, {"username": "ayesha", "password1": PASSWORD, "password2": PASSWORD})
        self.assertNotEqual(User.objects.get(username="ayesha").password, PASSWORD)

    def test_weak_or_mismatched_passwords_are_rejected(self):
        for p1, p2 in [("password", "password"), (PASSWORD, PASSWORD + "x"), ("12345678", "12345678")]:
            response = self.client.post(self.url, {"username": "weak", "password1": p1, "password2": p2})
            self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak").exists())

    def test_signed_in_users_are_redirected(self):
        User.objects.create_user("ayesha", password=PASSWORD)
        self.client.login(username="ayesha", password=PASSWORD)
        self.assertRedirects(self.client.get(self.url), reverse("analyzer:dashboard"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        User.objects.create_user("ayesha", password=PASSWORD)

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {"username": "ayesha", "password": PASSWORD})
        self.assertRedirects(response, reverse("analyzer:dashboard"))

    def test_login_honours_safe_next_only(self):
        response = self.client.post(reverse("accounts:login") + "?next=https://evil.example/",
                                    {"username": "ayesha", "password": PASSWORD, "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("analyzer:dashboard"))

    def test_wrong_password_shows_clear_error(self):
        response = self.client.post(reverse("accounts:login"), {"username": "ayesha", "password": "wrong"})
        self.assertContains(response, "don&#x27;t match")

    def test_logout_requires_post(self):
        self.client.login(username="ayesha", password=PASSWORD)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:landing"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_nav_reflects_auth_state(self):
        self.assertContains(self.client.get(reverse("core:landing")), reverse("accounts:login"))
        self.client.login(username="ayesha", password=PASSWORD)
        response = self.client.get(reverse("core:landing"))
        self.assertContains(response, "Log out")
        self.assertContains(response, reverse("analyzer:dashboard"))


class RememberMeTests(TestCase):
    def setUp(self):
        User.objects.create_user("ayesha", password=PASSWORD)

    def test_unticked_session_ends_with_browser(self):
        self.client.post(reverse("accounts:login"), {"username": "ayesha", "password": PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_ticked_session_persists(self):
        self.client.post(reverse("accounts:login"), {"username": "ayesha", "password": PASSWORD, "remember": "on"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())


class AuthLayoutTests(TestCase):
    def test_account_pages_use_split_layout_without_site_nav(self):
        for name in ["login", "register", "password_reset"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"accounts:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "images/hero.webp")
                self.assertNotContains(response, 'aria-label="Primary"')
                self.assertContains(response, "Back to home")

    def test_login_links_to_password_reset(self):
        self.assertContains(self.client.get(reverse("accounts:login")), reverse("accounts:password_reset"))


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ayesha", email="ayesha@example.com", password=PASSWORD)

    def test_full_reset_flow(self):
        import re
        from django.core import mail
        response = self.client.post(reverse("accounts:password_reset"), {"email": "ayesha@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Reset your AuthentiText password")

        link = re.search(r"https?://[^/]+(/accounts/password-reset/[^\s]+/)", mail.outbox[0].body).group(1)
        response = self.client.get(link, follow=True)  # Django swaps the token for a session marker
        self.assertContains(response, "Choose a new password")

        new = "a-brand-new-passphrase-77"
        response = self.client.post(response.redirect_chain[-1][0], {"new_password1": new, "new_password2": new})
        self.assertRedirects(response, reverse("accounts:password_reset_complete"))
        self.assertTrue(self.client.login(username="ayesha", password=new))

    def test_unknown_email_looks_identical_and_sends_nothing(self):
        from django.core import mail
        response = self.client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_bad_token_shows_expired_message(self):
        response = self.client.get(reverse("accounts:password_reset_confirm", args=["MQ", "bad-token"]))
        self.assertContains(response, "This link has expired")
