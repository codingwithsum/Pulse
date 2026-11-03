from django.core.management.base import BaseCommand, CommandError

from apps.ingestion.connectors.rmc_portal import RMCPortalConnector
from apps.ingestion.models import DataSource


class Command(BaseCommand):
    help = "Pull new complaints from the RMC grievance portal feed. Schedule via cron (e.g. every 15 minutes)."

    def handle(self, *args, **opts):
        ds = DataSource.objects.filter(source_type="RMC_PORTAL", is_active=True).select_related("config").first()
        if not ds or not getattr(ds, "config", None) or not ds.config.api_endpoint:
            raise CommandError("RMC portal is not configured: add a DataSource (RMC_PORTAL) with a ConnectorConfig api_endpoint in the admin.")
        run = RMCPortalConnector(ds).sync()
        self.stdout.write(self.style.SUCCESS(
            f"{run.imported_rows} new, {run.duplicate_rows} duplicates, {run.error_rows} errors (of {run.total_rows})"))
