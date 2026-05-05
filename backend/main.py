"""
RAKSHA AI — FastAPI Main Application
Entry point for the RAKSHA AI disaster response backend.
"""

import os
import time
import uuid
import json
import base64
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from database import db
from gemma_client import gemma_client, model_selector
from medical_rag import med_rag
from models import (
    Incident, IncidentCreate, IncidentUpdate, IncidentStatus,
    Responder, ResponderCreate, ResponderStatus,
    TriageEntry, TriageCreate,
    Alert, AlertCreate, AlertSeverity,
    ChatRequest, ChatResponse, ChatMessage,
    AssessmentRequest, DispatchRequest, DispatchResult,
    AIAssessment, ResourceEstimate,
    GeoPoint, Priority, SystemStatus
)

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("raksha")

START_TIME = time.time()

# ─── WebSocket Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Handle non-serializable objects (like datetime)
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError ("Type %s not serializable" % type(obj))
            
        json_msg = json.loads(json.dumps(message, default=json_serial))
        
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(json_msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_to(self, websocket: WebSocket, message: dict):
        await websocket.send_json(message)


manager = ConnectionManager()


# ─── App Lifecycle ────────────────────────────────────────────────────────────

async def overwatch_agent():
    """Background AI agent that monitors the situation and acts autonomously."""
    while True:
        try:
            await asyncio.sleep(60) # Check every minute
            
            # Find critical unassigned incidents
            incidents = await db.list_incidents(status="reported")
            critical_unassigned = [i for i in incidents if i.severity > 6.0 and len(i.responders_assigned) == 0]
            
            if critical_unassigned:
                incident = critical_unassigned[0]
                responders = await db.list_responders(status="available")
                if responders:
                    logger.info(f"[*] Overwatch Agent analyzing critical incident: {incident.id}")
                    prompt = f"""[AUTONOMOUS OVERWATCH ACTIVATED]
Critical unassigned incident: {incident.type} at coordinates {json.dumps(incident.coordinates)}.
Description: {incident.description}. Severity: {incident.severity}.
Available responders: {json.dumps([r.dict() for r in responders])}

ACTION REQUIRED: You must immediately call 'dispatch_responder' to send the best available team. You must also call 'broadcast_emergency_alert' to warn the area. Do not ask for confirmation."""
                    
                    result = await gemma_client.chat(
                        message=prompt,
                        enable_tools=True,
                        system_override="You are RAKSHA OVERWATCH, an autonomous AI commander. You monitor disasters and IMMEDIATELY take action via function calls. Do not hesitate."
                    )
                    
                    for fc in result.get("function_calls", []):
                        await _handle_function_side_effect(fc, incident.id)
                        
                    await manager.broadcast({
                        "type": "overwatch_action",
                        "data": {
                            "incident_id": incident.id,
                            "action": "Autonomous Dispatch & Alert Initiated",
                            "reasoning": result.get("message")
                        }
                    })
        except Exception as e:
            logger.error(f"Overwatch error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 RAKSHA AI starting up...")
    await db.connect()
    logger.info("✅ Database connected")
    
    # Initialize Medical RAG (FAISS)
    await med_rag.initialize()

    # Check AI model availability
    avail = await model_selector.check_availability()
    if avail["online"]:
        logger.info(f"✅ Cloud AI (Gemma 4 27B) available")
    if avail["local"]:
        logger.info(f"✅ Local AI (Gemma 4 4B via Ollama) available")
    if not avail["online"] and not avail["local"]:
        logger.warning("⚠️  No AI model available — offline fallback mode")

    # Start Overwatch Agent
    agent_task = asyncio.create_task(overwatch_agent())

    yield

    agent_task.cancel()

    logger.info("🛑 RAKSHA AI shutting down...")
    await db.disconnect()


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAKSHA AI",
    description="Offline-first Gemma 4-powered disaster response intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["*"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
PROTOTYPE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "dist"))

@app.get("/api/v1/status", response_model=SystemStatus)
async def get_status():
    avail = await model_selector.check_availability()
    model_type = "cloud" if avail["online"] else ("local" if avail["local"] else "none")

    active_incidents = await db.get_incident_count(status="active")
    available_responders = await db.get_available_responders_count()

    return SystemStatus(
        status="operational",
        version="1.0.0",
        online=avail["online"],
        model_available=avail["online"] or avail["local"],
        model_type=model_type,
        active_incidents=active_incidents,
        available_responders=available_responders,
        db_status="connected",
        uptime_seconds=time.time() - START_TIME
    )


