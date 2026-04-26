# 🦙 & 📡 RakshaSetu: Ollama & MQTT Setup Guide

This guide provides step-by-step instructions on how to install, configure, test, and connect the two most critical external dependencies of RakshaSetu: **Ollama** (for Local LLM inference) and **MQTT** (for Real-time Emergency Broadcasting).

---

## Part 1: Setting up Ollama (Local LLM)

Ollama is the engine that powers our AI Agents (Zone Analyst, Supervisor, etc.) locally on your machine, guaranteeing absolute privacy and offline capability.

### 1. Installation
1. Go to the official website: [https://ollama.com/download](https://ollama.com/download)
2. Download the installer for **Windows**.
3. Run the installer and complete the setup. Ollama will automatically start running in the background.

### 2. Downloading the Model
RakshaSetu is configured to use `qwen2.5:7b` by default because it is fast and highly capable for reasoning tasks. 
Open your terminal (PowerShell) and run:
```powershell
ollama pull qwen2.5:7b
```
*(Note: This is a ~4GB download. If your machine has low RAM, you can use `llama3.2:1b` or `qwen2.5:3b` instead).*

### 3. Testing Ollama Independently
Verify that Ollama is running and responding to API requests on its default port (`11434`):
```powershell
Invoke-RestMethod -Uri http://localhost:11434/api/generate `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"model": "qwen2.5:7b", "prompt": "Say exactly: SYSTEM_READY", "stream": false}'
```
You should receive a JSON response containing the text `SYSTEM_READY`.

### 4. Connecting Ollama to RakshaSetu
In the root directory of your project, open the `.env` file and ensure the following variables are set:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```
*If you downloaded a different model in step 2, make sure to change `OLLAMA_MODEL` to match exactly.*

---

## Part 2: Setting up MQTT (Real-time Broadcasting)

MQTT is used to push emergency alerts instantly. We are currently utilizing a public testing broker (`test.mosquitto.org`), so no local installation is strictly required. However, the connection must be exact.

### 1. Understanding the Dual-Protocol Setup
MQTT in RakshaSetu uses two different protocols to communicate:
*   **The Backend (Python)** connects via raw **TCP** on port `1883`. It acts as the *Publisher* (sending the alerts).
*   **The Frontend (React)** connects via **WebSockets (ws://)** on port `8080`. Browsers cannot speak raw TCP, so they must use WebSockets to act as the *Subscriber* (receiving the alerts).

### 2. Connecting MQTT to RakshaSetu
You must configure both the backend and frontend environment files.

**For the Backend:**
Open the `.env` file in the root directory and ensure it points to the raw TCP port:
```env
MQTT_BROKER_HOST=test.mosquitto.org
MQTT_BROKER_PORT=1883
```

**For the Frontend:**
Open the `frontend/.env` file and ensure it points to the WebSocket URL:
```env
VITE_MQTT_WS_URL=ws://test.mosquitto.org:8080/mqtt
```

### 3. Testing the MQTT Connection
You can test if the MQTT broadcasting is working without touching the code.

**Step A: Listen for Alerts (Subscriber)**
1. Open a browser and go to a free online MQTT client tool, like the **HiveMQ Web Client** (http://www.hivemq.com/demos/websocket-client/).
2. Click **Connect** (leave the default public broker settings if it points to a public broker, or change the Host to `test.mosquitto.org` and Port to `8080`).
3. Under **Subscriptions**, click **Add New Topic Subscription**.
4. Enter the topic: `rakshasetu/alerts/#` (The `#` is a wildcard, meaning it will listen to all alerts for all zones).

**Step B: Send an Alert (Publisher)**
With your RakshaSetu backend running (`uvicorn app.main:app`), use Postman or PowerShell to trigger a detection event:
```powershell
Invoke-RestMethod -Uri http://localhost:8001/api/v1/detect `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"zone_id": "cc0a2353-6648-406d-a8e2-32e792bb5de0", "count": 90, "metadata": {"source": "test"}}'
```
*Wait ~10 seconds for the AI agents to process the data.* 

**The Result:**
Once the **Notifier Agent** finishes drafting the alert, it will publish it. You will instantly see the JSON alert message appear in the HiveMQ Web Client, and if your React frontend is running, the red "Emergency Broadcast" banner will slide down at the top of the screen!
