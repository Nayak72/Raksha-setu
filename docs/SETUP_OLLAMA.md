# 🦙 RakshaSetu: Ollama Setup Guide

This guide provides step-by-step instructions on how to install, configure, and test Ollama (for Local LLM inference).

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

