from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Copy files from the local media/ folder into the configured storage (e.g. the database)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", default=str(settings.MEDIA_ROOT), help="Folder to copy from."
        )

    def handle(self, *args, source, **options):
        root = Path(source)
        copied = skipped = 0
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            name = path.relative_to(root).as_posix()
            if default_storage.exists(name):
                skipped += 1
                continue
            with path.open("rb") as fh:
                saved = default_storage.save(name, File(fh, name=name))
            if saved != name:  # never expected: the name was free a moment ago
                self.stderr.write(f"Saved {name} as {saved}")
            copied += 1
        self.stdout.write(
            self.style.SUCCESS(f"Copied {copied} file(s), {skipped} already present.")
        )
