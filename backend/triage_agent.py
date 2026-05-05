import os
import json
import logging
from typing import Dict, Any, List, Optional
from ai_core import advanced_ai

logger = logging.getLogger("raksha.triage")

class WebTriageAgent:
    """
    A specialized Web-connected Medical Triage Agent.
    Uses our Free LLM Engine (via Pollinations) to analyze patient symptoms 
    and provide highly accurate, contextual remedies and precautions for injured individuals.
    """
    
    async def evaluate_patient(
        self, 
        symptoms: List[str], 
        age_estimate: Optional[str] = "Unknown", 
        vitals: Dict[str, Any] = None, 
        language: str = "en"
    ) -> Dict[str, Any]:
        
        vitals_str = json.dumps(vitals) if vitals else "Not provided"
        symptoms_str = ", ".join(symptoms)
        
        # Advanced System Prompt for Medical Remediation
        prompt = (
            f"You are a highly advanced emergency medical triage system. "
            f"A patient has been presented with the following condition:\n"
            f"- Age Estimate: {age_estimate}\n"
            f"- Symptoms: {symptoms_str}\n"
            f"- Vitals: {vitals_str}\n\n"
            f"Please evaluate this patient using START triage protocol principles and provide immediate "
            f"remedies, precautions, and a priority level. "
            f"You MUST return ONLY a valid JSON object with EXACTLY these keys:\n"
            f"{{\n"
            f"  \"triage_color\": \"<Red|Yellow|Green|Black>\",\n"
            f"  \"priority_level\": <1 to 4>,\n"
            f"  \"immediate_remedy\": [\"<step1>\", \"<step2>\"],\n"
            f"  \"precautions\": [\"<precaution1>\", \"<precaution2>\"],\n"
            f"  \"medical_summary\": \"<Detailed 2 sentence medical explanation>\"\n"
            f"}}\n"
            f"Generate this JSON strictly in {language}."
        )
        
        # Utilize Web-connected Free LLM
        llm_response = await advanced_ai.generate_response(prompt, [], "en")
        
        return self._parse_json(llm_response, symptoms)

    def _parse_json(self, text: str, symptoms: List[str]) -> Dict[str, Any]:
        try:
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            
            # Clean trailing commas
            import re
            text = re.sub(r',\s*}', '}', text)
            text = re.sub(r',\s*\]', ']', text)
            
            assessment = json.loads(text)
            
            # Ensure proper typing
            return {
                "triage_color": assessment.get("triage_color", "Yellow"),
                "priority_level": assessment.get("priority_level", 2),
                "immediate_remedy": assessment.get("immediate_remedy", ["Stabilize patient", "Monitor vitals"]),
                "precautions": assessment.get("precautions", ["Do not move unless necessary", "Keep patient warm"]),
                "medical_summary": assessment.get("medical_summary", "Awaiting comprehensive human medical evaluation."),
                "model_used": "raksha-web-triage (Pollinations)"
            }
        except Exception as e:
            logger.error(f"Triage JSON parse failed: {e}")
            return self._get_fallback_json(symptoms)

    def _get_fallback_json(self, symptoms: List[str]) -> Dict[str, Any]:
        """Offline fallback if web access drops during triage"""
        is_critical = any(s in ' '.join(symptoms).lower() for s in ['bleeding', 'breathing', 'unconscious', 'chest'])
        return {
            "triage_color": "Red" if is_critical else "Yellow",
            "priority_level": 1 if is_critical else 2,
            "immediate_remedy": ["Apply direct pressure to wounds", "Clear airway if obstructed", "Prepare for transport"],
            "precautions": ["Avoid moving neck/spine", "Prevent shock"],
            "medical_summary": "System operating offline. Defaulting to high-priority conservative care protocols based on keyword heuristics.",
            "model_used": "raksha-offline-triage-fallback"
        }

triage_agent = WebTriageAgent()
