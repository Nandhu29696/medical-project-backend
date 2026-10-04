import os

from django.core.asgi import get_asgi_application

# Vercel sets VERCEL=1 (build and runtime): use production settings there.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.production" if os.environ.get("VERCEL") else "config.settings.development",
)

application = get_asgi_application()
