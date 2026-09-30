from rest_framework.test import APIClient

PASSWORD = "Str0ng-Pass-123"


def make_owner(email, business_name):
    """Register a new business and return (authenticated client, registration data)."""
    client = APIClient()
    response = client.post(
        "/api/auth/register/",
        {
            "full_name": f"Owner of {business_name}",
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


def login_client(email, password=PASSWORD):
    client = APIClient()
    response = client.post(
        "/api/auth/login/", {"email": email, "password": password}, format="json"
    )
    assert response.status_code == 200, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


def make_member_client(owner_client, email, role):
    """Have the owner add a team member, then return a client logged in as them."""
    response = owner_client.post(
        "/api/business/members/",
        {
            "full_name": "Team Member",
            "email": email,
            "password": PASSWORD,
            "role": role,
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return login_client(email)
