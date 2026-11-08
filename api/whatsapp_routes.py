import logging
from fastapi import APIRouter, Request, Response, HTTPException, status
from services.whatsapp.webhook_handler import webhook_handler
from core.security import verify_whatsapp_signature
from config.settings import settings

logger = logging.getLogger(__name__)
whatsapp_router = APIRouter(prefix="/webhook", tags=["WhatsApp"])

@whatsapp_router.get("")
async def verify_webhook(request: Request):
    """
    WhatsApp Cloud API Webhook Verification.
    Meta sends a GET request to verify the webhook endpoint.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp Webhook verified successfully!")
            return Response(content=str(challenge), media_type="text/plain")
        else:
            logger.warning("Verification token mismatch: received %s, expected %s", token, settings.WHATSAPP_VERIFY_TOKEN)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")
    
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing verification parameters")

@whatsapp_router.post("")
async def receive_webhook(request: Request):
    """
    WhatsApp Cloud API Incoming Event Ingestion.
    Meta sends POST requests for messages, statuses, and delivery receipts.
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # Secure HMAC signature verification
    if not verify_whatsapp_signature(raw_body, signature):
        logger.warning("Invalid X-Hub-Signature-256 received.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = await request.json()
        # Process message in background / pipeline
        await webhook_handler.process_incoming_payload(payload)
    except Exception as e:
        logger.error("Error handling webhook payload: %s", e)

    # WhatsApp API requires quick 200 OK response
    return {"status": "EVENT_RECEIVED"}
