import os
import json
import httpx
import logging
import base64
from typing import Dict, Any, List, Optional
from ai_core import advanced_ai
from multimodal_connectors import multimodal_router

logger = logging.getLogger("raksha.vision")

class FreeVisionAgent:
    """
    A high-performance, zero-cost multimodal vision pipeline.
    Utilizes HuggingFace BLIP for zero-cost image captioning and 
    Cascading LLMs (via Pollinations) for JSON-structured disaster intelligence.
    """
    
    def __init__(self):
        self.blip_api_url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN", "") # Optional, but helps with rate limits

    async def analyze_incident_image(self, image_base64: str, language: str = "en") -> Dict[str, Any]:
        """
        Analyze a disaster image using a hybrid pipeline:
        1. HF BLIP Captioning (Get raw visual description)
        2. Pollinations GPT (Structure into RAKSHA Intelligence Report)
        """
        try:
            # Step 1: Get visual description from BLIP
            caption = await self._get_image_caption(image_base64)
            logger.info(f"Visual Caption Generated: {caption}")

            # Step 2: Use Advanced AI to structure the report
            prompt = (
                f"You are a Disaster Response Intelligence Agent. I have an image from a disaster zone. "
                f"A computer vision model describes it as: '{caption}'.\n\n"
                f"Based on this visual evidence and common disaster patterns, generate a structural intelligence report. "
                f"You MUST return ONLY a valid JSON object with these keys:\n"
                f"{{\n"
                f"  \"damage_severity\": <1-10 float>,\n"
                f"  \"hazards\": [\"hazard1\", \"hazard2\"],\n"
                f"  \"structural_integrity\": \"<stable|compromised|collapsed>\",\n"
                f"  \"estimated_trapped\": <number or null>,\n"
                f"  \"recommended_actions\": [\"action1\", \"action2\"],\n"
                f"  \"intelligence_summary\": \"<Detailed 2 sentence situational assessment>\"\n"
                f"}}\n"
                f"Generate the report strictly in {language}."
            )

            # Use our advanced AI cascade
            llm_response = await advanced_ai.generate_response(prompt, [], "en")
            
            return self._parse_json(llm_response, caption)

        except Exception as e:
            logger.error(f"Vision Analysis Failed: {e}")
            # Fallback to Multimodal Connectors (Mistral/Llama) if cascading fails
            logger.info("Switching to Multimodal Connector Fallback...")
            fallback_json = await multimodal_router.route_and_analyze(image_base64, "Describe the disaster damage in this image.")
            return self._parse_json(fallback_json, "Fallback Analysis")

    async def _get_image_caption(self, image_base64: str) -> str:
        """Calls Salesforce/BLIP via HuggingFace Inference API"""
        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
            
        raw_b64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
        image_data = base64.b64decode(raw_b64)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    self.blip_api_url,
                    headers=headers,
                    content=image_data
                )
                if response.status_code == 200:
                    result = response.json()
                    return result[0].get("generated_text", "Image shows a disaster area.")
                return "Image showing potential disaster scene with structural damage."
        except Exception as e:
            logger.warning(f"BLIP Captioning failed: {e}")
            return "Image analysis unavailable (offline/network error)."

    def _parse_json(self, text: str, caption: str) -> Dict[str, Any]:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            
            # Clean trailing commas
            import re
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*\]', ']', text)
            
            data = json.loads(text)
            data["model_used"] = "raksha-vision-blip-pollinations"
            return data
        except:
            return {
                "damage_severity": 5.0,
                "hazards": ["Visual debris", "Potential structural risk"],
                "structural_integrity": "compromised",
                "estimated_trapped": None,
                "recommended_actions": ["Deploy drone for closer view", "Wait for human verification"],
                "intelligence_summary": f"Visual Assessment based on caption: {caption}. Automatic structure parsing failed.",
                "model_used": "raksha-vision-fallback"
            }

vision_agent = FreeVisionAgent()
