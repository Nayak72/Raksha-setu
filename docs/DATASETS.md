# 📊 RakshaSetu: Datasets & Data Layers

This document outlines all the datasets and data structures utilized in the RakshaSetu project, explaining **what** they are, **how** they are implemented within the system, and **why** they are absolutely essential for the AI agents to function.

---

## 1. 🚁 Drone/Aerial Imagery Dataset (Computer Vision Input)

**What it is:**
A curated dataset of high-resolution aerial and drone images representing four distinct geographical zones (Zone 1, Zone 2, Zone 3, Zone 4). This dataset is hosted securely inside a **Supabase Storage Bucket**.

**How it is used:**
*   **The Vision Agent (YOLO Pipeline):** This dataset acts as the raw input feed for the system's Computer Vision pipeline. 
*   Instead of humans manually assessing the damage, images from these buckets are fed into an object detection model (like YOLOv8).
*   The model analyzes the image and extracts quantifiable, structured metrics:
    *   `crowd_density` (e.g., detecting large gatherings of stranded people)
    *   `flood_level` (e.g., water boundary detection)
    *   `structural_damage` (e.g., collapsed roofs, blocked roads)
    *   `fire_detected` (Boolean flag)

**Why it is used:**
During a severe disaster (earthquakes, floods), on-the-ground IoT sensors often lose power or are physically destroyed. Aerial imagery is the most resilient form of telemetry. This dataset simulates live drone feeds, giving the AI an immediate, uncompromised "bird's-eye view" of the disaster to determine raw severity before weather or historical data is even considered.

---

## 2. 🧠 Historical Disaster Memory Dataset (RAG / ChromaDB)

**What it is:**
A continuously growing dataset of past disaster events, historical weather patterns, and the subsequent decisions made by emergency operators. It is stored locally as high-dimensional vector embeddings inside **ChromaDB**.

**How it is used:**
*   **Retrieval-Augmented Generation (RAG):** When a new disaster occurs, the `Zone Analyst Agent` takes the current telemetry (e.g., "40mm rain, hilly terrain, high crowd density") and queries this dataset.
*   ChromaDB uses `sentence-transformers` to calculate mathematical similarity, instantly returning the top 3 most similar past disasters.
*   These historical records are injected directly into the Local LLM's prompt as context before it makes a decision.

**Why it is used:**
LLMs are stateless—they have no inherent memory of what happened yesterday. This dataset acts as the "Long-Term Memory" of the system. If a specific combination of weather and terrain historically led to a landslide 80% of the time, the RAG dataset provides this precedent, allowing the AI to preemptively order an `EVACUATE` decision rather than reacting too late.

---

## 3. 🗺️ Geospatial & Logistics Dataset (PostGIS / Supabase)

**What it is:**
A strictly structured relational dataset stored in **Supabase PostgreSQL**, utilizing the **PostGIS** extension for spatial mathematics.

**It consists of three primary tables:**
1.  **Zones:** Coordinates (Latitude/Longitude), baseline risk scores, and terrain types (e.g., coastal, hilly).
2.  **Shelters:** Physical coordinates, total bed capacities, and dynamic `current_occupancy` trackers.
3.  **Volunteers:** Physical coordinates, deployment status, and specialized skills (e.g., "medical", "rescue", "logistics").

**How it is used:**
*   **Resource Allocator Agent:** This agent queries the dataset using spatial SQL (e.g., `ST_Distance`) to find resources within a specific radius (e.g., 15km) of the disaster zone.
*   It filters the dataset dynamically (e.g., only querying volunteers with "rescue" skills if the disaster severity is CRITICAL).
*   It executes atomic database updates to lock in shelter beds and mark volunteers as "DEPLOYED", preventing double-booking.

**Why it is used:**
While LLMs are great at reasoning, they are terrible at exact mathematics and spatial awareness. The AI cannot "guess" where a shelter is or if it has beds left. This dataset grounds the AI in physical reality, ensuring that when it drafts a rescue plan, it is dealing with mathematically verified distances and strictly tracked logistical capacities.

---

## 4. 🌦️ Stochastic Weather Simulation Dataset (Dynamic Generation)

**What it is:**
Unlike static datasets, this is a dynamically generated, time-series dataset produced by the system's **Weather Agent**.

**How it is used:**
*   It takes baseline meteorological data and applies continuous mathematical transformations based on the zone's terrain.
*   *Example:* If the terrain is "hilly" and elevation is above 500m, the agent mathematically increases the rainfall multiplier (simulating orographic lift). 
*   It outputs a continuous stream of `rainfall_mm`, `wind_speed_kmh`, and `humidity_pct`.

**Why it is used:**
Weather is the primary multiplier of disaster severity. A minor flood becomes a critical emergency if continuous heavy rainfall is projected for the next 6 hours. This dynamically generated dataset allows the AI to predict the *trajectory* of the disaster, rather than just reacting to the *current* state.
