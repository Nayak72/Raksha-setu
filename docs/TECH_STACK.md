# 🛠️ RakshaSetu: Technology Stack & Core Concepts

This document provides a comprehensive breakdown of all the frameworks, tools, and computer science concepts utilized in the RakshaSetu project. It details **what** they are, **why** they were chosen over alternatives, and exactly **how** they are implemented in the codebase.

---

## 1. LangGraph 
**What it is:** A powerful framework built on top of LangChain specifically designed for creating stateful, multi-actor LLM applications using graph architectures.
**Why we use it:** Traditional LLM chains (like standard LangChain or AutoGen) are linear and brittle. Disaster management requires cyclic logic, conditional routing, and human-in-the-loop fail-safes. LangGraph allows us to define agents as nodes in a Directed Acyclic Graph (DAG) with cyclic capabilities.
**How it's used:** 
* It manages the central `AgentState` dictionary.
* It routes the disaster data between specialized agents (Triage $\rightarrow$ Weather $\rightarrow$ Zone Analyst $\rightarrow$ Allocator $\rightarrow$ Notifier).
* It handles conditional logic natively (e.g., if the Triage agent detects conflicting data, LangGraph routes the flow directly to the Supervisor agent, bypassing the rest of the pipeline).

## 2. Local LLMs (Powered by Ollama)
**What it is:** Ollama is an engine that allows running large language models (like `qwen2.5:7b` or `llama3`) natively on local hardware without requiring cloud APIs.
**Why we use it:** **Resilience and Privacy.** During a severe disaster, internet connectivity is often the first infrastructure to fail. Relying on OpenAI or Anthropic APIs would render the system useless. Local LLMs guarantee zero API latency, zero ongoing costs, and total data privacy.
**How it's used:** 
* Runs as a background service on the host machine.
* The Python backend communicates with it via local HTTP requests.
* The models perform the cognitive synthesis for the Zone Analyst (deciding whether to evacuate) and the Supervisor (resolving conflicting sensor data).

## 3. Retrieval-Augmented Generation (RAG) & ChromaDB
**What it is:** RAG is a concept where an LLM is provided with external, searchable data context before answering. `ChromaDB` is an open-source vector database designed to store and retrieve these high-dimensional embeddings.
**Why we use it:** LLMs inherently lack long-term memory. If a similar disaster happened last year, a standard LLM wouldn't know. RAG gives the agents "historical intuition" by allowing them to instantly recall how past crises were handled, preventing repetitive mistakes.
**How it's used:** 
* Uses `sentence-transformers` (`all-MiniLM-L6-v2`) to convert JSON weather/detection payloads into vector embeddings.
* Maintains separate ChromaDB collections (`weather_history` and `detection_history`).
* When a new disaster occurs, the Zone Analyst queries ChromaDB to pull the top 5 most similar historical events and injects them into the LLM prompt for context.

## 4. FastAPI & Python AsyncIO
**What it is:** A modern, incredibly fast Python web framework built on standard Python type hints and ASGI (Asynchronous Server Gateway Interface).
**Why we use it:** Disaster systems handle massive influxes of telemetry data. Traditional synchronous frameworks (like Flask/Django) block the execution thread while waiting for I/O (like DB inserts or LLM responses). FastAPI's native `async/await` handles thousands of concurrent connections efficiently.
**How it's used:** 
* Exposes the core endpoints (`/api/v1/detect`, `/api/v1/simulate-weather`).
* Utilizes FastAPI `BackgroundTasks`. When a detection payload is received, the HTTP endpoint returns a `201 Created` instantly, while the heavy LangGraph multi-agent execution is spun off asynchronously in the background.

## 5. Supabase (PostgreSQL & PostGIS)
**What it is:** An open-source Firebase alternative built on top of PostgreSQL, extended with real-time web-socket capabilities and geospatial querying via PostGIS.
**Why we use it:** We needed relational data integrity (Users, Zones, Shelters) combined with instant UI updates and complex spatial math (finding shelters within X kilometers of a disaster).
**How it's used:** 
* **Relational State**: Stores all structured data, including the `agent_logs` trace.
* **Realtime Publications**: The React frontend subscribes to table changes. When the Resource Allocator locks in volunteer assignments, the UI metric cards update instantly without the frontend having to refresh or poll the server.
* **Spatial Queries**: Uses PostGIS `ST_Distance` inside the backend tools to calculate which shelters are closest to the disaster epicenter.

## 6. UDP Broadcast (Local Resilience)
**What it is:** A connectionless, low-overhead communication protocol used for one-to-many broadcasting on a local network.
**Why we use it:** **Offline Survivability.** During a disaster, the internet often fails. UDP allows the system to alert everyone on the local LAN/Mesh network (like a neighborhood Wi-Fi or community network) even if the global web is completely offline.
**How it's used:** 
* The Python backend sends raw datagrams to the `255.255.255.255` broadcast address on port `5005`. 
* This bypasses the need for any central server, broker, or handshake, making it extremely robust in unstable network conditions.

## 7. Firebase Cloud Messaging (FCM)
**What it is:** A cross-platform messaging solution that lets you reliably deliver messages at no cost.
**Why we use it:** **Wake-on-Push.** Standard background services on Android are often killed to save battery. FCM high-priority "data" messages are the only reliable way to "wake up" a completely closed app to show an emergency alert.
**How it's used:** 
* The Python backend uses the `firebase-admin` SDK to push alerts to the `"alerts"` topic.
* This ensures that even if a citizen has swiped the app away, their phone will still receive the evacuation order.

## 8. Android Application (Kotlin & Foreground Services)
**What it is:** A native mobile application built for disaster-affected citizens.
**Why we use it:** Browsers cannot access low-level networking (like UDP sockets) or bypass lock screens. A native app provides high-priority "Critical Alerts".
**How it's used:** 
* **Foreground Service**: Runs a `UdpListenerService` with a persistent notification to keep the network socket open indefinitely.
* **Lock-Screen Overlay**: Uses `AlertActivity` with `showWhenLocked` flags to ensure instructions are visible without needing to unlock the device.
* **Networking**: Uses `OkHttp` for reliable HTTP POST acknowledgments of alerts.

## 9. React, Vite, TailwindCSS & Leaflet
**What it is:** The modern frontend stack. React for component logic, Vite for ultra-fast build tooling, Tailwind for utility-first styling, and Leaflet for interactive maps.
**Why we use it:** Emergency operators need a visually dense, instantly updating, and highly responsive dashboard. 
**How it's used:** 
* **Vite/React**: Manages the component lifecycle.
* **Leaflet**: Renders the `LiveMap`, plotting risk zones with pulsating radius circles (based on severity score) and shelter capacities dynamically.
* **Tailwind**: Enables the "Glassmorphism" dark-mode UI, providing a premium, high-contrast command center aesthetic.

## 10. Event-Driven Architecture (Concept)
**What it is:** A software architecture paradigm promoting the production, detection, consumption of, and reaction to events, rather than scheduled polling.
**Why we use it:** Constant API polling (asking "is there new data?" every 2 seconds) wastes massive amounts of CPU and network bandwidth.
**How it's used:** 
* The entire system is reactive. A camera detects a flood $\rightarrow$ pushes to API $\rightarrow$ triggers Background Task $\rightarrow$ triggers Agent Pipeline $\rightarrow$ updates Database $\rightarrow$ triggers Supabase Realtime $\rightarrow$ updates React State & Mobile Devices.

