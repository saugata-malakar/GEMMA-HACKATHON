# 🛡️ RAKSHA AI — Offline-First Disaster Intelligence
### Powered by Gemma 4 & Ollama

[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-brightgreen)](https://gemma-hackathon.onrender.com/)
[![Track](https://img.shields.io/badge/Track-Global_Resilience-blue)](#)
[![Tech](https://img.shields.io/badge/Tech-Gemma_4-orange)](#)

**RAKSHA** (Sanskrit for "Protection") is a premium, mission-critical disaster response platform. It provides field responders with AI-grade intelligence—multimodal damage assessment, medical triage, and autonomous coordination—in environments where the internet has completely failed.

---

## 🚀 Live Deployment
The platform is globally deployed and accessible here:
👉 **[https://gemma-hackathon.onrender.com/](https://gemma-hackathon.onrender.com/)**

---

## ✨ Key Innovations

### 1. 👁️ Zero-Cost Multimodal Intelligence
Uses a hybrid vision pipeline (HuggingFace BLIP + Pollinations LLM) to analyze disaster footage. It identifies structural damage, life hazards, and trapped persons without requiring expensive GPU infrastructure.

### 2. 🏥 AI-Guided Medical Triage
Guides untrained volunteers through the **START Triage Protocol**. The AI assesses symptoms and vitals in real-time to assign life-saving priority levels (Red/Yellow/Green/Black).

### 3. 🤖 Autonomous Overwatch
A background AI commander that monitors incoming reports and automatically dispatches the nearest available responders to high-severity incidents using **Native Function Calling**.

### 4. 🌐 Multilingual & Offline-First
- **Offline PWA**: Installable on any smartphone; caches entire UI and logic for 100% offline use.
- **22+ Languages**: Native support for Hindi, Tamil, Bengali, and more, ensuring local volunteers can act immediately.

---

## 🛠️ Technical Architecture

- **AI Core**: Gemma 4 4B (Local via Ollama) & Gemma 4 27B (Cloud via Google AI).
- **Backend**: FastAPI (Python 3.11) with SQLite WAL-mode for high-concurrency offline sync.
- **Frontend**: Premium "Cyber-Ops" Glassmorphism UI (Vanilla JS/CSS) for maximum performance on field devices.
- **Deployment**: Dockerized high-availability setup on Render.

---

## 🏗️ Local Setup

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/saugata-malakar/GEMMA-HACKATHON.git
   cd GEMMA-HACKATHON
