import json
import os
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import DataSource, ConnectorConfig
from .connectors.whatsapp import WhatsAppCloudApiConnector
from .connectors.file_import import FileImportConnector
from .connectors.scaffolding import TwitterXConnector, MetaSocialConnector
from .connectors.email import EmailConnector
from .services import ingest_citizen_complaint

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    """
    Official Webhook Endpoint for Meta WhatsApp Business Cloud API.
    GET: Verification handshake
    POST: Ingestion of incoming citizen messages with HMAC-SHA256 signature security.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        connector = WhatsAppCloudApiConnector()
        expected_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "rmc_secure_verify_token_2026")

        verified, challenge_val = connector.verify_webhook_token(mode, token, challenge, expected_token)
        if verified:
            return HttpResponse(challenge_val, status=200, content_type="text/plain")
        return HttpResponse("Verification failed", status=403)

    def post(self, request):
        app_secret = os.environ.get("WHATSAPP_APP_SECRET", "rmc_demo_secret")
        signature = request.headers.get("X-Hub-Signature-256", "")

        connector = WhatsAppCloudApiConnector()

        if app_secret and app_secret != "rmc_demo_secret" and not connector.verify_signature(request.body, signature, app_secret):
            return Response({"error": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return Response({"error": "Malformed JSON payload"}, status=status.HTTP_400_BAD_REQUEST)

        data_source = DataSource.objects.filter(source_type="WHATSAPP").first()
        if not data_source:
            data_source = DataSource.objects.create(
                name="WhatsApp Business Cloud API",
                source_type="WHATSAPP",
                health_status="HEALTHY"
            )

        items = connector.handle_incoming_webhook(payload, data_source)
        return Response({
            "status": "success",
            "ingested_count": len(items)
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class TwitterWebhookView(APIView):
    """
    Endpoint for incoming Twitter (X) mentions / complaint tweets.
    Automatically assigns Source: Social Media -> Twitter (X).
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else request.POST.dict()
        except Exception:
            data = request.POST.dict()

        text = data.get("text") or data.get("tweet") or data.get("raw_text", "")
        if not text:
            return Response({"error": "Missing complaint text"}, status=status.HTTP_400_BAD_REQUEST)

        tweet_id = data.get("id") or data.get("tweet_id")
        item, analysis = ingest_citizen_complaint(
            raw_text=text,
            source_hint="twitter",
            external_id=str(tweet_id) if tweet_id else None,
            metadata={"platform": "Twitter (X)"}
        )
        return Response({
            "status": "success",
            "complaint_id": str(item.id),
            "source_type": item.source_type,
            "source_platform": item.source_platform,
            "sentiment": analysis.sentiment if analysis else None,
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class FacebookWebhookView(APIView):
    """
    Endpoint for incoming Meta / Facebook page posts and comments.
    Automatically assigns Source: Social Media -> Facebook.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else request.POST.dict()
        except Exception:
            data = request.POST.dict()

        message = data.get("message") or data.get("post_text") or data.get("raw_text", "")
        if not message:
            return Response({"error": "Missing complaint text"}, status=status.HTTP_400_BAD_REQUEST)

        post_id = data.get("post_id") or data.get("id")
        item, analysis = ingest_citizen_complaint(
            raw_text=message,
            source_hint="facebook",
            external_id=str(post_id) if post_id else None,
            metadata={"platform": "Facebook"}
        )
        return Response({
            "status": "success",
            "complaint_id": str(item.id),
            "source_type": item.source_type,
            "source_platform": item.source_platform,
            "sentiment": analysis.sentiment if analysis else None,
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class EmailIngestionView(APIView):
    """
    Endpoint for incoming citizen emails from authorized municipal Gmail / inbox.
    Automatically assigns Source: Via Email -> Gmail.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else request.POST.dict()
        except Exception:
            data = request.POST.dict()

        body = data.get("body") or data.get("text") or data.get("message") or data.get("raw_text", "")
        subject = data.get("subject", "")
        full_text = f"[{subject}] {body}".strip() if subject and subject not in body else body.strip()

        if not full_text:
            return Response({"error": "Missing email content"}, status=status.HTTP_400_BAD_REQUEST)

        msg_id = data.get("message_id") or data.get("id")
        item, analysis = ingest_citizen_complaint(
            raw_text=full_text,
            source_hint="email",
            external_id=str(msg_id) if msg_id else None,
            metadata={"subject": subject, "platform": "Gmail"}
        )
        return Response({
            "status": "success",
            "complaint_id": str(item.id),
            "source_type": item.source_type,
            "source_platform": item.source_platform,
            "sentiment": analysis.sentiment if analysis else None,
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class OfficialWebsiteSubmitView(APIView):
    """
    Endpoint for RMC official website complaint portal submissions.
    Automatically assigns Source: Official Website -> RMC Portal.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else request.POST.dict()
        except Exception:
            data = request.POST.dict()

        text = data.get("complaint_text") or data.get("description") or data.get("raw_text", "")
        if not text:
            return Response({"error": "Missing complaint text"}, status=status.HTTP_400_BAD_REQUEST)

        cno = data.get("complaint_no") or data.get("reference_number")
        item, analysis = ingest_citizen_complaint(
            raw_text=text,
            source_hint="rmc_portal",
            external_id=str(cno) if cno else None,
            metadata={"platform": "RMC Portal", "ward": data.get("ward"), "zone": data.get("zone")}
        )
        return Response({
            "status": "success",
            "complaint_id": str(item.id),
            "source_type": item.source_type,
            "source_platform": item.source_platform,
            "sentiment": analysis.sentiment if analysis else None,
        }, status=status.HTTP_201_CREATED)
