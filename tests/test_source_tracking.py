import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulse_project.settings')
django.setup()
from django.test.utils import setup_test_environment
setup_test_environment()

import uuid
from django.test import Client, TestCase
from django.contrib.auth.models import User
from apps.feedback.models import FeedbackItem
from apps.ingestion.models import DataSource
from apps.intelligence.models import FeedbackAnalysis
from apps.ingestion.services import ingest_citizen_complaint
from ui_prototype.views import compute_source_analytics, complaint_row

def run_source_tracking_tests():
    print("=" * 75)
    print("PULSE — RESOURCE-WISE COMPLAINT SOURCE TRACKING TEST SUITE")
    print("=" * 75)

    client = Client()
    # Authenticate as commissioner
    login_success = client.login(username="commissioner", password="RMCpulse2026!")
    assert login_success, "Commissioner login failed"
    print("\n[TEST 1] Staff Authentication Verified")
    print("  ✓ Commissioner authenticated for Admin Dashboard & Complaint Management Table.")

    # -------------------------------------------------------------------------
    # TEST 2: Social Media Source Tracking (Twitter & Facebook)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Social Media Source Tracking (Twitter & Facebook)")
    
    # 2A: Twitter (X)
    tw_text = f"Twitter test complaint: Severe waterlogging near Mavdi Circle {uuid.uuid4().hex[:6]}"
    tw_item, tw_analysis = ingest_citizen_complaint(
        raw_text=tw_text,
        source_hint="twitter",
        external_id=f"tw-test-{uuid.uuid4().hex[:6]}",
        metadata={"platform": "Twitter (X)"}
    )
    assert tw_item is not None, "Twitter complaint ingestion returned None"
    assert tw_item.source_type == "SOCIAL_MEDIA", f"Expected SOCIAL_MEDIA, got {tw_item.source_type}"
    assert tw_item.source_platform == "TWITTER", f"Expected TWITTER, got {tw_item.source_platform}"
    print(f"  ✓ Twitter (X) complaint auto-detected: Source Type = '{tw_item.get_source_type_display()}', Platform = '{tw_item.get_source_platform_display()}'.")

    # 2B: Facebook
    fb_text = f"Facebook post complaint: Streetlights not functioning on Gondal Road {uuid.uuid4().hex[:6]}"
    fb_item, fb_analysis = ingest_citizen_complaint(
        raw_text=fb_text,
        source_hint="facebook",
        external_id=f"fb-test-{uuid.uuid4().hex[:6]}",
        metadata={"platform": "Facebook"}
    )
    assert fb_item is not None, "Facebook complaint ingestion returned None"
    assert fb_item.source_type == "SOCIAL_MEDIA", f"Expected SOCIAL_MEDIA, got {fb_item.source_type}"
    assert fb_item.source_platform == "FACEBOOK", f"Expected FACEBOOK, got {fb_item.source_platform}"
    print(f"  ✓ Facebook complaint auto-detected: Source Type = '{fb_item.get_source_type_display()}', Platform = '{fb_item.get_source_platform_display()}'.")

    # -------------------------------------------------------------------------
    # TEST 3: Via Email Source Tracking (Gmail / Authorized Incoming Account)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Via Email Source Tracking (Gmail)")
    email_text = f"Email Grievance: Drinking water pipeline leak near Jubilee Garden {uuid.uuid4().hex[:6]}"
    email_item, email_analysis = ingest_citizen_complaint(
        raw_text=email_text,
        source_hint="email",
        external_id=f"email-test-{uuid.uuid4().hex[:6]}",
        metadata={"subject": "Pipeline Leakage", "platform": "Gmail"}
    )
    assert email_item is not None, "Email complaint ingestion returned None"
    assert email_item.source_type == "EMAIL", f"Expected EMAIL, got {email_item.source_type}"
    assert email_item.source_platform == "GMAIL", f"Expected GMAIL, got {email_item.source_platform}"
    print(f"  ✓ Email complaint auto-detected: Source Type = '{email_item.get_source_type_display()}', Platform = '{email_item.get_source_platform_display()}'.")

    # -------------------------------------------------------------------------
    # TEST 4: Official Website Source Tracking (RMC Complaint Portal)
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Official Website Source Tracking (RMC Portal)")
    portal_text = f"RMC Portal Form: Garbage container overflowing near Race Course {uuid.uuid4().hex[:6]}"
    portal_item, portal_analysis = ingest_citizen_complaint(
        raw_text=portal_text,
        source_hint="rmc_portal",
        external_id=f"rmc-test-{uuid.uuid4().hex[:6]}",
        metadata={"platform": "RMC Portal"}
    )
    assert portal_item is not None, "Portal complaint ingestion returned None"
    assert portal_item.source_type == "OFFICIAL_WEBSITE", f"Expected OFFICIAL_WEBSITE, got {portal_item.source_type}"
    assert portal_item.source_platform == "RMC_PORTAL", f"Expected RMC_PORTAL, got {portal_item.source_platform}"
    print(f"  ✓ Official Website complaint auto-detected: Source Type = '{portal_item.get_source_type_display()}', Platform = '{portal_item.get_source_platform_display()}'.")

    # -------------------------------------------------------------------------
    # TEST 5: Automatic Source Detection (Zero Citizen Manual Selection)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Automatic Source Detection Guarantee")
    # Verify model level auto-detection when creating directly without source_type
    ds_email = DataSource.objects.filter(source_type="EMAIL").first()
    auto_item = FeedbackItem(
        data_source=ds_email,
        external_id=f"email-auto-{uuid.uuid4().hex[:6]}",
        content_hash=uuid.uuid4().hex,
        raw_text="Direct database complaint test without citizen selecting source",
        status="PENDING_ANALYSIS"
    )
    auto_item.save()
    assert auto_item.source_type == "EMAIL", f"Auto-detection failed: {auto_item.source_type}"
    assert auto_item.source_platform == "GMAIL", f"Auto-detection failed: {auto_item.source_platform}"
    print("  ✓ Verified: System automatically identifies original source without asking citizens to select.")

    # -------------------------------------------------------------------------
    # TEST 6: Admin Dashboard Complaint Source Analytics
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Admin Dashboard — Complaint Source Analytics Section")
    dash_res = client.get("/dashboard/")
    assert dash_res.status_code == 200, f"Dashboard returned {dash_res.status_code}"
    html = dash_res.content.decode("utf-8")

    # Verify section title
    assert "Complaint Source Analytics" in html, "Missing 'Complaint Source Analytics' section in dashboard"
    assert "Social Media Complaints" in html, "Missing Social Media indicator"
    assert "Via Email Complaints" in html, "Missing Email indicator"
    assert "Official Website Complaints" in html, "Missing Official Website indicator"
    assert "Twitter vs Facebook Breakdown" in html, "Missing Twitter vs Facebook breakdown"
    assert "Resource-wise Complaint Percentage" in html, "Missing Resource-wise complaint percentage"
    assert "Resource-wise Sentiment Analysis" in html, "Missing Resource-wise sentiment analysis"
    assert "Resource-wise Category Analysis" in html, "Missing Resource-wise category analysis"
    assert "Monthly Source-wise Complaint Trends" in html, "Missing Monthly source-wise trends"

    # Verify context analytics computation
    qs = FeedbackAnalysis.objects.filter(is_active_version=True)
    stats = compute_source_analytics(qs)
    assert stats["total_social"] >= 2, f"Expected at least 2 social complaints, got {stats['total_social']}"
    assert stats["total_email"] >= 1, f"Expected at least 1 email complaint, got {stats['total_email']}"
    assert stats["total_website"] >= 1, f"Expected at least 1 website complaint, got {stats['total_website']}"
    assert stats["social_pct"] > 0, "Social pct should be > 0"
    assert len(stats["sentiments"]) == 3, "Sentiments should have 3 resources"
    assert len(stats["category_analysis"]) == 3, "Categories should have 3 resources"
    assert len(stats["monthly_trends"]) > 0, "Monthly trends should have records"
    print(f"  ✓ Admin Dashboard Section 4 rendered successfully.")
    print(f"    - Total Social Media complaints: {stats['total_social']} ({stats['social_pct']}%)")
    print(f"    - Total Email complaints: {stats['total_email']} ({stats['email_pct']}%)")
    print(f"    - Total Official Website complaints: {stats['total_website']} ({stats['website_pct']}%)")
    print(f"    - Twitter vs Facebook breakdown: Twitter={stats['twitter_count']}, Facebook={stats['facebook_count']}")
    print(f"    - Resource-wise Sentiment Analysis: {len(stats['sentiments'])} source types calculated")
    print(f"    - Resource-wise Category Analysis: {len(stats['category_analysis'])} source types calculated")
    print(f"    - Monthly Trends: {len(stats['monthly_trends'])} monthly periods tracked")

    # -------------------------------------------------------------------------
    # TEST 7: Complaint Management Table & 9 Required Columns
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Complaint Management Table (9 Required Columns)")
    inbox_res = client.get("/feedback/?view=table")
    assert inbox_res.status_code == 200, f"Inbox returned {inbox_res.status_code}"
    table_html = inbox_res.content.decode("utf-8")

    required_columns = [
        "Complaint ID",
        "Complaint Description",
        "Source Type",
        "Source Platform",
        "Category",
        "Sentiment",
        "Location",
        "Complaint Date",
        "Status",
    ]
    for col in required_columns:
        assert col in table_html, f"Missing required column in table: '{col}'"
        print(f"  ✓ Verified Column: '{col}' present in Complaint Management Table")

    # -------------------------------------------------------------------------
    # TEST 8: Complaint Source Filters
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Complaint Management Table Filters")
    # Filter 1: Social Media
    res_social = client.get("/feedback/?source=social&view=table")
    assert res_social.status_code == 200
    for item in res_social.context["items"]:
        assert item["source_type"] == "SOCIAL_MEDIA", f"Filter leaked non-social item: {item['source_type']}"
    print(f"  ✓ Social Media Filter verified ({len(res_social.context['items'])} items returned).")

    # Filter 2: Email
    res_email = client.get("/feedback/?source=email&view=table")
    assert res_email.status_code == 200
    for item in res_email.context["items"]:
        assert item["source_type"] == "EMAIL", f"Filter leaked non-email item: {item['source_type']}"
    print(f"  ✓ Email Filter verified ({len(res_email.context['items'])} items returned).")

    # Filter 3: Official Website
    res_web = client.get("/feedback/?source=website&view=table")
    assert res_web.status_code == 200
    for item in res_web.context["items"]:
        assert item["source_type"] == "OFFICIAL_WEBSITE", f"Filter leaked non-website item: {item['source_type']}"
    print(f"  ✓ Official Website Filter verified ({len(res_web.context['items'])} items returned).")

    # Filter 4: Twitter
    res_tw = client.get("/feedback/?source=twitter&view=table")
    assert res_tw.status_code == 200
    for item in res_tw.context["items"]:
        assert item["source_platform"] == "TWITTER", f"Filter leaked non-twitter item: {item['source_platform']}"
    print(f"  ✓ Twitter Filter verified ({len(res_tw.context['items'])} items returned).")

    # Filter 5: Facebook
    res_fb = client.get("/feedback/?source=facebook&view=table")
    assert res_fb.status_code == 200
    for item in res_fb.context["items"]:
        assert item["source_platform"] == "FACEBOOK", f"Filter leaked non-facebook item: {item['source_platform']}"
    print(f"  ✓ Facebook Filter verified ({len(res_fb.context['items'])} items returned).")

    # -------------------------------------------------------------------------
    # TEST 9: Ingestion HTTP Endpoints (Webhooks / APIs)
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Ingestion HTTP Webhook Endpoints")
    
    # Twitter Webhook
    tw_res = client.post("/api/v1/integrations/twitter/webhook/", {
        "text": f"Tweet endpoint test: Traffic light broken at Kotecha Chowk {uuid.uuid4().hex[:6]}",
        "id": f"tw-ep-{uuid.uuid4().hex[:6]}"
    }, content_type="application/json")
    assert tw_res.status_code == 201, f"Twitter webhook failed: {tw_res.status_code}"
    tw_json = tw_res.json()
    assert tw_json["source_type"] == "SOCIAL_MEDIA" and tw_json["source_platform"] == "TWITTER"
    print("  ✓ Twitter Webhook POST: Returned HTTP 201 with source_type='SOCIAL_MEDIA', source_platform='TWITTER'.")

    # Facebook Webhook
    fb_res = client.post("/api/v1/integrations/facebook/webhook/", {
        "message": f"Facebook endpoint test: Water pipeline burst on Kalawad road {uuid.uuid4().hex[:6]}",
        "post_id": f"fb-ep-{uuid.uuid4().hex[:6]}"
    }, content_type="application/json")
    assert fb_res.status_code == 201, f"Facebook webhook failed: {fb_res.status_code}"
    fb_json = fb_res.json()
    assert fb_json["source_type"] == "SOCIAL_MEDIA" and fb_json["source_platform"] == "FACEBOOK"
    print("  ✓ Facebook Webhook POST: Returned HTTP 201 with source_type='SOCIAL_MEDIA', source_platform='FACEBOOK'.")

    # Email Webhook
    email_res = client.post("/api/v1/integrations/email/incoming/", {
        "subject": "Contaminated Water",
        "body": f"Email endpoint test: Dirty water coming in Ward 7 {uuid.uuid4().hex[:6]}",
        "message_id": f"email-ep-{uuid.uuid4().hex[:6]}"
    }, content_type="application/json")
    assert email_res.status_code == 201, f"Email endpoint failed: {email_res.status_code}"
    email_json = email_res.json()
    assert email_json["source_type"] == "EMAIL" and email_json["source_platform"] == "GMAIL"
    print("  ✓ Email Webhook POST: Returned HTTP 201 with source_type='EMAIL', source_platform='GMAIL'.")

    # Portal Submission Webhook
    portal_res = client.post("/api/v1/integrations/portal/submit/", {
        "complaint_text": f"Portal endpoint test: Manhole overflow in Ward 2 {uuid.uuid4().hex[:6]}",
        "complaint_no": f"rmc-ep-{uuid.uuid4().hex[:6]}"
    }, content_type="application/json")
    assert portal_res.status_code == 201, f"Portal endpoint failed: {portal_res.status_code}"
    portal_json = portal_res.json()
    assert portal_json["source_type"] == "OFFICIAL_WEBSITE" and portal_json["source_platform"] == "RMC_PORTAL"
    print("  ✓ Portal Webhook POST: Returned HTTP 201 with source_type='OFFICIAL_WEBSITE', source_platform='RMC_PORTAL'.")

    print("\n" + "=" * 75)
    print("ALL RESOURCE-WISE COMPLAINT SOURCE TRACKING TESTS PASSED PERFECTLY!")
    print("=" * 75)

if __name__ == "__main__":
    run_source_tracking_tests()
