from django.urls import path
from .views import (
    WhatsAppWebhookView,
    TwitterWebhookView,
    FacebookWebhookView,
    EmailIngestionView,
    OfficialWebsiteSubmitView,
)

urlpatterns = [
    # WhatsApp Webhook
    path('api/v1/integrations/whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
    path('api/whatsapp/webhook', WhatsAppWebhookView.as_view(), name='whatsapp_webhook_direct'),
    path('api/whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook_direct_slash'),

    # Social Media: Twitter (X)
    path('api/v1/integrations/twitter/webhook/', TwitterWebhookView.as_view(), name='twitter_webhook'),
    path('api/twitter/webhook/', TwitterWebhookView.as_view(), name='twitter_webhook_direct'),

    # Social Media: Facebook
    path('api/v1/integrations/facebook/webhook/', FacebookWebhookView.as_view(), name='facebook_webhook'),
    path('api/facebook/webhook/', FacebookWebhookView.as_view(), name='facebook_webhook_direct'),

    # Via Email: Gmail / Authorized incoming email
    path('api/v1/integrations/email/incoming/', EmailIngestionView.as_view(), name='email_incoming'),
    path('api/email/incoming/', EmailIngestionView.as_view(), name='email_incoming_direct'),

    # Official Website: RMC Portal submission
    path('api/v1/integrations/portal/submit/', OfficialWebsiteSubmitView.as_view(), name='portal_submit'),
    path('api/portal/submit/', OfficialWebsiteSubmitView.as_view(), name='portal_submit_direct'),
]
