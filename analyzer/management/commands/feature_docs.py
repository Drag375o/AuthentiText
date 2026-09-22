from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from analyzer.services.features import FEATURES

UNITS = {"count": "count", "words": "words", "ratio": "share (0-1, shown as %)", "per100": "per 100 words",
         "zipf": "Zipf score", "number": "number"}


class Command(BaseCommand):
    help = "Generate docs/FEATURES.md from the feature registry (analyzer/services/features.py)."

    def add_arguments(self, parser):
        # Writing the file directly avoids shell redirection, which in Windows
        # PowerShell 5.1 produces UTF-16 instead of UTF-8.
        parser.add_argument("--write", action="store_true", help="Write docs/FEATURES.md (UTF-8) instead of printing.")

    def handle(self, *args, write=False, **options):
        lines = ["# Features", "",
                 "Generated from `analyzer/services/features.py` by `python manage.py feature_docs --write`.",
                 "Don't edit this file by hand; change the registry and regenerate it.", ""]
        for category in dict.fromkeys(f.category for f in FEATURES):
            lines += [f"## {category.title()}", "", "| Name | Label | Unit | What it measures |", "|---|---|---|---|"]
            for f in (f for f in FEATURES if f.category == category):
                lines.append(f"| `{f.name}` | {f.label} | {UNITS[f.unit]} | {f.description} |")
            lines.append("")
        content = "\n".join(lines) + "\n"
        if write:
            path = Path(settings.BASE_DIR) / "docs" / "FEATURES.md"
            path.parent.mkdir(exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
            self.stdout.write(self.style.SUCCESS(f"Wrote {path}"))
        else:
            self.stdout.write(content)
