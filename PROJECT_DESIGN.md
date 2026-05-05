# RAKSHA AI — Product Design Document

## Executive Summary

**RAKSHA AI** is a Gemma 4-powered disaster response intelligence platform built for frontline responders and affected communities. The platform is designed for zero-connectivity environments — cyclone zones, flood-hit villages, earthquake rubble — where internet infrastructure is destroyed but human coordination is most critical.

---

## 1. Problem Statement

### The Crisis Reality

Every major disaster destroys the very infrastructure needed to coordinate the response:

- **Hurricane Katrina (2005)**: 80% of New Orleans communications infrastructure failed in 72 hours
- **Turkey Earthquake (2023)**: Rescue teams couldn't share GPS coordinates; 50,000+ deaths
- **Cyclone Idai (2019)**: 90,000 people unreachable for 4+ days due to comms blackout
- **India Floods (2024)**: 700+ deaths partially attributed to delayed response coordination

**The core problem**: Disaster response coordination depends on real-time information exchange, but disasters destroy communication infrastructure exactly when it's needed most.

### Current Tool Failures

| Tool | Limitation |
|------|-----------|
| WhatsApp/SMS | Requires connectivity |
| FEMA Apps | Cloud-dependent |
| Radio Systems | One-way, no AI intelligence |
| Paper Forms | No aggregation, error-prone |
| Satellite Phones | Expensive, one per team |

---

## 2. Target Users

### Primary Users

**Field Responders** (Search & Rescue, Medical, NDRF)
- Need: Damage assessment without expert consultation
- Context: In the field, often without connectivity
- Pain: Can't reach command center; AI guidance needed

**Incident Commanders** (District Collectors, Emergency Directors)
- Need: Real-time situational awareness
- Context: Command center with intermittent connectivity
- Pain: Incomplete picture; poor resource allocation

**Community Volunteers**
- Need: Protocol guidance, reporting capability
- Context: Untrained but willing; diverse languages
- Pain: Don't know what to do or how to report

### Secondary Users

**Medical Triage Personnel**
- Need: Quick triage guidance with AI support
- Context: Mass casualty, overwhelmed

**Citizens in Affected Areas**
- Need: Evacuation routes, safety information
- Context: Scared, potentially injured, no internet

---

## 3. Product Features

### 3.1 Core Module: AI Incident Assessment

**How it works:**
1. Responder photographs damage (building collapse, flood, fire)
2. Gemma 4 multimodal vision analyzes the image
3. Returns: severity score, hazards, recommended actions, resource estimate
4. Automatically creates incident record and suggests dispatch

**Gemma 4 Advantage:** Native multimodal understanding means accurate assessment without custom trained models.

**Sample Assessment Output:**
```
📍 DAMAGE ASSESSMENT REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━
Severity: 8.2/10 (CRITICAL)
Type: Partial structural collapse
Trapped persons: Estimated 3-7

🚨 Immediate Hazards:
  • Gas leak detected (visual cues: debris pattern)
  • Live electrical wires exposed (NE corner)
  • Secondary collapse risk: 74%

✅ Recommended Actions:
  1. Establish 50m exclusion zone
  2. Deploy USAR team with gas detection
  3. Utility shutoff before entry
  4. Medical standby for crush injury protocol

📦 Resources Required:
  • USAR Team: 1x (8 persons)
  • Medical: 1x Paramedic team
  • Equipment: Hydraulic spreaders, gas detector
```

---

### 3.2 Core Module: Offline AI Chat Assistant

**Multilingual emergency guidance in 22+ languages**

The AI assistant provides:
- First aid protocols
- Evacuation guidance
- Safety checklists
- Survivor location protocols
- Mental health first aid

**Language Support**: Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Odia, Malayalam, Punjabi, Arabic, Swahili, French, Spanish, Indonesian, Portuguese, and more.

**Offline Operation**: Gemma 4 4B via Ollama runs fully on-device with 4GB RAM.

---

### 3.3 Core Module: Smart Dispatch (Function Calling)

Gemma 4's native function calling enables RAKSHA to take **real actions**:

```
User: "Send a medical team to the school on MG Road"

RAKSHA AI (internally):
  → analyze_location("school on MG Road") 
  → find_nearest_medical_team(lat, lng)
  → check_team_availability(team_id)
  → dispatch_responder(team_id, coords, priority="critical")
  → send_notification(team, "Dispatch confirmed")

User sees: "Medical Team Alpha dispatched. ETA 8 minutes. 
            Team lead: Dr. Priya Sharma (+91-XXXXX)"
```

---

### 3.4 Core Module: Medical Triage System

START (Simple Triage and Rapid Treatment) protocol implemented with AI guidance:

| Category | Color | Action |
|----------|-------|--------|
| Immediate | 🔴 Red | Life-threatening, treat now |
| Delayed | 🟡 Yellow | Serious but stable |
| Minimal | 🟢 Green | Walking wounded |
| Expectant | ⬛ Black | Unlikely to survive |

AI helps untrained volunteers perform triage by asking structured questions and providing guidance.

---

### 3.5 Core Module: Evacuation Route Intelligence

- Offline map tiles (OpenStreetMap)
- Dynamic hazard zones drawn by responders
- AI generates routes avoiding marked danger areas
- Multi-language turn-by-turn guidance
- Works with or without GPS (landmark-based)

---

### 3.6 Core Module: Incident Command Dashboard

