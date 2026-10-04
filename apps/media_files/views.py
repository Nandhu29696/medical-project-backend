import mimetypes

from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse
from django.views.decorators.http import require_GET


@require_GET
def serve_media(request, path):
    """Serve an uploaded file from the configured storage (database or disk) at /media/<path>."""
    if ".." in path.split("/"):
        raise Http404
    try:
        with default_storage.open(path) as f:
            data = f.read()
    except (FileNotFoundError, OSError):
        raise Http404 from None
    response = HttpResponse(
        data, content_type=mimetypes.guess_type(path)[0] or "application/octet-stream"
    )
    # Stored names never change content (a new upload gets a new name), so browsers can keep them.
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
