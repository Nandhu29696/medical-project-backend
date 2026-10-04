"""Django's MySQL backend with two fixes for MariaDB on shared hosting (e.g. Hostinger).

1. UUIDs stay char(32) on MariaDB too (see DatabaseFeatures), matching the MySQL schema.
2. Local-date grouping works without the server's time zone tables:

Django converts datetimes with CONVERT_TZ(col, 'UTC', 'Asia/Kolkata'). Named zones need the
server's mysql.time_zone* tables, which shared hosts (e.g. Hostinger) don't load, so the
call returns NULL and `__date` filters / TruncDate silently match nothing. When the tables
are missing, this backend passes numeric offsets ('+00:00', '+05:30') instead, which every
server understands. The offset is taken at query time, so zones with daylight saving can be
off by an hour for dates across a DST change; Asia/Kolkata has none.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.backends.mysql import base


def _offset(tzname: str) -> str:
    if tzname.upper() == "UTC":
        return "+00:00"
    minutes = int(datetime.now(ZoneInfo(tzname)).utcoffset().total_seconds() // 60)
    sign = "-" if minutes < 0 else "+"
    hours, mins = divmod(abs(minutes), 60)
    return f"{sign}{hours:02d}:{mins:02d}"


class DatabaseOperations(base.DatabaseOperations):
    def _convert_sql_to_tz(self, sql, params, tzname):
        if (
            tzname
            and settings.USE_TZ
            and self.connection.timezone_name != tzname
            and not self.connection.features.has_zoneinfo_database
        ):
            target = self._prepare_tzname_delta(tzname)
            if target[:1] not in "+-":
                target = _offset(target)
            source = _offset(self.connection.timezone_name)
            return f"CONVERT_TZ({sql}, %s, %s)", (*params, source, target)
        return super()._convert_sql_to_tz(sql, params, tzname)


class DatabaseFeatures(base.DatabaseFeatures):
    # Django 5 maps UUIDField to MariaDB 10.7+'s native UUID type and sends dashed values,
    # which don't fit the char(32) columns created on MySQL. Keep char(32) everywhere so
    # one schema (and one .sql dump) works on both MySQL and MariaDB.
    has_native_uuid_field = False


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations
