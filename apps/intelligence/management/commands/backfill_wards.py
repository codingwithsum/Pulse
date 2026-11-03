from django.core.management.base import BaseCommand

from apps.intelligence.models import FeedbackAnalysis
from apps.intelligence.services import official_ward_number
from apps.master_data.models import CivicLocation


class Command(BaseCommand):
    help = "Set the ward on existing analyses from the official RMC ward recorded with each complaint."

    def handle(self, *args, **options):
        wards = {w.ward_number: w for w in CivicLocation.objects.all()}
        qs = FeedbackAnalysis.objects.filter(is_active_version=True).select_related("feedback_item")
        updated = unchanged = no_ward = 0
        for analysis in qs:
            number = official_ward_number(analysis.feedback_item.raw_metadata)
            if not number or number not in wards:
                no_ward += 1
                continue
            if analysis.extracted_location_id == wards[number].id:
                unchanged += 1
                continue
            analysis.extracted_location = wards[number]
            analysis.save(update_fields=["extracted_location", "updated_at"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(
            f"Wards set on {updated} analyses; {unchanged} already correct; {no_ward} have no official ward."))
