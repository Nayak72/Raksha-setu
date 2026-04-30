"""
FCM Sender - sends push notifications to Android devices when the app is closed.
Requires a google-services.json or Firebase Admin SDK credentials.
"""
import structlog
import firebase_admin
from firebase_admin import credentials, messaging
import os

logger = structlog.get_logger(__name__)

# Initialize Firebase Admin if credentials exist
try:
    if not firebase_admin._apps:
        # Check if the path to serviceAccountKey.json is provided via env var
        # or use a default path if available.
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("firebase_admin.initialized")
        else:
            logger.warning("firebase_admin.credentials_not_found", path=cred_path, msg="FCM will not send. Add serviceAccountKey.json for Firebase Admin SDK.")
except Exception as e:
    logger.error("firebase_admin.initialization_failed", error=str(e))

async def send_fcm_alert_async(payload: dict) -> bool:
    """
    Send an FCM data message to a topic (e.g., 'alerts').
    This wakes up the app even if it is completely closed.
    """
    if not firebase_admin._apps:
        logger.warning("fcm_sender.skipped_not_initialized")
        return False
        
    try:
        # We send a data message instead of a notification message 
        # so the app can process it in the background/closed state via FcmListenerService
        message = messaging.Message(
            data={k: str(v) for k, v in payload.items()},
            topic='alerts'
        )
        response = messaging.send(message)
        logger.info("fcm_sender.success", response=response)
        return True
    except Exception as e:
        logger.error("fcm_sender.failed", error=str(e))
        return False
