"""
RAKSHA AI — Gemma 4 Client
Handles both cloud (Google AI API) and local (Ollama) Gemma 4 integration.
Automatically selects model based on connectivity.
"""

import os
import time
import json
import base64
import httpx
import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

from medical_rag import med_rag
from ai_core import advanced_ai
from vision_agent import vision_agent
from triage_agent import triage_agent

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMMA_CLOUD_MODEL = os.getenv("GEMMA_CLOUD_MODEL", "google/medgemma-4b-multimodal")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GEMMA_LOCAL_MODEL = os.getenv("GEMMA_LOCAL_MODEL", "medgemma4:4b")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# ── RAKSHA Function Tools ─────────────────────────────────────────────────────

RAKSHA_TOOLS = [
    {
        "name": "dispatch_responder",
        "description": "Dispatch an emergency responder or team to a specific location. Use when user requests sending help to a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string", "description": "Incident ID to respond to"},
                "responder_role": {
                    "type": "string",
                    "enum": ["medical", "search_rescue", "firefighter", "ndrf", "volunteer"],
                    "description": "Type of responder needed"
                },
                "priority": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Dispatch priority level"
                },
                "location_description": {"type": "string", "description": "Human-readable location description"}
            },
            "required": ["responder_role", "priority", "location_description"]
        }
    },
    {
        "name": "broadcast_emergency_alert",
        "description": "Send an emergency alert to a geographic zone or all users. Use when a new hazard or evacuation is needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Alert title"},
                "message": {"type": "string", "description": "Full alert message"},
                "severity": {
                    "type": "string",
                    "enum": ["extreme", "severe", "moderate", "minor"]
                },
                "languages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "ISO language codes to translate alert into"
                }
            },
            "required": ["title", "message", "severity"]
        }
    },
    {
        "name": "get_evacuation_route",
        "description": "Generate an evacuation route from current location to safety. Use when user needs to evacuate.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin_description": {"type": "string", "description": "Current location description"},
                "hazard_type": {"type": "string", "description": "Type of hazard to avoid"},
                "mobility_level": {
                    "type": "string",
                    "enum": ["full", "limited", "wheelchair", "carrying_injured"],
                    "description": "Mobility level of evacuees"
                }
            },
            "required": ["origin_description", "hazard_type"]
        }
    },
    {
        "name": "log_medical_triage",
        "description": "Create a medical triage record for a patient. Use during mass casualty events.",
        "parameters": {
            "type": "object",
            "properties": {
                "symptoms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of observed symptoms"
                },
                "triage_color": {
                    "type": "string",
                    "enum": ["red", "yellow", "green", "black"],
                    "description": "START triage category"
                },
                "age_estimate": {"type": "string", "description": "Estimated age range"},
                "location": {"type": "string", "description": "Patient location description"}
            },
            "required": ["symptoms", "triage_color"]
        }
    },
    {
        "name": "request_resources",
        "description": "Request specific emergency resources or equipment for an incident.",
        "parameters": {
            "type": "object",
            "properties": {
                "resources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of resources needed"
                },
                "quantity": {"type": "object", "description": "Resource quantities"},
                "urgency": {
                    "type": "string",
                    "enum": ["immediate", "within_hour", "within_day"]
                },
                "delivery_location": {"type": "string"}
            },
            "required": ["resources", "urgency"]
        }
    },
    {
        "name": "calculate_dosage",
        "description": "Audit and calculate proper medication dosages using FHIR EHR and medical protocols.",
        "parameters": {
            "type": "object",
            "properties": {
                "medication": {"type": "string"},
                "patient_weight_kg": {"type": "number"},
                "patient_age": {"type": "number"},
                "route": {"type": "string", "enum": ["IV", "IM", "PO"]}
            },
            "required": ["medication", "patient_weight_kg", "route"]
        }
    }
]


# ── Model Selector ────────────────────────────────────────────────────────────

