"""Keep uploaded files (product images, photos, documents) in the database.

Serverless hosts such as Vercel have no lasting disk, so files saved to MEDIA_ROOT vanish.
Storing them in the database keeps them with the rest of the data, on every server, with
no extra service. Suited to small files: uploads are capped at 10 MB (and ~4.5 MB on Vercel).
"""

import mimetypes
import posixpath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri


@deconstructible
class DatabaseStorage(Storage):
    @staticmethod
    def _model():
        from apps.media_files.models import StoredFile

        return StoredFile

    @staticmethod
    def _clean(name):
        return posixpath.normpath(str(name).replace("\\", "/")).lstrip("/")

    def _open(self, name, mode="rb"):
        try:
            row = self._model().objects.only("content").get(name=self._clean(name))
        except self._model().DoesNotExist:
            raise FileNotFoundError(name) from None
        file = ContentFile(bytes(row.content), name=name)
        file.mode = mode
        return file

    def _save(self, name, content):
        name = self._clean(name)
        if hasattr(content, "seek"):
            content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()
        content_type = getattr(content, "content_type", None) or mimetypes.guess_type(name)[0] or ""
        self._model().objects.update_or_create(
            name=name,
            defaults={"content": data, "size": len(data), "content_type": content_type[:100]},
        )
        return name

    def exists(self, name):
        return self._model().objects.filter(name=self._clean(name)).exists()

    def delete(self, name):
        if name:
            self._model().objects.filter(name=self._clean(name)).delete()

    def size(self, name):
        row = self._model().objects.filter(name=self._clean(name)).values("size").first()
        if row is None:
            raise FileNotFoundError(name)
        return row["size"]

    def url(self, name):
        return settings.MEDIA_URL + filepath_to_uri(self._clean(name))

    def listdir(self, path):
        prefix = self._clean(path).rstrip("/") + "/" if path else ""
        dirs, files = set(), []
        names = self._model().objects.filter(name__startswith=prefix).values_list("name", flat=True)
        for name in names:
            head, _, tail = name[len(prefix) :].partition("/")
            if tail:
                dirs.add(head)
            else:
                files.append(head)
        return sorted(dirs), sorted(files)
