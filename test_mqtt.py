import time
import paho.mqtt.client as paho_mqtt

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"Connected with result code {reason_code}")

client = paho_mqtt.Client(client_id="raksha-test-1234", callback_api_version=paho_mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect

print("Connecting to broker.hivemq.com...")
client.connect("broker.hivemq.com", 1883, 60)
client.loop_start()

for _ in range(10):
    time.sleep(1)

client.loop_stop()
print("Done")
