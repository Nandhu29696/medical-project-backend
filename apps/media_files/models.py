from django.db import models


class StoredFile(models.Model):
    """An uploaded file kept in the database (see apps.media_files.storage)."""

    name = models.CharField(max_length=255, unique=True)
    content = models.BinaryField()
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "stored_files"
        ordering = ["name"]

    def __str__(self):
        return self.name
