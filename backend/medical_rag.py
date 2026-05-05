import os
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("raksha.medrag")

class MedicalRAG:
    """
    Medical RAG using FAISS and local embeddings.
    Retrieves context from offline clinical protocols, FHIR patient histories, and triage guidelines.
    """
    def __init__(self, db_path: str = "./med_faiss_index"):
        self.db_path = db_path
        self._index = None
        self._encoder = None
        self._documents = []
        self._initialized = False

    async def initialize(self):
        """Initialize FAISS index and local MedSigLIP/SentenceTransformer encoder."""
        if self._initialized:
            return
            
        try:
            # Native Python keyword matching (No faiss required)
            self._documents = [
                {"id": "doc_1", "text": "START Triage: Red (Immediate) if respiration > 30, capillary refill > 2s, or unable to follow simple commands."},
                {"id": "doc_2", "text": "Dosage protocol for severe bleeding: Apply tourniquet 2-3 inches above wound. Administer Tranexamic Acid (TXA) 1g IV over 10 mins if within 3 hours of injury."},
                {"id": "doc_3", "text": "FHIR Protocol: For pediatric patients (<12 yrs or <36kg), fluid resuscitation is 20 mL/kg isotonic crystalloid bolus."},
                {"id": "doc_4", "text": "Dermatology / Triage: Rapidly spreading rash with hypotension suggests anaphylaxis. Administer Epinephrine 0.3mg IM immediately."},
                {"id": "doc_5", "text": "Radiology Protocol: Suspected tension pneumothorax requires immediate needle decompression at 2nd intercostal space, midclavicular line before chest tube."},
                {"id": "doc_6", "text": "CPR Protocol: 30 compressions to 2 rescue breaths. Push hard and fast in the center of the chest."},
                {"id": "doc_7", "text": "Burn Protocol: Cool the burn with running water for 20 minutes. Do not apply ice. Cover with sterile non-fluffy dressing."},
                {"id": "doc_8", "text": "Earthquake Protocol: Drop, Cover, and Hold On. Stay away from windows and outside walls."},
            ]
            
            self._initialized = True
            logger.info("✅ Medical RAG initialized with native keyword retrieval (No external dependencies).")
            
        except Exception as e:
            logger.error(f"Failed to initialize MedicalRAG: {e}")
            self._initialized = False

    async def retrieve(self, query: str, top_k: int = 2) -> List[Dict]:
        """Retrieve most relevant medical protocols using keyword matching."""
        if not self._initialized:
            return []
            
        # Simple native BM25/keyword scoring
        query_words = set(query.lower().split())
        scored_docs = []
        
        for doc in self._documents:
            doc_words = set(doc["text"].lower().split())
            score = len(query_words.intersection(doc_words))
            scored_docs.append((score, doc))
            
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, doc in scored_docs[:top_k]:
            if score >= 0: # Return even loose matches as fallback context
                results.append({
                    "score": float(score),
                    "content": doc["text"],
                    "source": "Local_Protocol_DB"
                })
        return results

    def parse_fhir_history(self, fhir_json: dict) -> str:
        """Process longitudinal EHR data (FHIR format) into context."""
        try:
            # Simplified FHIR patient bundle extraction
            conditions = []
            medications = []
            
            for entry in fhir_json.get("entry", []):
                resource = entry.get("resource", {})
                rtype = resource.get("resourceType")
                
                if rtype == "Condition":
                    cond = resource.get("code", {}).get("text", "Unknown condition")
                    conditions.append(cond)
                elif rtype == "MedicationStatement":
                    med = resource.get("medicationCodeableConcept", {}).get("text", "Unknown medication")
                    medications.append(med)
                    
            history = ""
            if conditions: history += f"Existing Conditions: {', '.join(conditions)}. "
            if medications: history += f"Current Medications: {', '.join(medications)}. "
            
            return history.strip()
        except Exception:
            return "No valid FHIR history found."

# Singleton instance
med_rag = MedicalRAG()
