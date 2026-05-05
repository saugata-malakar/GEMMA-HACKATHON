import os
import json
import logging
from typing import Dict, Any, List, Optional
from ai_core import advanced_ai

logger = logging.getLogger("raksha.triage")

class WebTriageAgent:
    """
    Enhanced Medical Triage Agent with location tracking and GPS support.
    Uses our Free LLM Engine (via Pollinations) to analyze patient symptoms 
    and provide highly accurate, contextual remedies and precautions for injured individuals.
    Supports detailed location capture for mass casualty incidents.
    """
    
    async def evaluate_patient(
        self, 
        symptoms: List[str], 
        age_estimate: Optional[str] = "Unknown", 
        vitals: Dict[str, Any] = None, 
        language: str = "en",
        location: Optional[Dict[str, float]] = None,
        additional_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        
        vitals_str = json.dumps(vitals) if vitals else "Not provided"
        symptoms_str = ", ".join(symptoms)
        
        # Enhanced prompt with location awareness
        location_info = ""
        if location:
            location_info = f"""
- GPS Location: Latitude {location.get('lat', 'N/A')}, Longitude {location.get('lng', 'N/A')}
- Location Accuracy: {location.get('accuracy', 'Unknown')} meters
"""
        
        notes_info = f"\n- Additional Notes: {additional_notes}" if additional_notes else ""
        
        # Advanced System Prompt for Medical Remediation
        prompt = (
            f"You are a highly advanced emergency medical triage system with START protocol expertise. "
            f"A patient has been presented with the following condition:\n"
            f"- Age Estimate: {age_estimate}\n"
            f"- Symptoms: {symptoms_str}\n"
            f"- Vitals: {vitals_str}\n"
            f"{location_info}"
            f"{notes_info}"
            f"\nPlease evaluate this patient using START triage protocol principles and provide immediate "
            f"remedies, precautions, and a priority level. "
            f"You MUST return ONLY a valid JSON object with EXACTLY these keys:\n"
            f"{{\n"
            f"  \"triage_color\": \"<Red|Yellow|Green|Black>\",\n"
            f"  \"priority_level\": <1 to 4>,\n"
            f"  \"immediate_remedy\": [\"<step1>\", \"<step2>\"],\n"
            f"  \"precautions\": [\"<precaution1>\", \"<precaution2>\"],\n"
            f"  \"medical_summary\": \"<Detailed 2 sentence medical explanation>\",\n"
            f"  \"vital_status\": \"<normal|abnormal|critical>\",\n"
            f"  \"airway_status\": \"<clear|compromised|blocked>\",\n"
            f"  \"breathing_status\": \"<normal|rapid|difficult|absent>\",\n"
            f"  \"circulation_status\": \"<normal|weak|absent>\",\n"
            f"  \"recommended_tests\": [\"<test1>\", \"<test2>\"],\n"
            f"  \"transport_priority\": \"<immediate|urgent|delayed|ambulatory>\",\n"
            f"  \"hospital_type\": \"<trauma_center|general_hospital|field_clinic|morgue>\",\n"
            f"  \"estimated_eta_to_hospital\": \"<minutes>\"\n"
            f"}}\n"
            f"Generate this JSON strictly in {language}. "
            f"Prioritize life-saving interventions in your response."
        )
        
        # Utilize Web-connected Free LLM
        llm_response = await advanced_ai.generate_response(prompt, [], "en")
        
        return self._parse_json(llm_response, symptoms)

    async def evaluate_mass_casualty(
        self,
        patients: List[Dict[str, Any]],
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Evaluate multiple patients for mass casualty incidents.
        Returns triage categorization for all patients.
        """
        results = []
        
        for i, patient in enumerate(patients):
            symptoms = patient.get("symptoms", [])
            age = patient.get("age_estimate", "Unknown")
            vitals = patient.get("vitals", None)
            location = patient.get("location", None)
            
            eval_result = await self.evaluate_patient(
                symptoms=symptoms,
                age_estimate=age,
                vitals=vitals,
                language=language,
                location=location
            )
            
            results.append({
                "patient_index": i,
                "patient_id": patient.get("patient_id", f"P-{i+1:03d}"),
                **eval_result
            })
        
        # Calculate triage statistics
        triage_counts = {"red": 0, "yellow": 0, "green": 0, "black": 0}
        for r in results:
            color = r.get("triage_color", "yellow").lower()
            if color in triage_counts:
                triage_counts[color] += 1
        
        return {
            "total_patients": len(patients),
            "triage_statistics": triage_counts,
            "patients": results,
            "recommended_actions": self._get_mass_casualty_actions(triage_counts)
        }

    def _get_mass_casualty_actions(self, counts: Dict[str, int]) -> List[str]:
        """Generate recommended actions for mass casualty based on counts."""
        actions = []
        
        if counts.get("red", 0) > 0:
            actions.append(f"🚨 IMMEDIATE: {counts['red']} patients require immediate life-saving intervention")
        if counts.get("yellow", 0) > 0:
            actions.append(f"⚠️ URGENT: {counts['yellow']} patients need delayed treatment")
        if counts.get("green", 0) > 0:
            actions.append(f"✅ AMBULATORY: {counts['green']} patients can walk to treatment area")
        if counts.get("black", 0) > 0:
            actions.append(f"⚰️ EXPECTANT: {counts['black']} patients - provide comfort care")
        
        total_critical = counts.get("red", 0) + counts.get("yellow", 0)
        if total_critical > 5:
            actions.append("📞 MASS CASUALTY ALERT: Request additional medical teams")
        
        return actions

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
            
            # Ensure proper typing and add defaults for new fields
            return {
                "triage_color": assessment.get("triage_color", "Yellow"),
                "priority_level": assessment.get("priority_level", 2),
                "immediate_remedy": assessment.get("immediate_remedy", ["Stabilize patient", "Monitor vitals"]),
                "precautions": assessment.get("precautions", ["Do not move unless necessary", "Keep patient warm"]),
                "medical_summary": assessment.get("medical_summary", "Awaiting comprehensive human medical evaluation."),
                "vital_status": assessment.get("vital_status", "unknown"),
                "airway_status": assessment.get("airway_status", "clear"),
                "breathing_status": assessment.get("breathing_status", "normal"),
                "circulation_status": assessment.get("circulation_status", "normal"),
                "recommended_tests": assessment.get("recommended_tests", []),
                "transport_priority": assessment.get("transport_priority", "delayed"),
                "hospital_type": assessment.get("hospital_type", "general_hospital"),
                "estimated_eta_to_hospital": assessment.get("estimated_eta_to_hospital", "30"),
                "model_used": "raksha-web-triage-enhanced"
            }
        except Exception as e:
            logger.error(f"Triage JSON parse failed: {e}")
            return self._get_fallback_json(symptoms)

    def _get_fallback_json(self, symptoms: List[str]) -> Dict[str, Any]:
        """Offline fallback if web access drops during triage"""
        is_critical = any(s in ' '.join(symptoms).lower() for s in ['bleeding', 'breathing', 'unconscious', 'chest', 'no pulse'])
        is_moribund = any(s in ' '.join(symptoms).lower() for s in ['decapitated', 'decomposed', 'not breathing'])
        
        if is_moribund:
            color = "Black"
            priority = 4
        elif is_critical:
            color = "Red"
            priority = 1
        else:
            color = "Yellow"
            priority = 2
            
        return {
            "triage_color": color,
            "priority_level": priority,
            "immediate_remedy": [
                "Apply direct pressure to wounds" if 'bleeding' in ' '.join(symptoms).lower() else "Check breathing and airway",
                "Clear airway if obstructed",
                "Prepare for transport"
            ],
            "precautions": [
                "Avoid moving neck/spine unless necessary",
                "Prevent shock - keep warm and calm"
            ],
            "medical_summary": "System operating offline. Defaulting to high-priority conservative care protocols based on keyword heuristics. Manual verification strongly recommended.",
            "vital_status": "unknown",
            "airway_status": "assess_required",
            "breathing_status": "assess_required", 
            "circulation_status": "assess_required",
            "recommended_tests": ["Manual vital signs", "Physical examination"],
            "transport_priority": "immediate" if color == "Red" else "delayed",
            "hospital_type": "trauma_center" if color == "Red" else "general_hospital",
            "estimated_eta_to_hospital": "15",
            "model_used": "raksha-offline-triage-fallback"
        }

triage_agent = WebTriageAgent()