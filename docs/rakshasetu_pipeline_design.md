# RakshaSetu: End-to-End Multi-Agent AI Pipeline Design

This document outlines the production-ready system design and implementation plan for the RakshaSetu multi-agent disaster response platform.

## 📦 1. Data Requirements & Dataset Strategy

To build a robust aerial disaster detection model, we require a fusion of multiple domains: human/vehicle detection from aerial views and disaster condition mapping (floods, structural damage, fire). 

### Selected Datasets & Justification

1. **VisDrone (People + Vehicles Aerial)**
   - **Contribution**: Provides high-density annotations of pedestrians, cars, and buses from drone viewpoints.
   - **Why Combine**: Disaster datasets rarely have dense crowd annotations. VisDrone teaches the model to accurately estimate crowd density and vehicle pile-ups, essential for the Triage and Resource Allocation agents.
   - **Limitations**: Only captures "normal" urban scenes, lacking disaster context.

2. **FloodNet (Flood + Infrastructure)**
   - **Contribution**: High-resolution drone imagery of post-hurricane flooding, flooded roads, and damaged buildings.
   - **Why Combine**: Crucial for the Weather and Zone Analyst agents to assess water levels and blocked routes.
   - **Limitations**: Specific to flooding; lacks fire/smoke or dense crowd annotations.

3. **AIDER (Disaster Scenes)**
   - **Contribution**: Aerial images of collapsed buildings, fire, smoke, and traffic accidents.
   - **Why Combine**: Teaches the model to recognize critical hazards (fire/smoke) that require immediate triage.
   - **Limitations**: Smaller dataset size, annotations can be noisy.

4. **C2A Dataset (Disaster + Humans)**
   - **Contribution**: Contextualizes humans within disaster scenarios (e.g., people stranded on roofs).
   - **Why Combine**: Bridges the gap between VisDrone (normal people) and FloodNet/AIDER (empty disasters), teaching the model to identify victims needing rescue.
   - **Limitations**: Often collected from varied altitudes, requiring careful normalization.

### Dataset Merging Pipeline

**Unified YOLO Classes:**
```yaml
0: person
1: vehicle
2: flooded_area
3: fire_smoke
4: damaged_struct
5: safe_struct
```

**Label Remapping Logic:**
All labels will be standardized to YOLO format (class, x_center, y_center, width, height). We will use a script to map original dataset classes to our unified 0-5 IDs. Extraneous classes (e.g., "tricycle" in VisDrone) will be mapped to `vehicle` (1) or ignored.

**Folder Structure (`datasets/rakshasetu_unified/`):**
```
rakshasetu_unified/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
└── data.yaml
```

**Final `data.yaml`:**
```yaml
path: ../datasets/rakshasetu_unified
train: images/train
val: images/val
test: images/test

nc: 6
names: ['person', 'vehicle', 'flooded_area', 'fire_smoke', 'damaged_struct', 'safe_struct']
```

---

## 🏗️ 2. Synthetic Data Generation (Simulation Mode)

To enable offline testing without real drones or external APIs, we synthesize data streams.

**A. Detection Data Generator**
Simulates YOLO outputs based on predefined disaster severity curves.
- `crowd_density`: Baseline + random spikes.
- `flood_level`: Logistic growth curve based on synthetic rainfall.
- `structural_damage`: Step function triggered by earthquake/wind spikes.

**B. Weather Data Generator**
Time-series generation using Perlin noise or random walks.
- `rainfall_mm`: (0-100mm/hr)
- `wind_kmh`: (0-200km/h)
- `severity_scoring`: Weighted sum `(0.6 * rain) + (0.4 * wind)`.

**C. Historical RAG Data**
JSON documents detailing past events:
- `"Event": "Kerala Floods 2018"`
- `"Decisions": "Deployed 50 boats to Zone A"`
- `"Outcomes": "98% rescue rate, 2 shelters over-capacity"`
*These are converted to vector embeddings via ChromaDB.*

**D. Resource Data**
Geospatially distributed entities initialized via seed scripts.
- Shelters: `{lat, lon, capacity, current_occupancy}`
- Volunteers: `{lat, lon, availability_status}`

---

## 🤖 3. Model Training Pipeline

