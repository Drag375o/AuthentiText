from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ml.training.train_baseline import train


class Command(BaseCommand):
    help = "Train the baseline detector from a JSONL file of labelled documents."

    def add_arguments(self, parser):
        parser.add_argument("data", type=Path, help="JSONL file: one {\"text\": ..., \"label\": \"human\"|\"ai\"} per line")
        parser.add_argument("--output", type=Path, default=None, help="Where to save the model bundle")
        parser.add_argument("--version", default="baseline-0.1")

    def handle(self, *args, data: Path, output: Path | None, version: str, **options):
        if not data.exists():
            raise CommandError(f"No such file: {data}")
        output = output or Path(settings.BASE_DIR) / "ml" / "models" / "baseline.joblib"
        try:
            report = train(data, output, version)
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(report.summary())
        self.stdout.write(self.style.SUCCESS(
            "\nRestart the server to use it. Documents analyzed earlier keep their old result "
            "until you run: python manage.py analyze_pending --all"))