# ─── Incidents ────────────────────────────────────────────────────────────────

@app.get("/api/v1/incidents")
async def list_incidents(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    incidents = await db.list_incidents(status=status, limit=limit, offset=offset)
    return {"incidents": [i.dict() for i in incidents], "total": len(incidents)}


@app.post("/api/v1/incidents", status_code=201)
async def create_incident(incident_data: IncidentCreate):
    incident = Incident(
        type=incident_data.type,
        description=incident_data.description,
        coordinates=incident_data.coordinates,
        affected_count=incident_data.affected_count,
        language=incident_data.language,
        reported_by=incident_data.reported_by
    )
    saved = await db.create_incident(incident)

    # Broadcast to dashboard
    await manager.broadcast({
        "type": "incident_created",
        "data": saved.dict()
    })

    logger.info(f"Incident created: {saved.id} ({saved.type.value})")
    return saved.dict()


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    incident = await db.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.dict()


@app.patch("/api/v1/incidents/{incident_id}")
async def update_incident(incident_id: str, updates: IncidentUpdate):
    incident = await db.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    if "status" in update_dict:
        update_dict["status"] = update_dict["status"].value

    updated = await db.update_incident(incident_id, update_dict)
    await manager.broadcast({"type": "incident_updated", "data": updated.dict()})
    return updated.dict()

class MeshSyncPayload(BaseModel):
    peer_id: str
    incidents: List[dict]
    triage_entries: List[dict]

@app.post("/api/v1/mesh/sync")
async def mesh_network_sync(payload: MeshSyncPayload):
    """Groundbreaking: Offline peer-to-peer data synchronization via Mesh Network."""
    merged_count = 0
    
    for inc_data in payload.incidents:
        existing = await db.get_incident(inc_data["id"])
        if not existing:
            await db.create_incident(Incident(**inc_data))
            merged_count += 1
            await manager.broadcast({"type": "new_incident", "data": inc_data})
            
    for t_data in payload.triage_entries:
        try:
            await db.create_triage_entry(TriageEntry(**t_data))
            merged_count += 1
            await manager.broadcast({"type": "triage_entry", "data": t_data})
        except Exception:
            pass # Ignore duplicates
            
    await manager.broadcast({
        "type": "mesh_sync",
        "data": {"peer": payload.peer_id, "merged_records": merged_count}
    })
    return {"status": "synced", "merged_records": merged_count}


class VoiceInput(BaseModel):
    audio_base64: str
    language: str = "en"

@app.post("/api/v1/voice/transcribe")
async def voice_transcribe(data: VoiceInput):
    """Simulates local Whisper.cpp offline voice transcription."""
    # In a full implementation, this would pass audio_base64 to a local Whisper.cpp process
    # For now, simulate the transcribed output based on RAKSHA emergency contexts.
    transcription = "[Whisper.cpp Local Synth] Immediate medical assistance needed. Patient has severe bleeding."
    return {"text": transcription, "language_detected": data.language}

# ─── AI Damage Assessment ─────────────────────────────────────────────────────

@app.post("/api/v1/assess")
async def assess_damage(
    image: UploadFile = File(...),
    disaster_type: Optional[str] = Form(None),
    building_type: Optional[str] = Form(None),
    incident_id: Optional[str] = Form(None),
    language: str = Form("en"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None)
):
    """Multimodal damage assessment using Gemma 4 vision."""
    # Read and encode image
    image_data = await image.read()
    image_b64 = base64.b64encode(image_data).decode("utf-8")

    logger.info(f"Damage assessment requested: {disaster_type}, {building_type}")

    assessment_data = await gemma_client.assess_damage(
        image_base64=image_b64,
        disaster_type=disaster_type,
        building_type=building_type,
        language=language
    )

    # If linked to an incident, update it
    if incident_id:
        ai_assessment = AIAssessment(
            damage_severity=assessment_data.get("damage_severity", 5),
            hazards=assessment_data.get("hazards", []),
            structural_integrity=assessment_data.get("structural_integrity", "unknown"),
            recommended_actions=assessment_data.get("recommended_actions", []),
            estimated_trapped=assessment_data.get("estimated_trapped"),
            confidence=assessment_data.get("confidence", 0.5),
            model_used=assessment_data.get("model_used", "unknown"),
            resource_requirements=ResourceEstimate(
                **assessment_data.get("resource_requirements", {})
            )
        )
        await db.update_incident(incident_id, {
            "ai_assessment": ai_assessment.json(),
            "severity": assessment_data.get("damage_severity", 5)
        })

        await manager.broadcast({
            "type": "assessment_complete",
            "incident_id": incident_id,
            "data": assessment_data
        })

    return assessment_data


@app.post("/api/v1/assess/base64")
async def assess_damage_base64(request: AssessmentRequest):
    """Damage assessment with base64 image (for offline/JS uploads)."""
    assessment_data = await gemma_client.assess_damage(
        image_base64=request.image_base64,
        disaster_type=request.disaster_type.value if request.disaster_type else None,
        building_type=request.building_type,
        language=request.language
    )
    return assessment_data


# ─── AI Chat ─────────────────────────────────────────────────────────────────

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """AI conversation endpoint with Gemma 4."""
    session_id = request.session_id or str(uuid.uuid4())

    # Load session history if exists
    history = [h.dict() for h in request.history]
    if not history and request.session_id:
        session = await db.get_chat_session(request.session_id)
        if session:
            history = session.get("history", [])

    result = await gemma_client.chat(
        message=request.message,
        history=history,
        image_base64=request.image_base64,
        language=request.language,
        enable_tools=True
    )

    # Update history
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": result["message"]})

    # Save session
    await db.save_chat_session(
        session_id=session_id,
        history=history[-20:],  # Keep last 20 turns
        language=request.language,
        incident_id=request.incident_id
    )

    # Handle function call side effects
    for fc in result.get("function_calls", []):
        await _handle_function_side_effect(fc, request.incident_id)

    return ChatResponse(
        session_id=session_id,
        message=result["message"],
        language=request.language,
        model_used=result.get("model_used", "unknown"),
        function_calls=result.get("function_calls", []),
        function_results=result.get("function_results", []),
        processing_time_ms=result.get("processing_time_ms", 0)
    )


async def _handle_function_side_effect(fc: dict, incident_id: Optional[str]):
    """Handle database/broadcast side effects of AI function calls."""
    name = fc.get("name")
    args = fc.get("args", {})

    if name == "broadcast_emergency_alert":
        alert = Alert(
            title=args.get("title", "Emergency Alert"),
            message=args.get("message", ""),
            severity=AlertSeverity(args.get("severity", "moderate")),
            languages=args.get("languages", ["en"]),
            incident_id=incident_id,
            created_by="RAKSHA AI"
        )
        await db.create_alert(alert)
        await manager.broadcast({"type": "new_alert", "data": alert.dict()})

    elif name == "dispatch_responder":
        role_str = args.get("responder_role")
        responders = await db.list_responders(status="available", role=role_str)
        if not responders:
            responders = await db.list_responders(status="available")
            
        if responders and incident_id:
            responder = responders[0]
            assigned = responder.incidents_assigned + [incident_id]
            await db.update_responder(responder.id, {
                "status": "dispatched",
                "incidents_assigned": json.dumps(assigned)
            })
            
            incident = await db.get_incident(incident_id)
            if incident:
                incident_responders = incident.responders_assigned + [responder.id]
                await db.update_incident(incident_id, {
                    "responders_assigned": json.dumps(incident_responders),
                    "status": "active"
                })
            
            await manager.broadcast({
                "type": "responder_dispatched",
                "data": {"responder": responder.dict(), "incident_id": incident_id}
            })
        else:
            await manager.broadcast({
                "type": "dispatch_initiated",
                "data": {
                    "role": args.get("responder_role"),
                    "location": args.get("location_description"),
                    "priority": args.get("priority"),
                    "incident_id": incident_id
                }
            })

    elif name == "log_medical_triage":
        from models import TriageColor, TriageEntry
        try:
            triage_color = TriageColor(args.get("triage_color", "yellow"))
        except ValueError:
            triage_color = TriageColor.YELLOW
            
        entry = TriageEntry(
            incident_id=incident_id,
            age_estimate=args.get("age_estimate"),
            symptoms=args.get("symptoms", []),
            triage_color=triage_color,
            ai_notes="Logged via AI Assistant"
        )
        saved = await db.create_triage_entry(entry)
        await manager.broadcast({"type": "triage_entry", "data": saved.dict()})

    elif name == "request_resources":
        await manager.broadcast({
            "type": "resource_requested",
            "data": {
                "incident_id": incident_id,
                "resources": args.get("resources", []),
                "urgency": args.get("urgency")
            }
        })
        
    elif name == "get_evacuation_route":
        await manager.broadcast({
            "type": "new_alert",
            "data": {
                "title": f"Evacuation: {args.get('hazard_type', 'Emergency')}",
                "message": f"Route generated for evacuation from {args.get('origin_description')}",
                "severity": "moderate",
                "timestamp": datetime.utcnow().isoformat()
            }
        })


# ─── Responders ───────────────────────────────────────────────────────────────

@app.get("/api/v1/responders")
async def list_responders(
    status: Optional[str] = None,
    role: Optional[str] = None
):
    responders = await db.list_responders(status=status, role=role)
    return {"responders": [r.dict() for r in responders]}


@app.post("/api/v1/responders", status_code=201)
async def create_responder(responder_data: ResponderCreate):
    responder = Responder(**responder_data.dict())
    saved = await db.create_responder(responder)
    return saved.dict()


@app.get("/api/v1/responders/{responder_id}")
async def get_responder(responder_id: str):
    responder = await db.get_responder(responder_id)
    if not responder:
        raise HTTPException(status_code=404, detail="Responder not found")
    return responder.dict()


@app.post("/api/v1/dispatch")
async def dispatch_responder(request: DispatchRequest):
    """Dispatch a responder to an incident."""
    incident = await db.get_incident(request.incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Find available responder
    responders = await db.list_responders(status="available")
    if not responders:
        return DispatchResult(
            success=False,
            message="No available responders at this time"
        )

    responder = responders[0] if not request.responder_id else None
    if request.responder_id:
        responder = await db.get_responder(request.responder_id)

    if not responder:
        return DispatchResult(success=False, message="Specified responder not found")

    # Update responder status
    assigned = responder.incidents_assigned + [request.incident_id]
    await db.update_responder(responder.id, {
        "status": "dispatched",
        "incidents_assigned": json.dumps(assigned)
    })

    # Update incident
    incident_responders = incident.responders_assigned + [responder.id]
    await db.update_incident(request.incident_id, {
        "responders_assigned": json.dumps(incident_responders),
        "status": "active"
    })

    # Broadcast
    await manager.broadcast({
        "type": "responder_dispatched",
        "data": {"responder": responder.dict(), "incident_id": request.incident_id}
    })

    return DispatchResult(
        success=True,
        responder=responder,
        eta_minutes=8.0,
        message=f"{responder.name} dispatched to incident {request.incident_id}"
    )


# ─── Medical Triage ───────────────────────────────────────────────────────────

@app.post("/api/v1/triage", status_code=201)
async def create_triage_entry(request: TriageCreate):
    """Create a medical triage entry with AI guidance."""
    # Get AI triage guidance
    guidance = await gemma_client.generate_triage_guidance(
        symptoms=request.symptoms,
        age_estimate=request.age_estimate,
        vitals=request.vitals,
        language=request.language
    )

    from models import TriageColor
    triage_color_str = guidance.get("triage_color", "yellow")
    try:
        triage_color = TriageColor(triage_color_str)
    except ValueError:
        triage_color = TriageColor.YELLOW

    entry = TriageEntry(
        incident_id=request.incident_id,
        age_estimate=request.age_estimate,
        gender=request.gender,
        symptoms=request.symptoms,
        vitals=request.vitals,
        triage_color=triage_color,
        ai_notes=guidance.get("reasoning", ""),
        location=request.location
    )

    saved = await db.create_triage_entry(entry)

    await manager.broadcast({"type": "triage_entry", "data": saved.dict()})

    return {
        "entry": saved.dict(),
        "ai_guidance": guidance
    }


@app.get("/api/v1/triage")
async def list_triage(incident_id: Optional[str] = None):
    entries = await db.list_triage_entries(incident_id=incident_id)
    return {"entries": [e.dict() for e in entries]}


# ─── Alerts ───────────────────────────────────────────────────────────────────

@app.post("/api/v1/alerts", status_code=201)
async def create_alert(request: AlertCreate):
    """Create and broadcast an emergency alert with multilingual translation."""
    translations = {}
    if len(request.languages) > 1:
        translations = await gemma_client.translate_alert(
            request.message,
            [l for l in request.languages if l != "en"]
        )

    alert = Alert(
        title=request.title,
        message=request.message,
        severity=request.severity,
        affected_zones=request.affected_zones,
        coordinates=request.coordinates,
        radius_km=request.radius_km,
        languages=request.languages,
        translations=translations,
        incident_id=request.incident_id
    )

    saved = await db.create_alert(alert)
    await manager.broadcast({"type": "new_alert", "data": saved.dict()})

    return saved.dict()


@app.get("/api/v1/alerts")
async def list_alerts(limit: int = 20):
    alerts = await db.list_alerts(limit=limit)
    return {"alerts": [a.dict() for a in alerts]}


# ─── Evacuation Routes ────────────────────────────────────────────────────────

@app.post("/api/v1/routes")
async def get_evacuation_route(
    origin_lat: float,
    origin_lng: float,
    hazard_type: Optional[str] = None,
    language: str = "en"
):
    """Generate AI-guided evacuation route."""
    result = await gemma_client.chat(
        message=f"""Generate evacuation guidance from coordinates ({origin_lat}, {origin_lng}).
Hazard: {hazard_type or 'general emergency'}.
Provide:
1. General direction to move (cardinal direction)
2. What to avoid
3. What to look for (landmarks, assembly points)
4. Emergency contacts
Keep it practical for someone who may be panicked.""",
        language=language,
        enable_tools=False
    )

    return {
        "origin": {"lat": origin_lat, "lng": origin_lng},
        "hazard_type": hazard_type,
        "guidance": result["message"],
        "model_used": result.get("model_used", "unknown")
    }


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """Real-time dashboard updates."""
    await manager.connect(websocket)
    try:
        # Send initial state
        incidents = await db.list_incidents(limit=20)
        responders = await db.list_responders()
        alerts = await db.list_alerts(limit=10)

        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "incidents": [i.dict() for i in incidents],
                "responders": [r.dict() for r in responders],
                "alerts": [a.dict() for a in alerts]
            }
        })

        while True:
            data = await websocket.receive_json()
            # Handle client messages (ping/pong, filter requests)
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """Streaming AI chat via WebSocket."""
    await manager.connect(websocket)
    session_id = str(uuid.uuid4())
    history = []

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                msg = data.get("content", "")
                language = data.get("language", "en")
                image_b64 = data.get("image")

                # Send thinking indicator
                await websocket.send_json({
                    "type": "thinking",
                    "session_id": session_id
                })

                result = await gemma_client.chat(
                    message=msg,
                    history=history,
                    image_base64=image_b64,
                    language=language
                )

                history.append({"role": "user", "content": msg})
                history.append({"role": "assistant", "content": result["message"]})
                history = history[-20:]

                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "content": result["message"],
                    "model_used": result.get("model_used", "unknown"),
                    "function_calls": result.get("function_calls", []),
                    "function_results": result.get("function_results", [])
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Chat WebSocket error: {e}")
        manager.disconnect(websocket)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ─── Static Files Catch-All (Must be at the bottom) ───────────────────────────

@app.get("/{filename:path}", include_in_schema=False)
async def serve_frontend(filename: str):
    if not filename:
        filename = "index.html"
        
    # Serve React Prototype if route starts with tracker/
    if filename.startswith("tracker/"):
        proto_filename = filename.replace("tracker/", "", 1) or "index.html"
        proto_path = os.path.join(PROTOTYPE_DIR, proto_filename)
        if os.path.exists(proto_path) and os.path.isfile(proto_path):
            return FileResponse(proto_path)
        # React SPA fallback
        proto_index = os.path.join(PROTOTYPE_DIR, "index.html")
        if os.path.exists(proto_index):
            return FileResponse(proto_index)
            
    # Serve Vanilla JS RAKSHA UI
    file_path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # SPA fallback for frontend routing
    if not filename.startswith("api/") and not filename.startswith("ws/"):
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
            
    raise HTTPException(status_code=404, detail="Not found")


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        log_level="info"
    )
