from datetime import timedelta
from typing import List, Dict, Any
from django.utils import timezone
from django.db.models import Count

from apps.master_data.models import Department, CivicLocation, CivicCategory
from apps.intelligence.models import FeedbackAnalysis
from apps.analytics.models import TrendAlert
from apps.notifications.services import dispatch_trend_notifications

def detect_civic_trends(
    time_window_hours: int = 24,
    baseline_days: int = 7,
    min_volume_threshold: int = 5,
    min_spike_ratio: float = 2.0
) -> List[TrendAlert]:
    """
    Statistical spike detection engine.
    Calculates rolling baselines and identifies anomalous complaint surges
    for (Department, CivicLocation) pairs.
    """
    now = timezone.now()
    window_start = now - timedelta(hours=time_window_hours)
    baseline_start = now - timedelta(days=baseline_days)

    created_alerts = []

    # 1. Calculate current volume per (Department, Location, Category)
    current_counts = (
        FeedbackAnalysis.objects.filter(
            created_at__gte=window_start,
            suggested_department__isnull=False,
            is_active_version=True
        )
        .values('suggested_department', 'extracted_location', 'category')
        .annotate(vol=Count('id'))
    )

    for item in current_counts:
        curr_vol = item['vol']
        if curr_vol < min_volume_threshold:
            continue  # Insufficient sample size to prevent isolated false alarms

        dept_id = item['suggested_department']
        loc_id = item['extracted_location']
        cat_id = item['category']

        # 2. Calculate baseline volume over past baseline_days (excluding current window)
        baseline_qs = FeedbackAnalysis.objects.filter(
            created_at__gte=baseline_start,
            created_at__lt=window_start,
            suggested_department_id=dept_id,
            is_active_version=True
        )
        if loc_id:
            baseline_qs = baseline_qs.filter(extracted_location_id=loc_id)
        if cat_id:
            baseline_qs = baseline_qs.filter(category_id=cat_id)

        historical_count = baseline_qs.count()
        # Daily average scaled to the active window length
        daily_baseline = historical_count / max(baseline_days - (time_window_hours / 24.0), 1.0)
        expected_window_vol = max(daily_baseline * (time_window_hours / 24.0), 1.0)

        spike_ratio = round(curr_vol / expected_window_vol, 2)

        if spike_ratio >= min_spike_ratio:
            dept = Department.objects.get(id=dept_id)
            loc = CivicLocation.objects.filter(id=loc_id).first() if loc_id else None
            cat = CivicCategory.objects.filter(id=cat_id).first() if cat_id else None

            # Get sample evidence UUIDs
            evidence_analyses = FeedbackAnalysis.objects.filter(
                created_at__gte=window_start,
                suggested_department_id=dept_id,
                is_active_version=True
            )
            if loc_id:
                evidence_analyses = evidence_analyses.filter(extracted_location_id=loc_id)
            sample_uuids = [str(a.feedback_item_id) for a in evidence_analyses[:5]]

            # Determine severity
            severity = "WARNING"
            has_emergency = evidence_analyses.filter(urgency__in=["EMERGENCY", "HIGH"]).exists()
            if spike_ratio >= 3.0 and has_emergency:
                severity = "CRITICAL"
            elif spike_ratio < 2.5:
                severity = "ADVISORY"

            loc_str = loc.ward_name if loc else "Citywide"
            cat_str = cat.name if cat else "Civic Issues"
            title = f"{int(spike_ratio * 100)}% Surge in {cat_str} in {loc_str}"

            # Create or update active alert
            alert, created = TrendAlert.objects.get_or_create(
                department=dept,
                location=loc,
                category=cat,
                is_acknowledged=False,
                defaults={
                    "alert_title": title,
                    "time_window_start": window_start,
                    "time_window_end": now,
                    "baseline_volume": round(expected_window_vol, 1),
                    "current_volume": curr_vol,
                    "spike_ratio": spike_ratio,
                    "severity": severity,
                    "sample_evidence_ids": sample_uuids,
                }
            )
            if not created:
                alert.current_volume = curr_vol
                alert.spike_ratio = spike_ratio
                alert.severity = severity
                alert.save(update_fields=["current_volume", "spike_ratio", "severity", "updated_at"])

            created_alerts.append(alert)

            # Proactively trigger staff notification
            dispatch_trend_notifications(alert)

    return created_alerts
