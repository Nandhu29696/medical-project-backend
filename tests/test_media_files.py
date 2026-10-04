import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.media_files.models import StoredFile
from apps.media_files.storage import DatabaseStorage


@pytest.mark.django_db
def test_uploads_are_stored_in_the_database_and_served_from_media(client):
    assert isinstance(default_storage._wrapped, DatabaseStorage) or isinstance(
        default_storage, DatabaseStorage
    )
    name = default_storage.save("products/2026/10/pill.png", ContentFile(b"\x89PNG-bytes"))
    assert name == "products/2026/10/pill.png"
    assert StoredFile.objects.get(name=name).size == 10
    assert default_storage.url(name) == "/media/products/2026/10/pill.png"

    response = client.get("/media/products/2026/10/pill.png")
    assert response.status_code == 200
    assert response.content == b"\x89PNG-bytes"
    assert response["Content-Type"] == "image/png"
    assert "immutable" in response["Cache-Control"]


@pytest.mark.django_db
def test_same_name_gets_a_new_name_and_delete_removes_the_row():
    first = default_storage.save("doctors/a.png", ContentFile(b"one"))
    second = default_storage.save("doctors/a.png", ContentFile(b"two"))
    assert first != second
    assert default_storage.open(first).read() == b"one"
    assert default_storage.listdir("doctors") == (
        [],
        sorted([first, second][i].split("/")[-1] for i in (0, 1)),
    )
    default_storage.delete(first)
    assert not default_storage.exists(first)


@pytest.mark.django_db
def test_missing_or_traversal_paths_are_404(client):
    assert client.get("/media/nope.png").status_code == 404
    assert client.get("/media/../config/settings/base.py").status_code == 404
