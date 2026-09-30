from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
BUSINESS_URL = "/api/business/"
MEMBERS_URL = "/api/business/members/"
PASSWORD = "Str0ng-Pass-123"


def make_owner(email, business_name):
    client = APIClient()
    response = client.post(
        REGISTER_URL,
        {
            "full_name": f"Owner {business_name}",
            "email": email,
            "password": PASSWORD,
            "business_name": business_name,
            "business_type": "RETAIL",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client, response.data


def login_client(email):
    client = APIClient()
    response = client.post(LOGIN_URL, {"email": email, "password": PASSWORD}, format="json")
    assert response.status_code == 200, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


def add_member(owner_client, email, role):
    return owner_client.post(
        MEMBERS_URL,
        {
            "full_name": "Team Member",
            "email": email,
            "password": PASSWORD,
            "role": role,
        },
        format="json",
    )


class TenancyTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")
        self.business_b_id = self.data_b["memberships"][0]["business_id"]

    def test_unauthenticated_requests_are_rejected(self):
        self.assertEqual(APIClient().get(BUSINESS_URL).status_code, 401)
        self.assertEqual(APIClient().get(MEMBERS_URL).status_code, 401)

    def test_user_sees_only_their_own_business(self):
        self.assertEqual(self.owner_a.get(BUSINESS_URL).data["name"], "A Mart")
        self.assertEqual(self.owner_b.get(BUSINESS_URL).data["name"], "B Mart")

    def test_cannot_act_for_another_business_via_header(self):
        response = self.owner_a.get(BUSINESS_URL, HTTP_X_BUSINESS_ID=self.business_b_id)
        self.assertEqual(response.status_code, 403)

    def test_garbage_business_header_is_rejected(self):
        response = self.owner_a.get(BUSINESS_URL, HTTP_X_BUSINESS_ID="not-a-uuid")
        self.assertEqual(response.status_code, 403)

    def test_member_lists_are_isolated(self):
        add_member(self.owner_a, "staff-a@example.com", "STAFF")
        emails = [m["user"]["email"] for m in self.owner_b.get(MEMBERS_URL).data["results"]]
        self.assertEqual(emails, ["b@example.com"])

    def test_cannot_modify_another_businesses_member(self):
        b_membership_id = self.data_b["memberships"][0]["id"]
        response = self.owner_a.patch(
            f"{MEMBERS_URL}{b_membership_id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_owner_can_update_business_profile(self):
        response = self.owner_a.patch(
            BUSINESS_URL, {"address": "Juba", "phone": "+211900000000"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["profile_complete"])
        self.assertEqual(self.owner_b.get(BUSINESS_URL).data["address"], "")

    def test_owner_creates_staff_who_has_restricted_access(self):
        self.assertEqual(add_member(self.owner_a, "staff@example.com", "STAFF").status_code, 201)
        staff = login_client("staff@example.com")
        self.assertEqual(staff.get(BUSINESS_URL).status_code, 200)
        self.assertEqual(staff.get(BUSINESS_URL).data["name"], "A Mart")
        self.assertEqual(
            staff.patch(BUSINESS_URL, {"name": "Hacked"}, format="json").status_code,
            403,
        )
        self.assertEqual(staff.get(MEMBERS_URL).status_code, 403)

    def test_manager_can_view_team_but_not_change_it(self):
        add_member(self.owner_a, "manager@example.com", "MANAGER")
        manager = login_client("manager@example.com")
        self.assertEqual(manager.get(MEMBERS_URL).status_code, 200)
        self.assertEqual(add_member(manager, "x@example.com", "STAFF").status_code, 403)
        self.assertEqual(manager.patch(BUSINESS_URL, {"name": "X"}, format="json").status_code, 403)

    def test_cannot_create_a_second_owner(self):
        self.assertEqual(add_member(self.owner_a, "boss@example.com", "OWNER").status_code, 400)

    def test_owner_membership_cannot_be_changed(self):
        results = self.owner_a.get(MEMBERS_URL).data["results"]
        owner_membership = next(m for m in results if m["role"] == "OWNER")
        response = self.owner_a.patch(
            f"{MEMBERS_URL}{owner_membership['id']}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_deactivated_member_loses_access_immediately(self):
        created = add_member(self.owner_a, "staff@example.com", "STAFF")
        staff = login_client("staff@example.com")
        self.assertEqual(staff.get(BUSINESS_URL).status_code, 200)
        self.owner_a.patch(
            f"{MEMBERS_URL}{created.data['id']}/", {"is_active": False}, format="json"
        )
        self.assertEqual(staff.get(BUSINESS_URL).status_code, 403)
