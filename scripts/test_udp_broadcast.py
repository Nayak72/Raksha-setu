"""
Test script — sends BOTH a UDP broadcast and an FCM Push Notification
to verify the Android app receives it in all states (open, background, or closed).

Usage:
    python test_udp_broadcast.py
"""

import json
import socket
import uuid
import os
from datetime import datetime, timezone

# Optional: Firebase Admin for FCM testing
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

# 1. Prepare Alert Payload
payload = {
    "type": "ALERT",
    "alert_id": str(uuid.uuid4()),
    "zone": "Z3",
    "severity": "CRITICAL",
    "message": "⚠️ TEST: Alert received via FCM! (App was closed/background)",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "server_ip": get_local_ip(),
}

# 2. Send via UDP (for LAN/Offline testing)
message = json.dumps(payload).encode("utf-8")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
try:
    sock.sendto(message, ("255.255.255.255", 5005))
    print(f"✅ UDP broadcast sent to 255.255.255.255:5005")
except Exception as e:
    print(f"❌ UDP broadcast failed: {e}")
finally:
    sock.close()

# 3. Send via FCM (for testing closed-app wake-up)
if FCM_AVAILABLE:
    cred_path = "serviceAccountKey.json"
    if os.path.exists(cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        
        fcm_payload = {k: str(v) for k, v in payload.items()}
        fcm_message = messaging.Message(
            data=fcm_payload,
            topic='alerts'
        )
        try:
            response = messaging.send(fcm_message)
            print(f"✅ FCM Push Notification sent to topic 'alerts'")
            print(f"   FCM Message ID: {response}")
        except Exception as e:
            print(f"❌ FCM send failed: {e}")
    else:
        print("⚠️ Skipping FCM: 'serviceAccountKey.json' not found in this directory.")
else:
    print("⚠️ Skipping FCM: 'firebase-admin' library not installed.")

print(f"\n--- Alert Details ---")
print(f"ID:       {payload['alert_id']}")
print(f"Message:  {payload['message']}")
print(f"Severity: {payload['severity']}")
print(f"----------------------")

