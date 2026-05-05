# RAKSHA AI — Offline-First Disaster Response Intelligence

![RAKSHA AI Banner](https://placehold.co/1200x400/0A0F1E/00B0FF?text=RAKSHA+AI)

RAKSHA AI is a fully offline-capable, multimodal disaster response platform powered by Gemma 4. It provides field responders with AI-grade intelligence — damage assessment, medical triage, smart dispatch, and multilingual communication — even when internet infrastructure is completely destroyed.

Created for the **Gemma 4 Good Hackathon**.
Tracks: **Global Resilience** & **Special Tech (Ollama)**

---

## 🌟 Key Capabilities

1. **Multimodal Damage Assessment**: Photograph damage and Gemma 4 vision instantly estimates severity, hazards, and required rescue teams.
2. **Native Function Calling for Real Actions**: Gemma 4 doesn't just chat; it uses native function calling to *dispatch* responders, *broadcast* alerts, and *generate* routing.
3. **True Offline Intelligence**: The full system runs locally via Ollama with Gemma 4 4B on edge devices (laptops, mini PCs). 
4. **Adaptive Cloud Sync**: When internet returns, it automatically switches to Gemma 4 27B via API and syncs local data.
5. **Medical Triage Intelligence**: AI-guided START protocol triage for mass casualty events.
6. **22+ Languages**: Native support for diverse disaster-affected communities.

## 🏗️ Architecture

- **AI Layer**: Gemma 4 4B (Ollama, local) / Gemma 4 27B (Google AI API, cloud)
- **Backend**: FastAPI (Python), SQLite (offline WAL mode), WebSockets
- **Frontend**: Vanilla JS, PWA Service Worker, Leaflet.js (offline maps)
- **Deployment**: Docker Compose

Read the full [Architecture Document](./ARCHITECTURE.md) and [Product Design](./PROJECT_DESIGN.md).

## 🚀 Quick Start (Local Deployment)

To run RAKSHA AI locally in full offline mode:

### 1. Prerequisites
- Docker and Docker Compose installed
- [Ollama](https://ollama.ai) installed locally

### 2. Prepare Local AI
Start Ollama and pull the Gemma 4 model:
```bash
ollama run gemma4:4b
```

### 3. Launch RAKSHA
```bash
# Clone repository
git clone https://github.com/your-username/raksha-ai.git
cd raksha-ai

# Start services
docker-compose up -d
```

Access the dashboard at: `http://localhost:8000`

## ⚙️ Configuration

If you want to use the cloud-connected Gemma 4 27B model (for testing/online usage):

1. Copy `.env.example` to `.env` in the `backend/` directory
2. Add your Google API Key:
```env
GOOGLE_API_KEY=your_key_here
GEMMA_CLOUD_MODEL=gemma-4-27b-it
```

## 🗺️ Kaggle Submission

Read the official [Kaggle Writeup](./KAGGLE_WRITEUP.md) included in this repository.

## 📜 License
MIT License
