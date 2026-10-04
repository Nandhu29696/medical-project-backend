import pytest

from apps.leads.models import Lead, LeadStatus


@pytest.mark.django_db
def test_public_lead_creation_requires_consent(api_client, product):
    response = api_client.post(
        "/api/v1/public/leads/",
        {
            "first_name": "Test",
            "last_name": "User",
            "phone": "9876543210",
            "product_id": str(product.id),
            "consent_given": False,
        },
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_public_lead_creation_success(api_client, product):
    response = api_client.post(
        "/api/v1/public/leads/",
        {
            "first_name": "Test",
            "last_name": "User",
            "phone": "9876543210",
            "product_id": str(product.id),
            "consent_given": True,
            "source": "ORGANIC",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Lead.objects.count() == 1
    lead = Lead.objects.first()
    assert lead.lead_number.startswith("MED-")
    assert lead.status == LeadStatus.NEW


@pytest.mark.django_db
def test_public_lead_honeypot_rejects_bots(api_client, product):
    response = api_client.post(
        "/api/v1/public/leads/",
        {
            "first_name": "Bot",
            "last_name": "Submission",
            "phone": "9876543210",
            "product_id": str(product.id),
            "consent_given": True,
            "website": "http://spam.example",
        },
        format="json",
    )
    assert response.status_code == 400
    assert Lead.objects.count() == 0


@pytest.mark.django_db
def test_duplicate_lead_is_flagged(api_client, product):
    api_client.post(
        "/api/v1/public/leads/",
        {
            "first_name": "A",
            "last_name": "B",
            "phone": "9876543210",
            "product_id": str(product.id),
            "consent_given": True,
        },
        format="json",
    )
    api_client.post(
        "/api/v1/public/leads/",
        {
            "first_name": "A",
            "last_name": "B",
            "phone": "9876543210",
            "product_id": str(product.id),
            "consent_given": True,
        },
        format="json",
    )
    leads = list(Lead.objects.order_by("created_at"))
    assert len(leads) == 2
    assert leads[1].is_potential_duplicate is True


@pytest.mark.django_db
def test_sales_executive_only_sees_assigned_leads(
    api_client, sales_executive, sales_manager, product
):
    own_lead = Lead.objects.create(
        first_name="Own",
        last_name="Lead",
        phone="9000000001",
        product=product,
        assigned_to=sales_executive,
    )
    Lead.objects.create(
        first_name="Other",
        last_name="Lead",
        phone="9000000002",
        product=product,
        assigned_to=sales_manager,
    )

    api_client.force_authenticate(user=sales_executive)
    response = api_client.get("/api/v1/leads/")
    assert response.status_code == 200
    results = response.data["data"]["results"]
    assert len(results) == 1
    assert results[0]["id"] == str(own_lead.id)


@pytest.mark.django_db
def test_manager_can_assign_lead(api_client, sales_manager, sales_executive, product):
    lead = Lead.objects.create(
        first_name="Assign", last_name="Me", phone="9000000003", product=product
    )
    api_client.force_authenticate(user=sales_manager)
    response = api_client.post(
        f"/api/v1/leads/{lead.id}/assign/", {"assigned_to": str(sales_executive.id)}, format="json"
    )
    assert response.status_code == 200
    lead.refresh_from_db()
    assert lead.assigned_to_id == sales_executive.id


@pytest.mark.django_db
def test_executive_cannot_assign_lead(api_client, sales_executive, product):
    lead = Lead.objects.create(
        first_name="NoAssign", last_name="Me", phone="9000000004", product=product
    )
    api_client.force_authenticate(user=sales_executive)
    response = api_client.post(
        f"/api/v1/leads/{lead.id}/assign/", {"assigned_to": str(sales_executive.id)}, format="json"
    )
    assert response.status_code == 403