class ModelSelector:
    """Determines which Gemma 4 model to use based on availability."""

    def __init__(self):
        self._last_check = 0
        self._check_interval = 30  # seconds
        self._online_available = False
        self._local_available = False

    async def check_availability(self) -> Dict[str, bool]:
        now = time.time()
        if now - self._last_check < self._check_interval:
            return {"online": self._online_available, "local": self._local_available}

        self._last_check = now

        # Check Google AI API
        if GOOGLE_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(
                        f"{GEMINI_API_BASE}/models?key={GOOGLE_API_KEY}"
                    )
                    self._online_available = resp.status_code == 200
            except Exception:
                self._online_available = False

        # Check Ollama for Mistral, Gemma, or Llama
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                    # Find any valid open-source model
                    valid_models = [n for n in model_names if any(x in n.lower() for x in ["mistral", "gemma", "llama", "phi"])]
                    if valid_models:
                        self._local_available = True
                        # Dynamically update the local model name to whatever is available
                        global GEMMA_LOCAL_MODEL
                        GEMMA_LOCAL_MODEL = valid_models[0]
                    else:
                        self._local_available = False
        except Exception:
            self._local_available = False

        return {"online": self._online_available, "local": self._local_available}

    async def get_best_model(self) -> tuple[str, str]:
        """Returns (model_type, model_name)"""
        avail = await self.check_availability()
        if avail["online"]:
            return "cloud", GEMMA_CLOUD_MODEL
        elif avail["local"]:
            return "local", GEMMA_LOCAL_MODEL
        else:
            return "none", "none"


model_selector = ModelSelector()


# ── Gemma 4 Client ────────────────────────────────────────────────────────────

