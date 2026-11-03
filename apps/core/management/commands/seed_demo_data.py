import hashlib
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from apps.master_data.models import Department, CivicCategory, CivicLocation
from apps.accounts.models import StaffProfile
from apps.ingestion.models import DataSource, ConnectorConfig, ImportRun
from apps.feedback.models import FeedbackItem
from apps.intelligence.models import FeedbackAnalysis, AnalysisReview
from apps.analytics.models import TrendAlert
from apps.notifications.models import StaffNotificationPreference, NotificationDeliveryLog
from apps.audit_compliance.models import AuditLog

class Command(BaseCommand):
    help = 'Seeds the database with strictly synthetic demo records for Rajkot Municipal Corporation.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing RMC PULSE synthetic database seed..."))

        # 1. Master Data: Departments
        departments_data = [
            {"name": "Engineering & Roads", "code": "engineering-roads", "head_title": "Executive Engineer (Roads)", "head_email": "ee.roads@rmc.gov.in"},
            {"name": "Water Works Department", "code": "water-works", "head_title": "Superintending Engineer (Water)", "head_email": "se.water@rmc.gov.in"},
            {"name": "Drainage & Sewerage", "code": "drainage-sewerage", "head_title": "Chief Drainage Officer", "head_email": "cdo.drainage@rmc.gov.in"},
            {"name": "Solid Waste Management", "code": "solid-waste", "head_title": "Director (Cleanliness & SWM)", "head_email": "dir.swm@rmc.gov.in"},
            {"name": "Health & Sanitation", "code": "health-sanitation", "head_title": "Medical Officer of Health (MOH)", "head_email": "moh.health@rmc.gov.in"},
            {"name": "Traffic & Street Lighting", "code": "traffic-streetlighting", "head_title": "Traffic & Electrical Engineer", "head_email": "tee.traffic@rmc.gov.in"},
        ]
        dept_map = {}
        for d in departments_data:
            dept, _ = Department.objects.get_or_create(code=d["code"], defaults=d)
            dept_map[d["code"]] = dept
        self.stdout.write(self.style.SUCCESS(f"  Created {len(dept_map)} RMC municipal departments."))

        # 2. Master Data: Civic Categories
        categories_data = [
            {"dept": "engineering-roads", "name": "Potholes & Road Damage", "code": "potholes", "en": "pothole, broken road, ditch", "gu": "ખાડા, રસ્તો, તૂટેલો રોડ, ડામર", "hi": "गड्ढे, सड़क"},
            {"dept": "engineering-roads", "name": "Footpath & Curb Repair", "code": "footpath", "en": "footpath, pavement, curb", "gu": "ફૂટપાથ, પેવર બ્લોક", "hi": "फुटपाथ"},
            {"dept": "water-works", "name": "Drinking Water Contamination", "code": "water-contamination", "en": "dirty water, foul smell, turbid", "gu": "ગંદુ પાણી, પીવાનું પાણી, વાસ", "hi": "गंदा पानी, बदबूदार"},
            {"dept": "water-works", "name": "Pipeline Leakage & Low Pressure", "code": "pipeline-leak", "en": "pipe leak, low pressure, no water", "gu": "પાઇપ લીકેજ, ધીમું પાણી, પાણી નથી આવતું", "hi": "पाइपलाइन लीकेज, कम प्रेशर"},
            {"dept": "drainage-sewerage", "name": "Manhole Overflow & Sewer Blockage", "code": "manhole-overflow", "en": "sewage, drain choke, gutter overflow", "gu": "ગટર, ઉભરાય છે, ચોકઅપ, મેનહોલ", "hi": "गटर, सीवर, ओवरफ्लो"},
            {"dept": "solid-waste", "name": "Garbage Container Overflow", "code": "garbage-overflow", "en": "garbage, trash bin, dumping", "gu": "કચરો, કચરાપેટી, ગંદકી, ડમ્પિંગ", "hi": "कचरा, डस्टबिन"},
            {"dept": "solid-waste", "name": "Door-to-Door Van Irregularity", "code": "door-to-door-van", "en": "door to door, tipper van", "gu": "ટીપર વાન, કચરાની ગાડી નથી આવી", "hi": "कचरा गाड़ी"},
            {"dept": "traffic-streetlighting", "name": "Streetlight Failure / Dark Spot", "code": "streetlight-off", "en": "streetlight, dark, pole bulb", "gu": "લાઈટ, અંધારું, થાંભલો, બંધ છે", "hi": "स्ट्रीट लाइट, अंधेरा"},
            {"dept": "traffic-streetlighting", "name": "Stray Cattle & Traffic Disruption", "code": "stray-cattle", "en": "stray cattle, cow, traffic jam", "gu": "રખડતા ઢોર, ગાય, ટ્રાફિક જામ", "hi": "आवारा पशु, गाय, जाम"},
            {"dept": "health-sanitation", "name": "Mosquito Fogging Request", "code": "mosquito-fogging", "en": "mosquito, malaria, dengue, fogging", "gu": "મચ્છર, દવા છંટકાવ, મેલેરિયા", "hi": "मच्छर, फॉगिंग"},
        ]
        cat_map = {}
        for c in categories_data:
            cat, _ = CivicCategory.objects.get_or_create(
                code=c["code"],
                defaults={
                    "department": dept_map[c["dept"]],
                    "name": c["name"],
                    "keywords_en": c["en"],
                    "keywords_gu": c["gu"],
                    "keywords_hi": c["hi"],
                }
            )
            cat_map[c["code"]] = cat
        self.stdout.write(self.style.SUCCESS(f"  Created {len(cat_map)} civic categories with multilingual keywords."))

        # 3. Master Data: Wards 1 to 18
        wards_data = [
            # West Zone
            {"zone": "WEST", "ward_number": 7, "ward_name": "Amin Marg / Race Course", "landmarks": "Race Course Ground, Prem Mandir, Amin Marg, Kotecha Chowk"},
            {"zone": "WEST", "ward_number": 8, "ward_name": "University Road / Indira Circle", "landmarks": "Saurashtra University, Indira Circle, Sadhu Vaswani Road"},
            {"zone": "WEST", "ward_number": 9, "ward_name": "Raiya Road / Nana Mava", "landmarks": "Nana Mava Circle, Raiya Telephone Exchange, Speedwell Party Plot"},
            {"zone": "WEST", "ward_number": 10, "ward_name": "150 Feet Ring Road / Mavdi", "landmarks": "Mavdi Chowkadi, Umiya Chowk, Puneet Nagar"},
            {"zone": "WEST", "ward_number": 11, "ward_name": "Kalawad Road / Pushkar Dham", "landmarks": "Pushkar Dham, Cosmoplex, Haridarshan"},
            {"zone": "WEST", "ward_number": 12, "ward_name": "Vavdi / Kankot Road", "landmarks": "Government Engineering College, Kankot, Vavdi Industrial"},
            # Central Zone
            {"zone": "CENTRAL", "ward_number": 2, "ward_name": "Railnagar / Popatpara", "landmarks": "Railnagar Underpass, Popatpara, Railway Station Colony"},
            {"zone": "CENTRAL", "ward_number": 3, "ward_name": "Dharmendrasinhji Road / Danapith", "landmarks": "Danapith, Dharmendra Road, Soni Bazaar, Para Bazaar"},
            {"zone": "CENTRAL", "ward_number": 4, "ward_name": "Gondal Road / Bhaktinagar", "landmarks": "Bhaktinagar Circle, Malaviya Chowk, Gondal Road Overbridge"},
            {"zone": "CENTRAL", "ward_number": 5, "ward_name": "Dhebar Road / Trikon Baug", "landmarks": "Trikon Baug Bus Station, Jubilee Garden, Alfred High School"},
            {"zone": "CENTRAL", "ward_number": 6, "ward_name": "Karanpara / Sadar Bazaar", "landmarks": "Karanpara, Sadar Bazaar, Limda Chowk, Shastri Maidan"},
            {"zone": "CENTRAL", "ward_number": 13, "ward_name": "Tagore Road / Bhaktinagar Station", "landmarks": "Tagore Road, Virani High School, Bhaktinagar Railway Station"},
            # East Zone
            {"zone": "EAST", "ward_number": 1, "ward_name": "Gandhigram / Madhapar", "landmarks": "Madhapar Chowkadi, Gandhigram Police Station, Sheetla Mataji Temple"},
            {"zone": "EAST", "ward_number": 14, "ward_name": "Ranchhod Nagar / Pedak Road", "landmarks": "Pedak Road, Ranchhod Nagar, Champaknagar, Patel Chowk"},
            {"zone": "EAST", "ward_number": 15, "ward_name": "Chunarwad / Sant Kabir Road", "landmarks": "Sant Kabir Road, Chunarwad, Bhavani Nagar, Dudhsagar Road"},
            {"zone": "EAST", "ward_number": 16, "ward_name": "Aji Dam / Bhavanagar Road", "landmarks": "Aji Dam, Chunarwad, Marketing Yard, Bhavanagar Highway"},
            {"zone": "EAST", "ward_number": 17, "ward_name": "Kothariya / Swati Park", "landmarks": "Swati Park, Kothariya Ring Road, Khodiyar Nagar"},
            {"zone": "EAST", "ward_number": 18, "ward_name": "Samrat Industrial Area / Kotharia", "landmarks": "Samrat Industrial, GIDC Aji, Sorathiyawadi"},
        ]
        ward_map = {}
        for w in wards_data:
            ward, _ = CivicLocation.objects.update_or_create(
                ward_number=w["ward_number"],
                defaults={
                    "zone": w["zone"],
                    "ward_name": w["ward_name"],
                    "known_landmarks": w["landmarks"],
                }
            )
            ward_map[w["ward_number"]] = ward
        self.stdout.write(self.style.SUCCESS(f"  Created {len(ward_map)} Rajkot municipal wards across 3 zones."))

        # 4. Staff Users & Profiles
        users_data = [
            {"username": "commissioner", "email": "commissioner@rmc.gov.in", "first": "Shri D. V.", "last": "Mehta", "role": "MUNICIPAL_COMMISSIONER", "emp_id": "RMC-ADMIN-01"},
            {"username": "ee_drainage", "email": "ee.drainage@rmc.gov.in", "first": "Rajesh", "last": "Patel", "role": "DEPT_HEAD", "dept": Department.objects.filter(code="drainage-chockup-overflow").first() or dept_map["engineering-roads"], "emp_id": "RMC-ENG-101"},
            {"username": "ward10_officer", "email": "ward10@rmc.gov.in", "first": "Hitesh", "last": "Vora", "role": "WARD_OFFICER", "ward": ward_map[10], "emp_id": "RMC-WARD-10"},
        ]
        user_map = {}
        for u in users_data:
            user, created = User.objects.get_or_create(
                username=u["username"],
                defaults={"email": u["email"], "first_name": u["first"], "last_name": u["last"]}
            )
            if created:
                user.set_password("RMCpulse2026!")
                user.save()
            user_map[u["username"]] = user

            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    "employee_id": u["emp_id"],
                    "role": u["role"],
                    "department": u.get("dept"),
                    "assigned_ward": u.get("ward"),
                    "phone_number": "+91-281-2224401",
                }
            )
        self.stdout.write(self.style.SUCCESS(f"  Created {len(user_map)} staff profiles with municipal roles."))

        # 5. Data Sources & Configurations
        sources_data = [
            {"name": "WhatsApp Business Cloud API", "source_type": "WHATSAPP", "health": "HEALTHY", "active": True},
            {"name": "CSV Batch Survey Importer", "source_type": "FILE_IMPORT", "health": "HEALTHY", "active": True},
            {"name": "Twitter / X (Official API v2)", "source_type": "TWITTER_X", "health": "HEALTHY", "active": True},
            {"name": "Meta (Facebook & Instagram)", "source_type": "FACEBOOK", "health": "HEALTHY", "active": True},
            {"name": "RMC Citizen Grievance Portal", "source_type": "RMC_PORTAL", "health": "HEALTHY", "active": True},
            {"name": "Gmail / Authorized Municipal Inbox", "source_type": "EMAIL", "health": "HEALTHY", "active": True},
        ]
        source_map = {}
        for s in sources_data:
            src, _ = DataSource.objects.get_or_create(
                name=s["name"],
                defaults={
                    "source_type": s["source_type"],
                    "health_status": s["health"],
                    "is_active": s["active"],
                    "last_sync_at": timezone.now(),
                }
            )
            ConnectorConfig.objects.get_or_create(
                data_source=src,
                defaults={
                    "api_endpoint": f"/api/v1/integrations/{s['source_type'].lower()}/",
                    "webhook_verify_token": "rmc_secure_verify_token_2026",
                    "encrypted_credentials": "ENCRYPTED_MOCK_SECRET_PAYLOAD",
                    "settings_json": {"sync_interval_mins": 15, "batch_limit": 100},
                }
            )
            source_map[s["source_type"]] = src
        self.stdout.write(self.style.SUCCESS(f"  Created {len(source_map)} ingestion sources & connector configs."))

        # 6. Import Run
        import_run, _ = ImportRun.objects.get_or_create(
            file_name="rmc_synthetic_survey_oct2026.csv",
            defaults={
                "data_source": source_map["FILE_IMPORT"],
                "uploaded_by": user_map["commissioner"],
                "total_rows": 6,
                "imported_rows": 6,
                "duplicate_rows": 0,
                "error_rows": 0,
                "status": "COMPLETED",
            }
        )

        # 7. Synthetic Feedback Items & Analyses
        # STRICT PRIVACY: ZERO citizen names, phone numbers, or private credentials
        feedback_seeds = [
            {
                "text": "કાલાવડ રોડ પર પ્રેમ મંદિર પાસે રોડ પર મોટો ખાડો પડી ગયો છે, રાત્રે બાઈક સ્લીપ થઈ ગઈ. તાત્કાલિક રીપેર કરો નહીંતર મોટો અકસ્માત થશે!",
                "lang": "gu",
                "source": "WHATSAPP",
                "ext_id": "wa-synth-001",
                "published_offset_mins": 15,
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.88,
                "cat": "potholes",
                "dept": "engineering-roads",
                "urgency": "EMERGENCY",
                "urgency_reasoning": "Direct road hazard with reported motorbike slip and accident risk.",
                "ward_num": 7,
                "raw_loc": "Kalawad Road, Prem Mandir",
                "confidence": 0.94,
                "theme": "Potholes & Cave-ins",
                "reviewed": True,
            },
            {
                "text": "રેલનગર અંડરપાસ પાસે છેલ્લા 3 દિવસથી ગટરનું ગંદુ પાણી રોડ પર ફરી વળ્યું છે. ચાલવું પણ મુશ્કેલ છે અને ખૂબ દુર્ગંધ આવે છે.",
                "lang": "gu",
                "source": "RMC_PORTAL",
                "ext_id": "rmc-cp-synth-002",
                "published_offset_mins": 45,
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.92,
                "cat": "manhole-overflow",
                "dept": "drainage-sewerage",
                "urgency": "HIGH",
                "urgency_reasoning": "Contaminated blackwater stagnant on public thoroughfare > 48h.",
                "ward_num": 2,
                "raw_loc": "Railnagar Underpass",
                "confidence": 0.91,
                "theme": "Manhole Overflow & Choke-up",
                "reviewed": False,
            },
            {
                "text": "Ward 4 Bhaktinagar area me peene ke paani me ganda badbudaar paani mix ho kar aa raha hai. Bacche bimaar pad rahe hai. Check pipeline leakage immediately.",
                "lang": "hi",
                "source": "TWITTER_X",
                "ext_id": "tw-synth-003",
                "published_offset_mins": 90,
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.95,
                "cat": "water-contamination",
                "dept": "water-works",
                "urgency": "EMERGENCY",
                "urgency_reasoning": "Contaminated drinking water with reported child illness indicators.",
                "ward_num": 4,
                "raw_loc": "Bhaktinagar",
                "confidence": 0.88,
                "theme": "Water Contamination",
                "reviewed": False,
            },
            {
                "text": "Good work by RMC team! The streetlight near Kotecha Chowk circle was repaired within 2 hours of complaint. Appreciate prompt response.",
                "lang": "en",
                "source": "WHATSAPP",
                "ext_id": "wa-synth-004",
                "published_offset_mins": 130,
                "sentiment": "POSITIVE",
                "sentiment_score": +0.89,
                "cat": "streetlight-off",
                "dept": "traffic-streetlighting",
                "urgency": "LOW",
                "urgency_reasoning": "Appreciative citizen feedback; resolution confirmed.",
                "ward_num": 7,
                "raw_loc": "Kotecha Chowk Circle",
                "confidence": 0.96,
                "theme": "Streetlight Repair",
                "reviewed": True,
            },
            {
                "text": "Nana Mava road par kachra peti bharaai gayi che ane kutra kachro raste par ghasiti rahya che. Swachhata mate van moklo.",
                "lang": "gu",
                "source": "FILE_IMPORT",
                "ext_id": "csv-synth-005",
                "published_offset_mins": 190,
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.65,
                "cat": "garbage-overflow",
                "dept": "solid-waste",
                "urgency": "MEDIUM",
                "urgency_reasoning": "Sanitation spillover; non-emergency municipal hygiene concern.",
                "ward_num": 9,
                "raw_loc": "Nana Mava Road",
                "confidence": 0.89,
                "theme": "Garbage Bin Overflow",
                "reviewed": False,
            },
            {
                "text": "Trikon Baug bus stop pase raste bhatakta dhor (cows/bulls) no trass bau vadhigayo che, traffic jam thai che everyday.",
                "lang": "gu",
                "source": "WHATSAPP",
                "ext_id": "wa-synth-006",
                "published_offset_mins": 250,
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.72,
                "cat": "stray-cattle",
                "dept": "traffic-streetlighting",
                "urgency": "MEDIUM",
                "urgency_reasoning": "Traffic disruption on major transit junction.",
                "ward_num": 5,
                "raw_loc": "Trikon Baug Bus Stop",
                "confidence": 0.84,
                "theme": "Stray Cattle & Traffic",
                "reviewed": False,
            },
            # --- Additional Resource-wise Tracking Seeds ---
            # 1. Social Media: Facebook
            {
                "text": "Facebook Page Complaint: Cleanliness drive in Mavdi Ward 10 was really appreciated by local residents. Keep it up RMC!",
                "lang": "en",
                "source": "FACEBOOK",
                "ext_id": "fb-synth-007",
                "published_offset_mins": 400,
                "sentiment": "POSITIVE",
                "sentiment_score": +0.85,
                "cat": "garbage-overflow",
                "dept": "solid-waste",
                "urgency": "LOW",
                "urgency_reasoning": "Appreciative civic feedback on cleanliness drive.",
                "ward_num": 10,
                "raw_loc": "Mavdi Chowkadi",
                "confidence": 0.92,
                "theme": "Cleanliness Appreciation",
                "reviewed": True,
            },
            {
                "text": "ફેસબુક પર ફરિયાદ: 150 ફીટ રિંગ રોડ પુનિત નગર પાસે ગટર લાઈન ડેમેજ થઈ ગઈ છે, ગંદુ પાણી ભરાયેલું રહે છે. તાત્કાલિક રીપેર કરો.",
                "lang": "gu",
                "source": "FACEBOOK",
                "ext_id": "fb-synth-008",
                "published_offset_mins": 1440 * 3,  # 3 days ago
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.80,
                "cat": "manhole-overflow",
                "dept": "drainage-sewerage",
                "urgency": "HIGH",
                "urgency_reasoning": "Damaged sewer line causing persistent dirty water stagnant.",
                "ward_num": 10,
                "raw_loc": "Puneet Nagar",
                "confidence": 0.90,
                "theme": "Damaged Sewer Line",
                "reviewed": False,
            },
            # 2. Social Media: Twitter (X)
            {
                "text": "@myrmc_rajkot Heavy traffic jam near Indira Circle due to open potholes on the main junction. Commuters facing tough time.",
                "lang": "en",
                "source": "TWITTER_X",
                "ext_id": "tw-synth-009",
                "published_offset_mins": 1440 * 5,  # 5 days ago
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.75,
                "cat": "potholes",
                "dept": "engineering-roads",
                "urgency": "HIGH",
                "urgency_reasoning": "Heavy traffic jam hazard caused by road potholes.",
                "ward_num": 8,
                "raw_loc": "Indira Circle",
                "confidence": 0.91,
                "theme": "Junction Potholes",
                "reviewed": False,
            },
            {
                "text": "Twitter citizen mention: Streetlights are functioning well on University Road now, good initiative @myrmc_rajkot.",
                "lang": "en",
                "source": "TWITTER_X",
                "ext_id": "tw-synth-010",
                "published_offset_mins": 1440 * 18,  # 18 days ago (last month)
                "sentiment": "POSITIVE",
                "sentiment_score": +0.78,
                "cat": "streetlight-off",
                "dept": "traffic-streetlighting",
                "urgency": "LOW",
                "urgency_reasoning": "Positive tweet confirming streetlight functioning.",
                "ward_num": 8,
                "raw_loc": "Saurashtra University",
                "confidence": 0.95,
                "theme": "Streetlight Functionality",
                "reviewed": True,
            },
            # 3. Via Email: Gmail
            {
                "text": "[Official Email Grievance] Subject: Mosquito menace and dengue cases rising near Gandhigram Sheetla Mataji Temple. Need urgent fogging.",
                "lang": "en",
                "source": "EMAIL",
                "ext_id": "email-synth-011",
                "published_offset_mins": 1440 * 2,  # 2 days ago
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.85,
                "cat": "mosquito-fogging",
                "dept": "health-sanitation",
                "urgency": "EMERGENCY",
                "urgency_reasoning": "Health hazard with reported dengue cases requiring vector control fogging.",
                "ward_num": 1,
                "raw_loc": "Gandhigram Police Station",
                "confidence": 0.89,
                "theme": "Mosquito Fogging Request",
                "reviewed": False,
            },
            {
                "text": "Email to Commissioner: Inquiry regarding pipeline connection in Kalawad road Cosmoplex area. Please provide update on the timeline.",
                "lang": "en",
                "source": "EMAIL",
                "ext_id": "email-synth-012",
                "published_offset_mins": 1440 * 20,  # 20 days ago
                "sentiment": "NEUTRAL",
                "sentiment_score": 0.0,
                "cat": "pipeline-leak",
                "dept": "water-works",
                "urgency": "LOW",
                "urgency_reasoning": "Informational inquiry regarding connection timeline.",
                "ward_num": 11,
                "raw_loc": "Cosmoplex",
                "confidence": 0.82,
                "theme": "Water Pipeline Inquiry",
                "reviewed": True,
            },
            {
                "text": "Email from citizen: Highly satisfied with the prompt cleaning of community garbage container near Raiya Telephone Exchange.",
                "lang": "en",
                "source": "EMAIL",
                "ext_id": "email-synth-013",
                "published_offset_mins": 1440 * 45,  # 45 days ago (Sep 2026)
                "sentiment": "POSITIVE",
                "sentiment_score": +0.92,
                "cat": "garbage-overflow",
                "dept": "solid-waste",
                "urgency": "LOW",
                "urgency_reasoning": "Citizen appreciation email.",
                "ward_num": 9,
                "raw_loc": "Raiya Telephone Exchange",
                "confidence": 0.94,
                "theme": "Garbage Cleaning Appreciation",
                "reviewed": True,
            },
            # 4. Official Website: RMC Portal
            {
                "text": "RMC Portal Complaint #44021: Broken paver blocks on footpath near Kankot Road creating difficulty for elderly pedestrians.",
                "lang": "en",
                "source": "RMC_PORTAL",
                "ext_id": "rmc-cp-synth-014",
                "published_offset_mins": 1440 * 4,  # 4 days ago
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.68,
                "cat": "footpath",
                "dept": "engineering-roads",
                "urgency": "MEDIUM",
                "urgency_reasoning": "Footpath obstruction and paver block damage.",
                "ward_num": 12,
                "raw_loc": "Kankot",
                "confidence": 0.88,
                "theme": "Footpath Paver Block Damage",
                "reviewed": False,
            },
            {
                "text": "RMC Portal Complaint #39810: Drinking water pressure is extremely low during morning supply in Sant Kabir Road area.",
                "lang": "en",
                "source": "RMC_PORTAL",
                "ext_id": "rmc-cp-synth-015",
                "published_offset_mins": 1440 * 40,  # 40 days ago (Sep 2026)
                "sentiment": "NEGATIVE",
                "sentiment_score": -0.74,
                "cat": "pipeline-leak",
                "dept": "water-works",
                "urgency": "MEDIUM",
                "urgency_reasoning": "Low drinking water pressure in residential area.",
                "ward_num": 15,
                "raw_loc": "Sant Kabir Road",
                "confidence": 0.87,
                "theme": "Low Water Pressure",
                "reviewed": False,
            },
            {
                "text": "RMC Portal Feedback #35102: Water quality test report received promptly as requested through online portal. Thank you.",
                "lang": "en",
                "source": "RMC_PORTAL",
                "ext_id": "rmc-cp-synth-016",
                "published_offset_mins": 1440 * 75,  # 75 days ago (Aug 2026)
                "sentiment": "POSITIVE",
                "sentiment_score": +0.86,
                "cat": "water-contamination",
                "dept": "water-works",
                "urgency": "LOW",
                "urgency_reasoning": "Positive resolution acknowledgment on official portal.",
                "ward_num": 3,
                "raw_loc": "Danapith",
                "confidence": 0.93,
                "theme": "Water Report Acknowledgment",
                "reviewed": True,
            },
        ]

        feedback_created = 0
        sample_evidence_uuids = []
        now = timezone.now()

        for s in feedback_seeds:
            # Generate deterministic SHA-256 content hash
            content_hash = hashlib.sha256(s["text"].strip().lower().encode('utf-8')).hexdigest()
            pub_time = now - timedelta(minutes=s["published_offset_mins"])

            item, created = FeedbackItem.objects.get_or_create(
                content_hash=content_hash,
                defaults={
                    "data_source": source_map[s["source"]],
                    "import_run": import_run if s["source"] == "FILE_IMPORT" else None,
                    "external_id": s["ext_id"],
                    "raw_text": s["text"],
                    "detected_language": s["lang"],
                    "published_at": pub_time,
                    "raw_metadata": {"channel": s["source"], "anonymized_sender_hash": hashlib.sha256(s["ext_id"].encode()).hexdigest()[:16]},
                    "is_synthetic": True,
                    "status": "REVIEWED" if s["reviewed"] else "ANALYZED",
                }
            )
            sample_evidence_uuids.append(str(item.id))

            analysis, _ = FeedbackAnalysis.objects.get_or_create(
                feedback_item=item,
                defaults={
                    "model_version": "pulse-heuristic-v1.0",
                    "is_civic_related": True,
                    "sentiment": s["sentiment"],
                    "sentiment_score": s["sentiment_score"],
                    "category": cat_map.get(s["cat"]),
                    "suggested_department": dept_map.get(s["dept"]),
                    "urgency": s["urgency"],
                    "urgency_reasoning": s["urgency_reasoning"],
                    "extracted_location": ward_map.get(s["ward_num"]),
                    "raw_location_string": s["raw_loc"],
                    "recurring_theme": s["theme"],
                    "short_summary": s["text"][:100],
                    "confidence_score": s["confidence"],
                    "requires_human_review": not s["reviewed"] and s["urgency"] == "EMERGENCY",
                    "is_active_version": True,
                }
            )

            if s["reviewed"]:
                AnalysisReview.objects.get_or_create(
                    analysis=analysis,
                    defaults={
                        "reviewed_by": user_map["commissioner"],
                        "previous_category": cat_map.get(s["cat"]),
                        "corrected_category": cat_map.get(s["cat"]),
                        "previous_department": dept_map.get(s["dept"]),
                        "corrected_department": dept_map.get(s["dept"]),
                        "previous_urgency": s["urgency"],
                        "corrected_urgency": s["urgency"],
                        "review_notes": "Verified by RMC Municipal Flying Squad. Work order dispatched.",
                    }
                )
            feedback_created += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {feedback_created} synthetic FeedbackItems, Analyses, and Review entries."))

        # 8. Trend Alert
        alert, _ = TrendAlert.objects.get_or_create(
            alert_title="340% Surge in Drainage & Manhole Overflows",
            defaults={
                "department": dept_map["drainage-sewerage"],
                "category": cat_map["manhole-overflow"],
                "location": ward_map[2],
                "time_window_start": now - timedelta(hours=18),
                "time_window_end": now,
                "baseline_volume": 12.0,
                "current_volume": 41,
                "spike_ratio": 3.42,
                "severity": "CRITICAL",
                "sample_evidence_ids": sample_evidence_uuids[:2],
                "is_acknowledged": False,
            }
        )
        self.stdout.write(self.style.SUCCESS("  Created statistical TrendAlert (340% drainage spike in Ward 2)."))

        # 9. Staff Notification Preferences & Logs
        pref, _ = StaffNotificationPreference.objects.get_or_create(
            staff_user=user_map["commissioner"],
            defaults={
                "email_enabled": True,
                "daily_digest": True,
                "notify_critical_trends": True,
                "notify_emergency_urgency": True,
            }
        )
        NotificationDeliveryLog.objects.get_or_create(
            recipient=user_map["commissioner"],
            alert=alert,
            subject="[PULSE CRITICAL ALERT] 340% Surge in Drainage Overflows in Ward 2",
            defaults={
                "status": "SENT",
                "retry_count": 0,
                "sent_at": now - timedelta(hours=2),
            }
        )

        # 10. Audit Log
        AuditLog.objects.get_or_create(
            action="DATABASE_SEED",
            target_model="FeedbackItem",
            target_id="ALL",
            defaults={
                "user": user_map["commissioner"],
                "details": {"action": "Synthetic demo database seed completed", "total_records": feedback_created},
                "ip_address": "127.0.0.1",
            }
        )
        self.stdout.write(self.style.SUCCESS("  AuditLog entry logged."))
        self.stdout.write(self.style.SUCCESS("RMC PULSE Database Seed completed successfully!"))
