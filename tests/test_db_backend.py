from datetime import UTC, date, datetime

import pytest
from django.db import connection
from django.db.models.functions import TruncDate

from apps.accounts.models import User
from common.db.mysql.base import _offset

pytestmark = pytest.mark.skipif(connection.vendor != "mysql", reason="MySQL/MariaDB backend only")


def test_offset_formats_named_zones():
    assert _offset("UTC") == "+00:00"
    assert _offset("Asia/Kolkata") == "+05:30"
    assert _offset("America/St_Johns") in ("-03:30", "-02:30")


@pytest.mark.django_db
def test_local_date_grouping_works_without_server_time_zone_tables(super_admin):
    # 20:00 UTC on 1 Mar is already 2 Mar in India (UTC+05:30).
    users = User.objects.filter(pk=super_admin.pk)
    users.update(created_at=datetime(2026, 3, 1, 20, 0, tzinfo=UTC))
    features = connection.features
    original = features.__dict__.get("has_zoneinfo_database")
    features.__dict__["has_zoneinfo_database"] = False  # behave like shared hosting
    try:
        days = users.annotate(day=TruncDate("created_at")).values_list("day", flat=True)
        assert list(days) == [date(2026, 3, 2)]
        assert users.filter(created_at__date=date(2026, 3, 2)).exists()
    finally:
        if original is None:
            features.__dict__.pop("has_zoneinfo_database", None)
        else:
            features.__dict__["has_zoneinfo_database"] = original


def test_uuid_columns_stay_char32():
    assert connection.data_types["UUIDField"] == "char(32)"
