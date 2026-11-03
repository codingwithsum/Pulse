import json
from unittest import mock

from django.test import TestCase

from apps.feedback.models import FeedbackItem
from apps.ingestion.connectors.rmc_portal import RMCPortalConnector
from apps.ingestion.models import ConnectorConfig, DataSource

FEED = [
    {"complaint_no": "C1", "department": "Drainage", "complaint_type": "Drainage Chockup", "complaint_date": "2026-10-20 10:00:00",
     "ward": "10", "address": "Mavdi", "remarks": "", "citizen_name": "X", "mobile": "999"},
    {"complaint_no": "C2", "department": "Drainage", "complaint_type": "Drainage Chockup", "address": "Mavdi", "complaint_date": "2026-10-20 10:00:00"},
    {"complaint_no": "C3", "complaint_type": "", "address": ""},
]


class RMCPortalSyncTests(TestCase):
    def setUp(self):
        self.ds = DataSource.objects.create(name="RMC Portal", source_type="RMC_PORTAL")
        ConnectorConfig.objects.create(data_source=self.ds, api_endpoint="https://example.invalid/feed")
        self.ds.refresh_from_db()

    def test_sync_stores_new_dedupes_and_discards_pii(self):
        with mock.patch.object(RMCPortalConnector, "_request", return_value=FEED):
            run = RMCPortalConnector(self.ds).sync()
        self.assertEqual((run.imported_rows, run.duplicate_rows), (1, 1))
        item = FeedbackItem.objects.get(external_id="C1")
        self.assertNotIn("999", json.dumps(item.raw_metadata) + item.raw_text)
        self.ds.refresh_from_db()
        self.assertEqual(self.ds.health_status, "HEALTHY")
        self.assertIsNotNone(self.ds.last_sync_at)

    def test_unconfigured_reports_pending(self):
        self.ds.config.api_endpoint = ""
        self.ds.config.save()
        self.assertEqual(RMCPortalConnector(DataSource.objects.get(pk=self.ds.pk)).test_connection()["status"], "PENDING_CONFIG")
