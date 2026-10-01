import pytest


@pytest.mark.django_db
def test_login_success(api_client, super_admin):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "admin@test.demo", "password": "TestPass123!"},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert response.data["user"]["role"] == "SUPER_ADMIN"


@pytest.mark.django_db
def test_login_invalid_credentials(api_client, super_admin):
    response = api_client.post(
        "/api/v1/auth/login/", {"email": "admin@test.demo", "password": "wrong"}, format="json"
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_current_user(api_client, sales_executive):
    api_client.force_authenticate(user=sales_executive)
    response = api_client.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.data["data"]["email"] == "exec@test.demo"