Real-time overview (online) / cached snapshot (offline):
- Heat map of active incidents
- Responder locations and status
- Resource allocation
- Timeline of events
- AI-generated situation reports (SITREP)
- Exportable incident logs for post-disaster analysis

---

## 4. User Experience Design

### Design Principles

1. **Stress-Proof UI**: Designed for users under extreme stress
   - Large touch targets (48px minimum)
   - High contrast (WCAG AAA)
   - Single-action per screen where possible
   - Clear status indicators

2. **Zero Training Required**: A volunteer with no prior training should be productive in < 60 seconds

3. **Graceful Degradation**: Every feature works offline with reduced capability

4. **Multilingual First**: Language selector on first launch, not buried in settings

### Color System

| Color | Hex | Usage |
|-------|-----|-------|
| Emergency Red | `#FF1744` | Critical alerts, danger |
| Warning Orange | `#FF6D00` | High priority, caution |
| Safe Green | `#00E676` | Clear, safe, confirmed |
| Primary Blue | `#00B0FF` | Interface, navigation |
| Background Dark | `#0A0F1E` | App background |
| Surface | `#111827` | Cards, panels |
| Text Primary | `#F0F4FF` | Primary text |
| Text Secondary | `#94A3B8` | Secondary text |

### Typography

- **Headings**: Inter (700, 600)
- **Body**: Inter (400, 500)
- **Monospace**: JetBrains Mono (data, coordinates, IDs)
- **Size Scale**: 12/14/16/18/24/32/48px

---

## 5. Technical Innovation

### 5.1 Why Gemma 4 Specifically

| Feature | How RAKSHA Uses It |
|---------|-------------------|
| Multimodal Vision | Damage assessment from photos |
| Native Function Calling | Real dispatch actions, not just text |
| 128K Context Window | Full incident history in one prompt |
| Multilingual | 22+ languages for diverse communities |
| Small (4B) + Large (27B) | Edge (offline) + Cloud (when available) |
| Open Weights | Deploy anywhere, no data leaves |

### 5.2 Adaptive Intelligence Architecture

```
Request arrives
      │
      ├── Image attached? ──→ Multimodal path
      │
      ├── Action needed? ──→ Function calling path
      │
      ├── Complex analysis? ──→ 27B (if online)
      │
      └── Field query? ──→ 4B Ollama (offline capable)
```

### 5.3 Data Sovereignty

All data stays local unless explicitly synced:
- No telemetry
- No cloud dependency
- Patient data never leaves device
- Incident data opt-in sync only

---

## 6. Impact Metrics

### Quantifiable Goals

| Metric | Baseline (Manual) | With RAKSHA AI |
|--------|-------------------|----------------|
| Damage assessment time | 45 min (expert) | 30 seconds |
| Triage accuracy (untrained) | ~60% | ~87% |
| Responder dispatch time | 15-20 min | < 2 min |
| Language barriers | Major | Eliminated |
| Offline operation | 0% | 100% |
| Information loss | High | Near-zero |

### Target Communities

- **Primary**: India (NDRF, SDRF, District Administration)
- **Secondary**: South/Southeast Asia, East Africa
- **Scale Potential**: 1.2 billion people in disaster-prone regions

---

## 7. Competitive Landscape

| Solution | Online Required | AI Powered | Open Source | Multimodal | Cost |
|----------|----------------|------------|-------------|------------|------|
| RAKSHA AI | No | Yes (Gemma 4) | Yes | Yes | Free |
| FEMA App | Yes | No | No | No | Free |
| Palantir | Yes | Partial | No | No | $$$$ |
| Sahana Eden | Partial | No | Yes | No | Free |
| WebEOC | Yes | No | No | No | $$$ |

---

## 8. Go-to-Market Strategy

### Phase 1: Pilot (Months 1-3)
- Partner with 2-3 Indian state disaster management authorities
- Deploy in Odisha (cyclone-prone) + Assam (flood-prone)
- Train 500 field responders

### Phase 2: Scale (Months 4-12)
- NDRF national deployment
- Partner with UN OCHA for international expansion
- Community volunteer program

### Phase 3: Global (Year 2)
- WHO partnership for medical triage module
- World Bank funding for underserved regions
- Open-source community contributions

---

## 9. Project Directory Structure

```
raksha-ai/
├── 📄 README.md
├── 📄 ARCHITECTURE.md
├── 📄 PROJECT_DESIGN.md
├── 📄 KAGGLE_WRITEUP.md
├── 🐳 docker-compose.yml
├── 🐳 Dockerfile
│
├── backend/
│   ├── main.py              # FastAPI application
│   ├── gemma_client.py      # Gemma 4 API + Ollama integration
│   ├── tools.py             # Function calling tool implementations
│   ├── models.py            # Pydantic data models
│   ├── database.py          # SQLite database layer
│   ├── routers/
│   │   ├── incidents.py     # Incident management endpoints
│   │   ├── chat.py          # AI chat endpoints
│   │   ├── responders.py    # Responder management
│   │   ├── triage.py        # Medical triage
│   │   └── alerts.py        # Emergency alerts
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html           # Main app shell
│   ├── styles.css           # Design system + components
│   ├── app.js               # Application logic
│   ├── sw.js                # Service worker (offline)
│   ├── manifest.json        # PWA manifest
│   └── assets/
│       ├── icons/
│       └── sounds/
│
└── notebooks/
    └── gemma4_demo.ipynb    # Kaggle notebook demo
```
