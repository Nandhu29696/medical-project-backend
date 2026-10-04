import os

if os.environ.get("VERCEL"):
    # Never run with DEBUG on a deployed site, whichever settings module the host picked.
    from .production import *  # noqa: F403
else:
    from .base import *  # noqa: F403

    DEBUG = True

    INSTALLED_APPS += []  # noqa: F405

    CORS_ALLOW_ALL_ORIGINS = True