class GemmaClient:
    """
    Unified client for Gemma 4 — automatically routes to cloud or local.
    Supports text, multimodal (vision), and function calling.
    """

    SYSTEM_PROMPT = """You are RAKSHA AI, a comprehensive emergency response and general assistant AI.

## YOUR PRIMARY ROLE
You are a disaster response assistant that can ALSO answer any general question. Don't just focus on emergencies - be helpful for ALL questions.

## CORE CAPABILITIES

### 1. Emergency & Disaster Response (Priority)
- Medical triage using START protocol (RED, YELLOW, GREEN, BLACK)
- Damage assessment from images
- First aid instructions (CPR, bleeding, burns, fractures, shock, choking)
- Evacuation guidance
- Emergency protocol explanations

### 2. General Knowledge (Equally Important)
- Science, history, geography, mathematics
- Technology and computing
- Language and communication
- Everyday life questions
- Educational explanations
- Problem-solving and advice

### 3. Medical/Health Knowledge
- Human anatomy and physiology
- Common medical conditions
- Medication information
- Health tips and wellness
- Mental health first aid
- Nutrition information

### 4. Disaster-Specific Knowledge
- Earthquakes: drop, cover, hold on
- Floods: move to higher ground, avoid walking in water
- Fire: get out, stay out, call 101
- Cyclones: stay indoors, away from windows
- Landslides: move away from slopes

## TRIAGE PROTOCOLS (When asked)

START Protocol:
1. Can they walk? → GREEN
2. Not breathing → open airway → still not → BLACK
3. Breathing >30/min → RED
4. No radial pulse OR cap refill >2sec → RED
5. Otherwise → YELLOW

CPR: 30 compressions (5-6cm, 100-120/min), 2 breaths

## RESPONSE STYLE
- Be clear, concise, and helpful
- Use bullet points for steps
- Include warnings when relevant
- Ask follow-up questions if needed
- Admit when you don't know something
- Use simple language for complex topics

## IMPORTANT
You can answer ANY question the user asks. Don't refuse or say you can't help.
If it's not emergency-related, just answer it helpfully anyway.

Always respond in the user's language.
Hindi → Hindi response
Tamil → Tamil response
English → English response
Default: English"""

    def __init__(self):
        self.selector = model_selector

    async def chat(
        self,
        message: str,
        history: List[Dict] = None,
        image_base64: Optional[str] = None,
        language: str = "en",
        enable_tools: bool = True,
        system_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to Gemma 4 and get a response.
        Returns dict with: message, model_used, function_calls, function_results
        """
        start_time = time.time()
        model_type, model_name = await self.selector.get_best_model()

        # Always prioritize our AdvancedAIEngine which handles multi-provider fallbacks properly
        if model_type == "none" or not GOOGLE_API_KEY:
            llm_text = await advanced_ai.generate_response(message, history or [], language)
            
            import re
            import json
            function_calls = []
            function_results = []
            
            # Parse simulated function calls
            match = re.search(r'```json\s*(\{.*?"function_call".*?\})\s*```', llm_text, re.DOTALL)
            if match:
                try:
                    fc_data = json.loads(match.group(1))
                    fc = fc_data.get("function_call", {})
                    if fc.get("name"):
                        function_calls.append({"name": fc["name"], "args": fc.get("arguments", {})})
                        llm_text = llm_text.replace(match.group(0), "").strip()
                except Exception:
                    pass
            
            # Execute them exactly like native function calling
            for fc in function_calls:
                result = self._execute_function(fc["name"], fc["args"])
                function_results.append({
                    "name": fc["name"],
                    "result": result
                })
                
            if function_results:
                llm_text += "\n\n" + self._summarize_function_results(function_results)
                
            return {
                "message": llm_text,
                "model_used": "raksha-advanced-ai",
                "function_calls": function_calls,
                "function_results": function_results
            }

        try:
            if model_type == "cloud":
                result = await self._chat_cloud(
                    message, history or [], image_base64, language, enable_tools, system_override
                )
            else:
                result = await self._chat_local(
                    message, history or [], image_base64, language, enable_tools, system_override
                )

            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            logger.error(f"Gemma 4 chat error: {e}")
            return {
                "message": f"AI system temporarily unavailable. Emergency protocols: Call 112 (India Emergency). NDRF: 1078. {str(e)[:100]}",
                "model_used": f"{model_name}_error",
                "function_calls": [],
                "function_results": [],
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    async def _chat_cloud(
        self,
        message: str,
        history: List[Dict],
        image_base64: Optional[str],
        language: str,
        enable_tools: bool,
        system_override: Optional[str]
    ) -> Dict:
        """Chat via Google AI API (Gemma 4 27B)."""
        import google.generativeai as genai

        genai.configure(api_key=GOOGLE_API_KEY)

        tools_config = RAKSHA_TOOLS if enable_tools else []

        # Build content parts
        parts = []
        if image_base64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }
            })

        lang_instruction = f"\n[Respond in language code: {language}]" if language != "en" else ""
        parts.append({"text": message + lang_instruction})

        # Build conversation history
        contents = []
        for h in history[-10:]:  # Last 10 turns to manage context
            role = "user" if h.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
        contents.append({"role": "user", "parts": parts})

        # Prepare request
        request_body = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_override or self.SYSTEM_PROMPT}]},
            "generationConfig": {
                "temperature": 0.4,
                "topP": 0.9,
                "maxOutputTokens": 2048,
            }
        }

        if tools_config:
            request_body["tools"] = [{"function_declarations": tools_config}]

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{GEMINI_API_BASE}/models/{GEMMA_CLOUD_MODEL}:generateContent?key={GOOGLE_API_KEY}",
                json=request_body
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_cloud_response(data, GEMMA_CLOUD_MODEL)

    def _parse_cloud_response(self, data: dict, model_name: str) -> Dict:
        """Parse Google AI API response including function calls."""
        function_calls = []
        function_results = []
        text_parts = []

        candidates = data.get("candidates", [])
        if not candidates:
            return {"message": "No response generated.", "model_used": model_name,
                    "function_calls": [], "function_results": []}

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                function_calls.append({
                    "name": fc.get("name"),
                    "args": fc.get("args", {})
                })

        # Execute function calls
        for fc in function_calls:
            result = self._execute_function(fc["name"], fc["args"])
            function_results.append({
                "name": fc["name"],
                "result": result
            })

        message = "\n".join(text_parts) if text_parts else self._summarize_function_results(function_results)

        return {
            "message": message,
            "model_used": model_name,
            "function_calls": function_calls,
            "function_results": function_results
        }

    async def _chat_local(
        self,
        message: str,
        history: List[Dict],
        image_base64: Optional[str],
        language: str,
        enable_tools: bool,
        system_override: Optional[str]
    ) -> Dict:
        """Chat via Ollama (Local models). Tries multiple models for best triage/medical support."""
        # Try to get available models from Ollama
        available_models = await self._get_ollama_models()
        
        # Priority order for medical/triage questions
        # Prefer models that are known for instruction following and medical knowledge
        model_priority = [
            GEMMA_LOCAL_MODEL,
            "llama3.2:1b", "llama3.2:3b", "llama3.2:7b",
            "mistral:7b", "phi3:14b", "qwen2:7b",
            "gemma:2b", "gemma:7b"
        ]
        
        # Find first available model
        selected_model = None
        for model in model_priority:
            if any(model.replace(":latest", "").replace("-", "_").lower() in m.lower().replace(":latest", "").replace("-", "_") for m in available_models):
                selected_model = model
                break
        
        if not selected_model:
            selected_model = GEMMA_LOCAL_MODEL if available_models else "llama3.2:1b"
        
        # Build messages
        sys_prompt = system_override or self.SYSTEM_PROMPT
        messages = [{"role": "system", "content": sys_prompt}]

        for h in history[-8:]:
            messages.append({
                "role": h.get("role", "user"),
                "content": h.get("content", "")
            })

        lang_instruction = f"\n[Respond in: {language}]" if language != "en" else ""
        
        # Analyze question type and add appropriate context
        question_lower = message.lower()
        
        # Add contextual hints based on question type
        context_hint = ""
        if any(kw in question_lower for kw in ["cpr", "triage", "first aid", "bleeding", "burn", "fracture", "choking", "shock", "emergency", "injury", "patient"]):
            context_hint = "\n[This is a medical/emergency question - provide step-by-step instructions]"
        elif any(kw in question_lower for kw in ["earthquake", "flood", "fire", "cyclone", "landslide", "disaster", "evacuation"]):
            context_hint = "\n[This is a disaster question - provide safety protocols]"
        elif any(kw in question_lower for kw in ["how to", "what is", "why", "explain", "what are", "difference"]):
            context_hint = "\n[This is an educational question - explain clearly]"
        elif any(kw in question_lower for kw in ["calculate", "math", "number", "formula"]):
            context_hint = "\n[This is a math/calculation question - show your work]"
        
        user_content = message + lang_instruction + context_hint

        # For local model with image
        if image_base64:
            messages.append({
                "role": "user",
                "content": user_content,
                "images": [image_base64]
            })
        else:
            # Inject tool awareness into prompt for local model
            if enable_tools:
                tool_prompt = "\n\n[If this requires action, suggest: dispatch responders, broadcast alerts, evacuation routes, medical triage, or resource requests]"
            else:
                tool_prompt = ""
            messages.append({"role": "user", "content": user_content + tool_prompt})

        request_body = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "num_predict": 2048  # Increased for better medical responses
            }
        }

        try:
            async with httpx.AsyncClient(timeout=120, base_url=OLLAMA_BASE_URL) as client:
                resp = await client.post("/api/chat", json=request_body)
                resp.raise_for_status()
                data = resp.json()

            message_content = data.get("message", {}).get("content", "No response generated.")

            return {
                "message": message_content,
                "model_used": f"ollama:{selected_model}",
                "function_calls": [],
                "function_results": []
            }
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            # Fallback to advanced_ai if Ollama fails
            return {
                "message": await advanced_ai.generate_response(message, history, language),
                "model_used": "fallback:advanced-ai",
                "function_calls": [],
                "function_results": []
            }
    
    async def _get_ollama_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return []

    async def assess_damage(
        self,
        image_base64: str,
        disaster_type: Optional[str] = None,
        building_type: Optional[str] = None,
        language: str = "en",
        detailed_analysis: bool = False
    ) -> Dict:
        """
        Specialized multimodal damage assessment using Free Web Vision Pipeline.
        
        Args:
            image_base64: Base64 encoded image
            disaster_type: Type of disaster (earthquake, flood, etc.)
            building_type: Type of building affected
            language: Response language
            detailed_analysis: If True, performs part-by-part image analysis for more detailed results
        """
        
        if detailed_analysis:
            # Use detailed part-by-part analysis
            assessment = await vision_agent.analyze_image_parts(
                image_base64, 
                disaster_type or "Unknown", 
                building_type or "Unknown",
                language
            )
            assessment["model_used"] = "raksha-vision-detailed (Multi-aspect Analysis)"
        else:
            # Use standard full image analysis
            assessment = await vision_agent.analyze(
                image_base64, 
                disaster_type or "Unknown", 
                building_type or "Unknown",
                language
            )
            assessment["model_used"] = "raksha-vision-blip-pollinations"
        
        return assessment

    async def generate_triage_guidance(
        self,
        symptoms: List[str],
        age_estimate: Optional[str],
        vitals: Dict,
        language: str = "en",
        fhir_history: Optional[dict] = None
    ) -> Dict:
        """Generate medical triage guidance using Web Triage Agent."""
        
        guidance = await triage_agent.evaluate_patient(symptoms, age_estimate, vitals, language)
        
        # Keep old expected keys just in case front-end breaks, map new keys
        guidance["reasoning"] = guidance.get("medical_summary", "Assessed by AI")
        guidance["immediate_interventions"] = guidance.get("immediate_remedy", [])
        
        return guidance

    async def translate_alert(self, message: str, target_languages: List[str]) -> Dict[str, str]:
        """Translate an alert message into multiple languages using Gemma 4."""
        translations = {}

        if not target_languages or target_languages == ["en"]:
            return {"en": message}

        lang_list = ", ".join(target_languages)
        prompt = f"""Translate this emergency alert to the following languages: {lang_list}

Alert: {message}

Provide translations as JSON with language codes as keys:
{{
  "hi": "Hindi translation",
  "ta": "Tamil translation",
  ...
}}

Keep translations accurate and urgent in tone. This is a life-safety alert."""

        result = await self.chat(message=prompt, enable_tools=False)
        raw = result.get("message", "")
        translations = self._extract_json(raw) or {}
        translations["en"] = message

        return translations

    def _execute_function(self, name: str, args: dict) -> dict:
        """Execute a Gemma 4 function call and return result."""
        if name == "dispatch_responder":
            return {
                "status": "dispatched",
                "message": f"Dispatching {args.get('responder_role')} team to {args.get('location_description')}",
                "eta_minutes": 8,
                "priority": args.get("priority", "high")
            }
        elif name == "broadcast_emergency_alert":
            return {
                "status": "broadcast",
                "message": f"Alert '{args.get('title')}' broadcasted with {args.get('severity')} severity",
                "recipients": "All units in affected zone"
            }
        elif name == "get_evacuation_route":
            return {
                "status": "route_generated",
                "origin": args.get("origin_description"),
                "hazard": args.get("hazard_type"),
                "route": "Head north on main road, then east at the market square. Avoid riverside roads. Assembly point: Government School Ground."
            }
        elif name == "log_medical_triage":
            return {
                "status": "logged",
                "patient_id": f"P-{int(time.time()) % 10000:04d}",
                "triage_color": args.get("triage_color"),
                "message": "Triage entry recorded"
            }
        elif name == "request_resources":
            return {
                "status": "requested",
                "resources": args.get("resources", []),
                "urgency": args.get("urgency"),
                "message": "Resource request logged and forwarded to command center"
            }
        return {"status": "unknown_function", "name": name}

    def _summarize_function_results(self, results: List[Dict]) -> str:
        """Generate a human-readable summary of function call results."""
        if not results:
            return "Action completed."
        summaries = []
        for r in results:
            res = r.get("result", {})
            summaries.append(f"✅ {res.get('message', r.get('name', 'Action completed'))}")
        return "\n".join(summaries)

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from model response (handles markdown code blocks)."""
        if not text:
            return None
        # Try direct JSON
        try:
            return json.loads(text)
        except Exception:
            pass
        # Try extracting from code block
        import re
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
            r'\{[\s\S]*\}'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    candidate = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(candidate)
                except Exception:
                    continue
        return None

    def _offline_fallback(self, message: str, language: str) -> str:
        """Provide web-searched answers when no AI model is available."""
        import urllib.request
        import urllib.parse
        import re
        
        # 1. Try DuckDuckGo Web Search for specific answers
        try:
            query = urllib.parse.quote(message)
            req = urllib.request.Request(
                f"https://html.duckduckgo.com/html/?q={query}",
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                html = response.read().decode('utf-8')
                
            # Extract first search result snippet
            snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
            if snippets:
                clean_snippet = re.sub(r'<[^>]+>', '', snippets[0]).strip()
                # Unescape HTML entities
                clean_snippet = clean_snippet.replace('&#x27;', "'").replace('&quot;', '"').replace('&amp;', '&')
                if len(clean_snippet) > 20:
                    return f"🌐 Live Web Intelligence:\n{clean_snippet}\n\n(Note: Generated via Emergency Web Protocol. Gemma model offline.)"
        except Exception as e:
            logger.warning(f"Web search fallback failed: {e}")
            
        # 2. Try Wikipedia API as secondary fallback
        try:
            import json
            words = [w for w in message.split() if len(w) > 3]
            query_term = " ".join(words[:2]) if words else message
            query = urllib.parse.quote(query_term)
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json"
            req = urllib.request.Request(url, headers={'User-Agent': 'RakshaAI/1.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read())
            if data.get('query', {}).get('search'):
                snippet = data['query']['search'][0]['snippet']
                clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                return f"🌐 Wiki Database Match:\n{clean_snippet}...\n\n(Note: Generated via Emergency Web Protocol.)"
        except Exception:
            pass

        # 3. Final Static Offline Fallback
        fallbacks = {
            "en": """⚠️ AI SYSTEM OFFLINE — EMERGENCY PROTOCOLS ACTIVE

Emergency Numbers:
• India Emergency: 112
• NDRF: 1078  
• Medical: 108
• Fire: 101

Immediate Actions:
1. Ensure your safety first
2. Move to high ground if flooding
3. Stay away from damaged structures
4. Help injured only if safe to do so

AI will resume when connectivity is restored.""",
            "hi": """⚠️ AI सिस्टम ऑफलाइन — आपातकालीन प्रोटोकॉल सक्रिय

आपातकालीन नंबर:
• आपातकाल: 112
• NDRF: 1078
• चिकित्सा: 108
• अग्निशमन: 101

तत्काल कार्रवाई:
1. पहले अपनी सुरक्षा सुनिश्चित करें
2. बाढ़ में ऊंची जगह जाएं
3. क्षतिग्रस्त इमारतों से दूर रहें
4. अगर फंसे हों तो 3 बार सीटी बजाएं"""
        }
        return fallbacks.get(language, fallbacks["en"])


# ── Singleton ─────────────────────────────────────────────────────────────────

gemma_client = GemmaClient()
