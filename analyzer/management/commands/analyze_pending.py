from django.core.management.base import BaseCommand

from analyzer.models import Analysis
from analyzer.services.pipeline import PIPELINE_VERSION, analyze_document


class Command(BaseCommand):
    help = "Run the NLP pipeline for documents that are pending, failed, or from an older pipeline version."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Re-analyze every document, not only outdated ones.")

    def handle(self, *args, all=False, **options):
        queryset = Analysis.objects.all()
        if not all:
            queryset = queryset.exclude(status=Analysis.Status.COMPLETE, pipeline_version=PIPELINE_VERSION)
        total = queryset.count()
        if not total:
            self.stdout.write("Nothing to analyze.")
            return
        ok = 0
        for i, analysis in enumerate(queryset.iterator(), start=1):
            done = analyze_document(analysis)
            ok += done
            self.stdout.write(f"[{i}/{total}] {'ok  ' if done else 'FAIL'} {analysis.display_name}")
        self.stdout.write(self.style.SUCCESS(f"Analyzed {ok} of {total} document(s)."))
