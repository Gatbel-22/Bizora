from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from apps.businesses.models import Branch, Business

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"
CHANGE_PASSWORD_URL = "/api/auth/change-password/"
PASSWORD = "Str0ng-Pass-123"


def registration_payload(**overrides):
    payload = {
        "full_name": "Test Owner",
        "email": "owner@example.com",
        "password": PASSWORD,
        "business_name": "Test Mart",
        "business_type": "RETAIL",
    }
    payload.update(overrides)
    return payload


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()  # reset rate-limit counters between tests

    def register(self, **overrides):
        return self.client.post(REGISTER_URL, registration_payload(**overrides), format="json")

    def authed_client(self, access):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    def test_register_creates_user_business_branch_and_owner_membership(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["memberships"][0]["role"], "OWNER")
        self.assertEqual(response.data["memberships"][0]["currency"], "SSP")
        self.assertEqual(Business.objects.count(), 1)
        self.assertEqual(Branch.objects.filter(is_primary=True).count(), 1)

    def test_register_rejects_duplicate_email_case_insensitively(self):
        self.register()
        response = self.register(email="OWNER@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["error"]["details"])
        self.assertEqual(Business.objects.count(), 1)

    def test_register_rejects_weak_password(self):
        response = self.register(password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data["error"]["details"])
        self.assertEqual(Business.objects.count(), 0)

    def test_register_rejects_unsupported_currency(self):
        response = self.register(currency="XXX")
        self.assertEqual(response.status_code, 400)

    def test_login_returns_tokens_user_and_memberships(self):
        self.register()
        response = self.client.post(
            LOGIN_URL,
            {"email": "OWNER@EXAMPLE.COM", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["email"], "owner@example.com")
        self.assertEqual(len(response.data["memberships"]), 1)

    def test_login_with_wrong_password_fails(self):
        self.register()
        response = self.client.post(
            LOGIN_URL,
            {"email": "owner@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_me_requires_authentication(self):
        self.assertEqual(self.client.get(ME_URL).status_code, 401)

    def test_me_returns_profile_and_can_update_name(self):
        access = self.register().data["access"]
        client = self.authed_client(access)
        self.assertEqual(client.get(ME_URL).data["user"]["full_name"], "Test Owner")
        response = client.patch(ME_URL, {"full_name": "New Name"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["full_name"], "New Name")

    def test_logout_blacklists_refresh_token(self):
        data = self.register().data
        client = self.authed_client(data["access"])
        response = client.post(LOGOUT_URL, {"refresh": data["refresh"]}, format="json")
        self.assertEqual(response.status_code, 204)
        refreshed = self.client.post(REFRESH_URL, {"refresh": data["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 401)

    def test_change_password(self):
        access = self.register().data["access"]
        client = self.authed_client(access)
        bad = client.post(
            CHANGE_PASSWORD_URL,
            {"current_password": "nope", "new_password": "An0ther-Pass-456"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        good = client.post(
            CHANGE_PASSWORD_URL,
            {"current_password": PASSWORD, "new_password": "An0ther-Pass-456"},
            format="json",
        )
        self.assertEqual(good.status_code, 204)
        login = self.client.post(
            LOGIN_URL,
            {"email": "owner@example.com", "password": "An0ther-Pass-456"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

    def test_logout_works_with_only_the_refresh_token(self):
        data = self.register().data
        response = self.client.post(LOGOUT_URL, {"refresh": data["refresh"]}, format="json")
        self.assertEqual(response.status_code, 204)
