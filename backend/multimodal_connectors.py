import os
import json
import base64
import logging
import httpx
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger("raksha.multimodal")

# ============================================================================
# ABSTRACT BASE VISION PROVIDER
# ============================================================================

class BaseVisionProvider(ABC):
    """
    Abstract base class for all Multimodal/Vision LLM connectors.
    Ensures a standardized interface for processing images across Mistral, Llama, and Gemma.
    """
    
    def __init__(self):
        self.provider_name = "Base"
        
    @abstractmethod
    async def analyze_image(self, image_base64: str, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a base64 encoded image and return structured assessment data.
        """
        pass

    def format_base64_image(self, base64_str: str) -> str:
        """Ensure base64 string has the correct data URI prefix if needed."""
        if not base64_str.startswith("data:image"):
            # Try to guess mime type or default to jpeg
            return f"data:image/jpeg;base64,{base64_str}"
        return base64_str

# ============================================================================
# LOCAL OLLAMA VISION CONNECTOR (Llava, Llama 3.2 Vision, Pixtral)
# ============================================================================

class OllamaVisionConnector(BaseVisionProvider):
    """
    Connects to local Ollama instances running Multimodal models.
    Supports: llama3.2-vision, llava, moondream, etc.
    """
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.2-vision"):
        super().__init__()
        self.provider_name = "OllamaLocal"
        self.base_url = base_url
        self.default_model = default_model

    async def check_available_vision_models(self) -> List[str]:
        """Query Ollama for installed vision-capable models."""
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return [m.get("name") for m in models if any(v in m.get("name", "").lower() for v in ["vision", "llava", "pixtral", "moondream"])]
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama vision models: {e}")
        return []

    async def analyze_image(self, image_base64: str, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        available_models = await self.check_available_vision_models()
        model_to_use = available_models[0] if available_models else self.default_model
        
        # Ollama requires raw base64 without the data uri prefix
        raw_b64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
        
        payload = {
            "model": model_to_use,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [raw_b64]
                }
            ],
            "stream": False
        }
        
        if system_prompt:
            payload["messages"].insert(0, {"role": "system", "content": system_prompt})
            
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                result = resp.json().get("message", {}).get("content", "")
                
                return {
                    "success": True,
                    "model_used": model_to_use,
                    "provider": self.provider_name,
                    "raw_response": result
                }
        except Exception as e:
            logger.error(f"Ollama Vision API failed: {e}")
            return {"success": False, "error": str(e), "provider": self.provider_name}

# ============================================================================
# MISTRAL CLOUD API CONNECTOR (Pixtral-12b)
# ============================================================================

class MistralCloudVisionConnector(BaseVisionProvider):
    """
    Connects directly to La Plateforme (Mistral API) to utilize Pixtral for image assessment.
    """
    def __init__(self, api_key: str = None):
        super().__init__()
        self.provider_name = "MistralCloud"
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.endpoint = "https://api.mistral.ai/v1/chat/completions"
        self.model = "pixtral-12b-2409"

    async def analyze_image(self, image_base64: str, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "MISTRAL_API_KEY not configured"}
            
        formatted_image = self.format_base64_image(image_base64)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": formatted_image}}
            ]
        })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 1000
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                return {
                    "success": True,
                    "model_used": self.model,
                    "provider": self.provider_name,
                    "raw_response": data["choices"][0]["message"]["content"]
                }
        except Exception as e:
            logger.error(f"Mistral Cloud Vision API failed: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# GROQ LPU API CONNECTOR (Llama 3.2 Vision)
# ============================================================================

class GroqVisionConnector(BaseVisionProvider):
    """
    Connects to Groq's high-speed inference LPU network using Llama 3.2 Vision.
    """
    def __init__(self, api_key: str = None):
        super().__init__()
        self.provider_name = "GroqCloud"
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.endpoint = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.2-11b-vision-preview"

    async def analyze_image(self, image_base64: str, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "GROQ_API_KEY not configured"}
            
        formatted_image = self.format_base64_image(image_base64)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": formatted_image}}
            ]
        })
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(self.endpoint, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                return {
                    "success": True,
                    "model_used": self.model,
                    "provider": self.provider_name,
                    "raw_response": data["choices"][0]["message"]["content"]
                }
        except Exception as e:
            logger.error(f"Groq Vision API failed: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# MULTIMODAL ROUTER
# ============================================================================

class MultimodalRouter:
    """
    Intelligently routes image assessment requests to the best available Mistral/Llama model.
    Prioritizes Local Offline (Ollama) -> Groq (Llama 3.2) -> Mistral API (Pixtral).
    """
    def __init__(self):
        self.local_connector = OllamaVisionConnector()
        self.groq_connector = GroqVisionConnector()
        self.mistral_connector = MistralCloudVisionConnector()
        
    async def route_and_analyze(self, image_base64: str, context_prompt: str) -> str:
        """
        Attempts to route the image to the fastest/available multimodal connector.
        Returns the parsed JSON string suitable for the RAKSHA Dashboard.
        """
        system_instructions = (
            "You are an expert disaster assessment AI. Analyze the image and extract hazards, "
            "damage severity (1-10), and structural integrity. Return ONLY valid JSON format with keys: "
            "damage_severity, structural_integrity, hazards, estimated_trapped, recommended_actions."
        )

        # 1. Try Local Ollama (Highest priority for Offline Survival)
        local_result = await self.local_connector.analyze_image(image_base64, context_prompt, system_instructions)
        if local_result.get("success"):
            return local_result.get("raw_response", "")

        # 2. Try Groq Llama 3.2 Vision (Fastest Cloud)
        groq_result = await self.groq_connector.analyze_image(image_base64, context_prompt, system_instructions)
        if groq_result.get("success"):
            return groq_result.get("raw_response", "")

        # 3. Try Mistral Pixtral (Premium Cloud)
        mistral_result = await self.mistral_connector.analyze_image(image_base64, context_prompt, system_instructions)
        if mistral_result.get("success"):
            return mistral_result.get("raw_response", "")
            
        # Fallback if no models available
        return json.dumps({
            "damage_severity": 0,
            "structural_integrity": "unknown",
            "hazards": ["Error: No vision models reachable (Mistral/Llama/Local offline)"],
            "estimated_trapped": 0,
            "recommended_actions": ["Awaiting human verification", "Establish network link"]
        })

# Global singleton router
multimodal_router = MultimodalRouter()
