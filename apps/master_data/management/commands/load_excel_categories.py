import os
import openpyxl
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.master_data.models import Department, CivicCategory, CivicLocation

class Command(BaseCommand):
    help = 'Extracts official RMC Complaint Types and Departments from the official Excel dataset and syncs CivicCategory.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Complaint Details 01-10-2026 to 10-10-2026.xlsx',
            help='Path to the official RMC complaints Excel file.'
        )

    def handle(self, *args, **options):
        file_path = options['file']

        # Check in project root or relative path
        if not os.path.exists(file_path):
            candidates = [
                file_path,
                os.path.join(os.getcwd(), file_path),
                'Complaint Details 01-10-2026 to 10-10-2026.xlsx',
                'complaints.xlsx',
                'complaint_details.xlsx',
            ]
            for c in candidates:
                if os.path.exists(c):
                    file_path = c
                    break

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(
                f"Excel file '{file_path}' not found!\n"
                f"Please place your official Excel file in D:\\PULSE-main\\ and run:\n"
                f"  python manage.py load_excel_categories --file <your_file.xlsx>"
            ))
            return

        self.stdout.write(self.style.NOTICE(f"Loading official RMC categories from: {file_path}..."))

        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active

        # Identify column headers from the first 5 rows
        header_row = 1
        col_map = {}
        for r in range(1, min(10, ws.max_row + 1)):
            row_vals = [str(ws.cell(row=r, column=c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]
            if any("department" in v for v in row_vals) and any("complaint" in v for v in row_vals):
                header_row = r
                for c in range(1, ws.max_column + 1):
                    val = str(ws.cell(row=r, column=c).value or "").strip().lower()
                    if "department" in val:
                        col_map["dept"] = c
                    elif "complaint type" in val or "category" in val or "type" in val:
                        col_map["type"] = c
                    elif "complaint no" in val:
                        col_map["no"] = c
                    elif "ward" in val:
                        col_map["ward"] = c
                    elif "zone" in val:
                        col_map["zone"] = c
                break

        # Fallback if headers were on default columns
        dept_col = col_map.get("dept", 2)
        type_col = col_map.get("type", 3)

        self.stdout.write(f"Header row detected at {header_row}. Department col: {dept_col}, Complaint Type col: {type_col}.")

        dept_categories = {}
        rows_processed = 0

        for r in range(header_row + 1, ws.max_row + 1):
            raw_dept = ws.cell(row=r, column=dept_col).value
            raw_type = ws.cell(row=r, column=type_col).value

            if raw_dept and raw_type:
                dept_name = str(raw_dept).strip()
                type_name = str(raw_type).strip()

                if dept_name and type_name:
                    if dept_name not in dept_categories:
                        dept_categories[dept_name] = set()
                    dept_categories[dept_name].add(type_name)
                    rows_processed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Processed {rows_processed} complaint records.\n"
            f"Extracted {len(dept_categories)} unique Departments and "
            f"{sum(len(v) for v in dept_categories.values())} unique Complaint Types."
        ))

        # Synchronize into Department and CivicCategory models
        total_created = 0
        for dept_name, types in dept_categories.items():
            dept_code = slugify(dept_name)[:50]
            dept_obj, _ = Department.objects.get_or_create(
                name=dept_name,
                defaults={"code": dept_code, "is_active": True}
            )

            for t_name in sorted(types):
                cat_code = slugify(f"{dept_obj.code}-{t_name[:35]}")[:50]
                CivicCategory.objects.update_or_create(
                    department=dept_obj,
                    name=t_name,
                    defaults={
                        "code": cat_code,
                        "keywords_en": t_name.lower(),
                        "is_active": True,
                    }
                )
                total_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully synchronized {total_created} official complaint categories across {len(dept_categories)} departments into database!"
        ))

