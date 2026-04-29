import socket
import json
import uuid
import time
from datetime import datetime

# UDP Configuration
UDP_IP = "<broadcast>"
UDP_PORT = 5005

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def send_test_broadcast():
    print(f"Starting Manual UDP Broadcast Test on port {UDP_PORT}...")
    local_ip = get_local_ip()
    
    # Create the payload matching Android app's expectations
    payload = {
        "type": "ALERT",
        "alert_id": str(uuid.uuid4()),
        "zone": "TEST-ZONE-01",
        "severity": "CRITICAL",
        "message": "TEST BROADCAST: This is a manual test message from RakshaSetu CLI.",
        "timestamp": datetime.now().isoformat(),
        "server_ip": local_ip 
    }

    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind((local_ip, 0)) # Bind to correct interface
        
        # Encode and send
        message = json.dumps(payload).encode('utf-8')
        sock.sendto(message, ("255.255.255.255", UDP_PORT))
        
        print(f"Broadcast sent successfully!")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"\nCheck your Android device! It should show a notification if the app is running and connected to the same network.")
        
    except Exception as e:
        print(f"Failed to send broadcast: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    send_test_broadcast()
