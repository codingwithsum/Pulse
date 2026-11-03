import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.feedback.models import FeedbackItem
from apps.ingestion.models import ConnectorConfig, DataSource, ImportRun
from apps.intelligence.services import analyze_and_store_feedback

from .base import BaseConnector, IngestionBatchResult, NormalizedFeedbackPayload

DATE_FORMATS = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %I:%M %p", "%d-%m-%Y %H:%M", "%d/%m/%Y"]

# Default JSON keys of one complaint in the RMC feed; override per deployment via
# ConnectorConfig.settings_json["field_map"]. Citizen name / mobile keys are never read.
DEFAULT_FIELD_MAP = {
    "complaint_no": "complaint_no",
    "department": "department",
    "complaint_type": "complaint_type",
    "complaint_date": "complaint_date",
    "zone": "zone",
    "ward": "ward",
    "address": "address",
    "remarks": "remarks",
}


class RMCPortalConnector(BaseConnector):
    """
    Live pull of new complaints from the RMC grievance portal, so no manual export is needed.

    Expects an authorised endpoint that returns a JSON list (or {"results": [...]}) of complaints and
    accepts a `since` query parameter. Run it on a schedule with `manage.py sync_rmc_portal`.
    """
    connector_id = "rmc-egov-portal"
    connector_name = "RMC Citizen Grievance Portal"

    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self.config = getattr(data_source, "config", None)

    # -- configuration / health -------------------------------------------------
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("api_endpoint"))

    def _settings(self) -> Dict[str, Any]:
        return (self.config.settings_json if self.config else {}) or {}

    def _request(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        url = self.config.api_endpoint
        if since:
            sep = "&" if "?" in url else "?"
            url += sep + urllib.parse.urlencode({self._settings().get("since_param", "since"): since.isoformat()})
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        if self.config.encrypted_credentials:
            req.add_header("Authorization", f"Bearer {self.config.encrypted_credentials}")
        with urllib.request.urlopen(req, timeout=self._settings().get("timeout", 30)) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body.get("results", []) if isinstance(body, dict) else body

    def test_connection(self) -> Dict[str, Any]:
        if not (self.config and self.validate_configuration({"api_endpoint": self.config.api_endpoint})):
            return {"status": "PENDING_CONFIG", "message": "No RMC portal API endpoint configured yet."}
        try:
            self._request(since=timezone.now())
        except (urllib.error.URLError, ValueError, OSError) as e:
            return {"status": "DISCONNECTED", "message": f"Could not reach the RMC portal: {e}"}
        return {"status": "HEALTHY", "message": "Connected to the RMC portal feed."}

    # -- normalisation ----------------------------------------------------------
    def normalize(self, raw_record: Dict[str, Any]) -> NormalizedFeedbackPayload:
        fm = {**DEFAULT_FIELD_MAP, **self._settings().get("field_map", {})}
        get = lambda k: str(raw_record.get(fm[k]) or "").strip()
        dept, ctype, cno, address, remarks = get("department"), get("complaint_type"), get("complaint_no"), get("address"), get("remarks")

        parts = []
        if dept:
            parts.append(f"[{dept}]")
        if ctype:
            parts.append(ctype)
        if address:
            parts.append(f"at {address}")
        if remarks:
            parts.append(f"— Note: {remarks}")

        pub_date = timezone.now()
        for fmt in DATE_FORMATS:
            try:
                pub_date = timezone.make_aware(datetime.strptime(get("complaint_date"), fmt))
                break
            except ValueError:
                pass

        return NormalizedFeedbackPayload(
            raw_text=" ".join(parts) if (ctype or address) else "",
            external_id=cno,
            source_type="OFFICIAL_WEBSITE",
            source_platform="RMC_PORTAL",
            published_at=pub_date,
            anonymized_sender_hash=hashlib.sha256(f"rmc-{cno}".encode()).hexdigest()[:16],
            technical_metadata={
                "rmc_zone": get("zone"), "rmc_ward": get("ward"),
                "original_dept": dept, "original_complaint_type": ctype,
                "platform": "RMC Portal",
            },
        )

    # -- sync -------------------------------------------------------------------
    def sync(self) -> ImportRun:
        """Fetch complaints newer than the last sync, dedupe, analyse and store them."""
        ds = self.data_source
        run = ImportRun.objects.create(data_source=ds, file_name="RMC portal live sync", status="PROCESSING")
        result = IngestionBatchResult()
        started = timezone.now()
        try:
            for raw in self._request(since=ds.last_sync_at):
                result.total_processed += 1
                try:
                    payload = self.normalize(raw)
                    if not payload.raw_text or not payload.external_id:
                        continue
                    if FeedbackItem.objects.filter(content_hash=payload.content_hash).exists() or \
                            FeedbackItem.objects.filter(data_source=ds, external_id=payload.external_id).exists():
                        result.duplicates_blocked += 1
                        continue
                    with transaction.atomic():
                        item = FeedbackItem.objects.create(
                            data_source=ds, import_run=run, external_id=payload.external_id,
                            content_hash=payload.content_hash, raw_text=payload.raw_text,
                            detected_language="und", published_at=payload.published_at,
                            raw_metadata=payload.technical_metadata, status="PENDING_ANALYSIS",
                        )
                        analyze_and_store_feedback(item)
                    result.new_items_count += 1
                except Exception as e:
                    result.errors_count += 1
                    result.error_details.append(f"Complaint {raw.get(DEFAULT_FIELD_MAP['complaint_no'], '?')}: {e}")
        except Exception as e:
            run.status, run.error_log = "FAILED", [f"Portal fetch failed: {e}"]
            run.save()
            ds.health_status, ds.error_message = "DISCONNECTED", str(e)
            ds.save(update_fields=["health_status", "error_message"])
            raise

        run.total_rows, run.imported_rows = result.total_processed, result.new_items_count
        run.duplicate_rows, run.error_rows = result.duplicates_blocked, result.errors_count
        run.status, run.error_log = "COMPLETED", result.error_details[:50]
        run.save()
        ds.last_sync_at, ds.health_status, ds.error_message = started, "HEALTHY", ""
        ds.save(update_fields=["last_sync_at", "health_status", "error_message"])
        return run
