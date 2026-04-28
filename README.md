<<<<<<< HEAD
# 🛡️ RakshaSetu: AI-Driven Disaster Response System

RakshaSetu is an advanced, real-time disaster management and emergency response platform. It leverages a state-of-the-art event-driven architecture, combining a multi-agent AI workflow (LangGraph + Local LLMs), real-time database triggers (Supabase), and live MQTT broadcasting to orchestrate complex disaster response scenarios.

---

## 🏗️ System Architecture & Layers

The project is structured into four highly decoupled, scalable layers:

### 1. 🖥️ Frontend Layer (React + Vite + TailwindCSS)
The frontend serves as the live command center for emergency operators.
* **Live Map Visualization**: Uses `Leaflet` to plot critical zones, risk radii, shelters, and volunteer locations dynamically.
* **Event-Driven UI**: Built with `Supabase Realtime`, allowing metrics, logs, and alerts to update instantly without HTTP polling.
* **Agent Transparency Panel**: The `AgentLogsPanel` renders the live stream of thought, reasoning steps, and confidence scores from the AI agents as they process live disasters.
* **MQTT WebSocket Client**: A built-in MQTT client connects to public or local brokers (e.g., `ws://test.mosquitto.org:8080/mqtt`) to visualize broadcasted emergency alerts.

### 2. ⚙️ Backend Layer (FastAPI)
A high-performance, fully async Python backend designed for non-blocking event processing.
* **REST API**: Provides core endpoints (`/api/v1/detect`, `/api/v1/simulate-weather`) to ingest sensor data and trigger the AI pipeline.
* **Background Tasks & Event Listeners**: Instead of blocking HTTP responses, incoming events are passed to FastAPI `BackgroundTasks` (or Postgres `NOTIFY` listeners) which asynchronously trigger the AI agent workflows.
* **Structured Logging**: Uses `structlog` to provide machine-readable JSON logs for tracking system health and agent invocation.

### 3. 🧠 AI Agents Layer (LangGraph + Ollama + RAG)
The brain of RakshaSetu. Instead of a single LLM call, the system utilizes a **Directed Acyclic Graph (DAG)** of specialized AI agents.
* **Local LLM**: Powered entirely by local models via **Ollama** (e.g., `qwen2.5:7b`), ensuring absolute data privacy and zero API latency during critical outages.
* **The Agent Workflow**:
  1. **Vision / Detection Agent**: Uses Computer Vision (YOLO) to extract structured metrics (crowd density, flood levels, structural damage) from drone/satellite imagery.
  2. **Triage Agent**: Assesses the immediate severity of the extracted detection data.
  3. **Weather Agent**: Evaluates stochastic weather simulations (rainfall, wind) affecting the disaster zone.
  4. **Zone Analyst Agent**: Fuses weather and detection data. It queries the **RAG Memory** for historical context to predict escalation.
  5. **Resource Allocator**: Calculates the optimal dispatch of nearby volunteers and available shelter beds.
  6. **Notifier Agent**: Drafts concise, actionable alert messages for the public and rescue teams.
  7. **Supervisor Agent**: The final oversight node. It reviews all agent outputs, resolves data conflicts (e.g., fire detected but pouring rain), and commits the final decision.

### 4. 🗄️ Database & Storage Layer
* **Relational DB (Supabase / PostgreSQL)**: Stores the state of Zones, Shelters, Volunteers, and Alerts. Uses Row Level Security (RLS) and Realtime Publications.
* **Vector Database (ChromaDB)**: A local **Retrieval-Augmented Generation (RAG)** store using `sentence-transformers`. It maintains separate semantic collections (`weather_history`, `detection_history`) so agents can recall how similar past disasters were handled.
* **Object Storage**: Supabase Buckets are utilized to store raw drone/aerial images for the Vision pipeline.

---

## 🚀 Setup & Installation Guide (Windows)

### Prerequisites
* **Python 3.11+**
* **Node.js 18+**
* **Ollama** (Running locally with a model like `qwen2.5:7b` pulled)
* **Supabase Account** (For managed PostgreSQL)

### 1. Backend Setup
Clone the repository and set up the Python environment:
```powershell
# Create and activate virtual environment
python -m venv .venv_win
.\.venv_win\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download required spaCy NLP model
python -m spacy download en_core_web_sm
```

### 2. Environment Variables
Create a `.env` file in the root directory (use `.env.example` as a template):
```env
# ── Supabase ──
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_DB_HOST=aws-0-region.pooler.supabase.com
SUPABASE_DB_PORT=6543
SUPABASE_DB_USER=postgres.your-project-id
SUPABASE_DB_PASSWORD=your-db-password
SUPABASE_DB_NAME=postgres

# ── Local LLM ──
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# ── MQTT Broker ──
MQTT_BROKER_HOST=test.mosquitto.org
MQTT_BROKER_PORT=1883
```

### 3. Database Migrations
Go to your **Supabase Dashboard -> SQL Editor** and execute the SQL scripts found in the `migrations/` folder in order:
* `001_initial.sql` (Creates core tables, RLS policies, and triggers)
* `002_agent_logs.sql` (Creates the tracking table for AI reasoning steps)

### 4. Frontend Setup
Open a new terminal and prepare the React frontend:
```powershell
cd frontend
npm install

# Optional: verify frontend environment variables in frontend/.env
# VITE_API_BASE=http://localhost:8001
# VITE_MQTT_WS_URL=ws://test.mosquitto.org:8080/mqtt
```

---

## 🏃‍♂️ Running the Project

You need three terminal windows to run the complete stack:

**Terminal 1: Ollama Engine**
Ensure the local LLM is active in the background.
```powershell
ollama run qwen2.5:7b
```

**Terminal 2: FastAPI Backend**
```powershell
.\.venv_win\Scripts\activate
python -m uvicorn app.main:app --port 8001 --reload
```

**Terminal 3: React Frontend**
```powershell
cd frontend
npm run dev
```

Visit `http://localhost:5173` in your browser. The dashboard will connect to Supabase Realtime and the MQTT WebSocket.

---

## 🧪 Testing the Agent Pipeline

You can simulate a live disaster event to watch the agents process data in real-time. With the backend running, send a POST request (or use a tool like Postman) to the detection endpoint:

```powershell
Invoke-RestMethod -Uri http://localhost:8001/api/v1/detect `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"zone_id": "YOUR_ZONE_UUID", "count": 95, "metadata": {"source": "drone_camera"}}'
```
*Note: Replace `YOUR_ZONE_UUID` with a valid zone ID from your Supabase database.*

Once triggered, watch the **Agent Logs** panel on the frontend UI to see the Triage, Analyst, and Supervisor agents dynamically resolve the emergency!

### Automated Simulation Mode

You can run continuous, stochastic simulations of disaster scenarios (Flood, Fire, Calm) that generate realistic data patterns:
```powershell
python scripts/simulation/automated_simulation.py
```
This script relies on the `synthetic_generator.py` mathematically modeling disaster evolutions and submitting them to the backend API.
