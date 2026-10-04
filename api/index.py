"""Vercel entry point: every request is routed here (see vercel.json)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = get_wsgi_application()
