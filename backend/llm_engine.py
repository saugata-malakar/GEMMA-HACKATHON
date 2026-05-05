import json
import urllib.request
import urllib.parse
import logging
from typing import List, Dict

logger = logging.getLogger("raksha.llm")

class FreeLLMEngine:
    """
    A powerful fallback LLM engine that uses free, open AI APIs (like Pollinations.ai)
    to provide a true conversational LLM experience without needing API keys.
    """
    def __init__(self):
        # Pollinations text generation API is free, requires no key, and supports GPT-like text generation
        self.api_url = "https://text.pollinations.ai/"

    async def generate_response(self, system_prompt: str, history: List[Dict], user_message: str) -> str:
        try:
            # Build the conversation payload
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent history (last 6 messages to keep context window reasonable)
            for msg in history[-6:]:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
                
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Use urllib to send a POST request
            data = json.dumps({"messages": messages, "model": "openai"}).encode("utf-8")
            req = urllib.request.Request(
                self.api_url, 
                data=data, 
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "RakshaAI/1.0"
                },
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                result_text = response.read().decode('utf-8')
                
            if result_text:
                return result_text
            else:
                raise ValueError("Empty response from LLM API")
                
        except Exception as e:
            logger.error(f"FreeLLMEngine failed: {e}")
            return None

# Singleton instance
free_llm = FreeLLMEngine()