**YOLOv8 Training Command (CLI equivalent):**
```bash
yolo task=detect mode=train model=yolov8m.pt data=datasets/rakshasetu_unified/data.yaml epochs=200 imgsz=640 batch=32 project=RakshaSetu name=aerial_v1
```

**Augmentation Strategy:**
- `mosaic: 1.0` (crucial for small objects like people in aerial views)
- `mixup: 0.2` (helps model generalize combined disasters like flooded cars)
- `hsv_s: 0.7` (simulates varying weather, fog, and rain)
- `degrees: 15.0` (simulates drone roll/pitch)

**Class Balancing:**
Minority classes (like `fire_smoke`) will be oversampled in the dataset merger by duplicating their images/labels with slight augmentations, ensuring the model doesn't bias towards `vehicle` or `person`.

**Model Output → System Mapping:**
- Count of `person` boxes -> `crowd_density`
- Area of `flooded_area` polygon/box -> `flood_severity`
- Count of `damaged_struct` -> `infrastructure_status`

---

## 🧠 4. Multi-Agent Integration (Data Flow)

1. **Triage Agent**: Ingests drone frames -> Runs YOLOv8 -> Outputs JSON `{"zone": "A", "people": 45, "flood_detected": true}`.
2. **Weather Agent**: Reads synthetic weather stream -> Outputs `{"trend": "worsening", "rainfall_mm": 45}`.
3. **Zone Analyst Agent**: Takes Triage + Weather data -> Queries **RAG (ChromaDB)** for similar past scenarios -> Outputs `{"risk_level": "CRITICAL", "recommendation": "immediate evacuation"}`.
4. **Resource Allocator Agent**: Receives CRITICAL status -> Queries DB for nearest shelters/volunteers -> Outputs `{"allocate": [{"resource_id": 12, "destination": "Zone A"}]}`.
5. **Notifier Agent**: Formats allocation into natural language SMS/Email alerts.
6. **Feedback Agent**: Monitors if resources reached destination in simulation time -> Adjusts weights.
7. **Supervisor Agent (LangGraph/CrewAI)**: Orchestrates the graph, handling failures and routing.

---

## 🗄️ 5. Database Design (PostgreSQL / Supabase)

**Schema Overview:**

```sql
CREATE TABLE weather_records (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    zone_id VARCHAR(50),
    rainfall_mm FLOAT,
    wind_kmh FLOAT
);

CREATE TABLE detection_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    zone_id VARCHAR(50),
    person_count INT,
    hazard_type VARCHAR(50), -- 'flood', 'fire', 'none'
    severity_score FLOAT
);

CREATE TABLE shelters (
    id SERIAL PRIMARY KEY,
    zone_id VARCHAR(50),
    lat FLOAT,
    lon FLOAT,
    max_capacity INT,
    current_occupancy INT
);

CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    message TEXT,
    recipient_role VARCHAR(50),
    status VARCHAR(20) -- 'sent', 'failed'
);
```

---

## 🌍 6. Simulation Mode

A fully offline runtime execution graph.

**Scenarios:**
- `flood_event`: Ramps up synthetic rainfall -> synthetic `flood_area` YOLO detections increase.
- `fire_event`: High wind, low humidity -> triggers `fire_smoke` anomalies.
- `calm`: Normal variance, tests baseline system stability.

**Runtime:**
The backend spins up background threads running the synthetic generators, pumping data into the DB, which the Agents read from in an event-driven loop.

---

## ⚙️ 7. Step-by-Step Implementation Plan

1. **Download Datasets**: Fetch VisDrone, FloodNet, AIDER locally.
2. **Convert Formats**: Use conversion scripts to make everything YOLO `txt` format.
3. **Merge Datasets**: Run `dataset_merger.py` with unified class mappings.
4. **Train YOLO Model**: Execute `train_rakshasetu.py` on GPU.
5. **Build Synthetic Generators**: Finalize `synthetic_generator.py` to output dynamic JSON streams.
6. **Seed Database**: Inject mock shelters and volunteers.
7. **Setup RAG**: Chunk historical PDFs/JSONs and embed into ChromaDB.
8. **Run Agents**: Start the LangGraph orchestration (`agent_graph.py`).
9. **Validate Outputs**: Monitor the frontend dashboard and console logs for correct alerting logic.

---

*See the `model_pipeline/scripts/train_rakshasetu.py` file for the exact training implementation logic.*
