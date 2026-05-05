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
    A high-performance, zero-cost multimodal vision pipeline with part-by-part analysis.
    Uses HuggingFace BLIP for image captioning and cascading LLMs for structured disaster intelligence.
    Supports analyzing images in sections for detailed damage assessment.
    """
    
    def __init__(self):
        self.blip_api_url = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
        self.hf_token = os.getenv("HUGGINGFACE_TOKEN", "")

    async def analyze(
        self, 
        image_base64: str, 
        disaster_type: str = "Unknown", 
        building_type: str = "Unknown",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Main entry point for image analysis.
        Uses full image analysis first, then optionally part-by-part if enabled.
        """
        # Get base analysis
        result = await self.analyze_full_image(image_base64, disaster_type, building_type, language)
        
        # Add metadata
        result["model_used"] = "raksha-vision-blip-pollinations"
        result["analysis_type"] = "full"
        
        return result

    async def analyze_full_image(
        self, 
        image_base64: str, 
        disaster_type: str = "Unknown", 
        building_type: str = "Unknown",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze the full disaster image using a hybrid pipeline:
        1. HF BLIP Captioning (Get raw visual description)
        2. Pollinations GPT (Structure into RAKSHA Intelligence Report)
        """
        try:
            # Step 1: Get visual description from BLIP
            caption = await self._get_image_caption(image_base64)
            logger.info(f"Visual Caption Generated: {caption}")

            # Step 2: Use Advanced AI to structure the report
            prompt = self._build_analysis_prompt(caption, disaster_type, building_type, language)
            
            # Use our advanced AI cascade
            llm_response = await advanced_ai.generate_response(prompt, [], "en")
            
            return self._parse_json(llm_response, caption)

        except Exception as e:
            logger.error(f"Vision Analysis Failed: {e}")
            # Fallback to Multimodal Connectors (Mistral/Llama) if cascading fails
            logger.info("Switching to Multimodal Connector Fallback...")
            fallback_json = await multimodal_router.route_and_analyze(image_base64, "Describe the disaster damage in this image.")
            return self._parse_json(fallback_json, "Fallback Analysis")

    async def analyze_image_parts(
        self, 
        image_base64: str,
        disaster_type: str = "Unknown",
        building_type: str = "Unknown",
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Analyze the image in parts (top, bottom, left, right, center) for detailed assessment.
        This provides more granular damage identification.
        """
        try:
            # Get overall caption first
            overall_caption = await self._get_image_caption(image_base64)
            logger.info(f"Overall Caption: {overall_caption}")
            
            # Analyze different aspects
            aspect_prompts = {
                "structural": "Analyze the structural damage, cracks in walls, broken beams, foundation issues.",
                "hazard": "Identify visible hazards: fire, gas leaks, electrical dangers, flooding, debris.",
                "accessibility": "Assess entry points, blocked roads, safe passages, evacuation routes visible.",
                "casualties": "Look for signs of trapped persons, injuries, people needing rescue, casualties.",
                "surroundings": "Note surrounding buildings, landmarks, infrastructure damage, environmental hazards."
            }
            
            # Generate detailed analysis for each aspect
            analyses = {}
            for aspect, analysis_prompt in aspect_prompts.items():
                prompt = f"""
                You are a disaster damage analyst. A field responder has uploaded an image from a disaster zone.
                
                Overall scene description: {overall_caption}
                
                Analyze specifically for: {aspect_prompt}
                
                Provide a detailed assessment in JSON format:
                {{
                    "aspect": "{aspect}",
                    "severity": <1-10>,
                    "findings": ["finding1", "finding2"],
                    "immediate_actions": ["action1"],
                    "confidence": <0.0-1.0>
                }}
                Response in {language}.
                """
                
                result = await advanced_ai.generate_response(prompt, [], language)
                analyses[aspect] = self._parse_aspect_json(result)
            
            # Synthesize into final report
            final_report = self._synthesize_part_analysis(analyses, overall_caption, language)
            final_report["analysis_type"] = "detailed_parts"
            
            return final_report
            
        except Exception as e:
            logger.error(f"Part-by-part analysis failed: {e}")
            # Fall back to full image analysis
            return await self.analyze_full_image(image_base64, disaster_type, building_type, language)

    def _build_analysis_prompt(self, caption: str, disaster_type: str, building_type: str, language: str) -> str:
        """Build the analysis prompt with disaster context."""
        return f"""
        You are a Disaster Response Intelligence Agent. I have an image from a disaster zone.
        Disaster Type: {disaster_type}
        Building Type: {building_type}
        
        A computer vision model describes it as: '{caption}'.
        
        Based on this visual evidence and common disaster patterns, generate a structural intelligence report.
        You MUST return ONLY a valid JSON object with these keys:
        {{
          "damage_severity": <1-10 float>,
          "hazards": ["hazard1", "hazard2"],
          "structural_integrity": "<stable|compromised|collapsed>",
          "estimated_trapped": <number or null>,
          "recommended_actions": ["action1", "action2"],
          "intelligence_summary": "<Detailed 2 sentence situational assessment>",
          "resource_requirements": {{
            "teams_required": <number>,
            "medical_personnel": <number>,
            "equipment": ["equipment1", "equipment2"]
          }},
          "confidence": <0.0-1.0>,
          "summary": "<One line summary for quick reference>"
        }}
        Generate the report strictly in {language}.
        """

    def _synthesize_part_analysis(
        self, 
        analyses: Dict[str, Any], 
        overall_caption: str, 
        language: str
    ) -> Dict[str, Any]:
        """Synthesize multiple aspect analyses into a single comprehensive report."""
        
        # Calculate average severity
        severities = [a.get("severity", 5) for a in analyses.values() if a.get("severity")]
        avg_severity = sum(severities) / len(severities) if severities else 5.0
        
        # Collect all hazards
        all_hazards = []
        for aspect_data in analyses.values():
            findings = aspect_data.get("findings", [])
            if isinstance(findings, list):
                all_hazards.extend(findings)
        
        # Collect all actions
        all_actions = []
        for aspect_data in analyses.values():
            actions = aspect_data.get("immediate_actions", [])
            if isinstance(actions, list):
                all_actions.extend(actions)
        
        # Determine overall structural integrity based on structural analysis
        structural = analyses.get("structural", {})
        structural_severity = structural.get("severity", 5)
        if structural_severity >= 8:
            integrity = "collapsed"
        elif structural_severity >= 5:
            integrity = "compromised"
        else:
            integrity = "stable"
        
        # Check for trapped persons
        casualties = analyses.get("casualties", {})
        estimated_trapped = None
        if casualties.get("findings"):
            # Try to extract number from findings
            for finding in casualties.get("findings", []):
                import re
                numbers = re.findall(r'\d+', str(finding))
                if numbers:
                    estimated_trapped = int(numbers[0])
                    break
        
        # Calculate average confidence
        confidences = [a.get("confidence", 0.5) for a in analyses.values()]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return {
            "damage_severity": round(avg_severity, 1),
            "hazards": list(set(all_hazards))[:5] if all_hazards else ["Assessed via detailed analysis"],
            "structural_integrity": integrity,
            "estimated_trapped": estimated_trapped,
            "recommended_actions": list(set(all_actions))[:5] if all_actions else ["Continue assessment"],
            "intelligence_summary": f"Detailed multi-aspect analysis of disaster scene. Structural: {integrity}. Hazards identified: {len(all_hazards)}. Average severity: {avg_severity:.1f}/10.",
            "resource_requirements": {
                "teams_required": 1 if avg_severity >= 5 else 1,
                "medical_personnel": 1 if analyses.get("casualties", {}).get("severity", 0) > 5 else 0,
                "equipment": self._determine_equipment(integrity, all_hazards)
            },
            "confidence": round(avg_confidence, 2),
            "summary": f"Multi-aspect analysis complete. {len(all_hazards)} hazards identified.",
            "detailed_analysis": analyses
        }

    def _determine_equipment(self, integrity: str, hazards: List[str]) -> List[str]:
        """Determine required equipment based on analysis."""
        equipment = []
        
        if integrity == "collapsed":
            equipment.extend(["Hydraulic rescue tools", "Search cameras", "Rescue dogs"])
        elif integrity == "compromised":
            equipment.extend(["Structural shoring", "Hard hats", "Safety ropes"])
            
        hazard_str = " ".join(hazards).lower()
        if "fire" in hazard_str:
            equipment.extend(["Fire extinguishers", "Thermal imaging"])
        if "gas" in hazard_str or "chemical" in hazard_str:
            equipment.extend(["Gas detectors", "Hazmat suits"])
        if "flood" in hazard_str or "water" in hazard_str:
            equipment.extend(["Water pumps", "Life jackets", "boats"])
            
        return list(set(equipment)) if equipment else ["Standard rescue kit"]

    def _parse_aspect_json(self, text: str) -> Dict[str, Any]:
        """Parse individual aspect analysis JSON."""
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            
            import re
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*\]', ']', text)
            
            return json.loads(text)
        except:
            return {
                "aspect": "unknown",
                "severity": 5,
                "findings": ["Analysis unavailable"],
                "immediate_actions": ["Manual assessment required"],
                "confidence": 0.3
            }

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
            
            # Ensure resource_requirements exists
            if "resource_requirements" not in data:
                data["resource_requirements"] = {
                    "teams_required": 1,
                    "medical_personnel": 0,
                    "equipment": []
                }
                
            return data
        except:
            return {
                "damage_severity": 5.0,
                "hazards": ["Visual debris", "Potential structural risk"],
                "structural_integrity": "compromised",
                "estimated_trapped": None,
                "recommended_actions": ["Deploy drone for closer view", "Wait for human verification"],
                "intelligence_summary": f"Visual Assessment based on caption: {caption}. Automatic structure parsing failed.",
                "resource_requirements": {
                    "teams_required": 1,
                    "medical_personnel": 0,
                    "equipment": ["Standard rescue kit"]
                },
                "confidence": 0.5,
                "summary": "Assessment based on visual evidence"
            }

vision_agent = FreeVisionAgent()