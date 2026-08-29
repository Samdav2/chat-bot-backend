import logging
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("service.ai")


class AIService:
    """Async AI service for generating intelligent bot chat responses using OpenAI, Gemini, or fallback logic."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.gemini_api_key = gemini_api_key or settings.GEMINI_API_KEY
        self.provider = (provider or settings.AI_PROVIDER).lower()

    async def generate_response(
        self, prompt: str, history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate AI response for user query.
        Uses OpenAI or Gemini if configured, or falls back to intelligent response engine.
        """
        if self.provider == "openai" or (self.provider == "auto" and self.openai_api_key):
            response = await self._generate_openai(prompt, history)
            if response:
                return response

        if self.provider == "gemini" or (self.provider == "auto" and self.gemini_api_key):
            response = await self._generate_gemini(prompt, history)
            if response:
                return response

        return self._generate_fallback(prompt)

    async def _generate_openai(
        self, prompt: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        if not self.openai_api_key:
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }

        messages = [{"role": "system", "content": settings.AI_SYSTEM_PROMPT}]
        if history:
            for item in history:
                role = "assistant" if item.get("role") in ["bot", "assistant", "agent"] else "user"
                messages.append({"role": role, "content": item.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"OpenAI API Error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Exception during OpenAI API call: {e}")
        return None

    async def _generate_gemini(
        self, prompt: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[str]:
        if not self.gemini_api_key:
            return None

        model = settings.GEMINI_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"

        contents = []
        if history:
            for item in history:
                role = "model" if item.get("role") in ["bot", "assistant", "agent"] else "user"
                contents.append({"role": role, "parts": [{"text": item.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "system_instruction": {"parts": [{"text": settings.AI_SYSTEM_PROMPT}]},
            "contents": contents,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
                else:
                    logger.error(f"Gemini API Error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Exception during Gemini API call: {e}")
        return None

    def _generate_fallback(self, prompt: str) -> str:
        """Intelligent conversational fallback engine when external API keys are unavailable."""
        lower_prompt = prompt.lower().strip()

        if any(word in lower_prompt for word in ["hello", "hi", "hey", "greetings"]):
            return "🤖 Hello! I am your AI assistant. How can I help you today? If you'd like to talk to a human agent, click below or type /support."
        elif any(word in lower_prompt for word in ["price", "pricing", "cost", "fee"]):
            return "🤖 Our services are competitively priced. For detailed pricing inquiries or custom plans, feel free to reach out to a support agent using the button below!"
        elif any(word in lower_prompt for word in ["hours", "open", "time", "schedule"]):
            return "🤖 Our support team is available 24/7 to assist you. Let us know how we can help!"
        elif any(word in lower_prompt for word in ["thank", "thanks"]):
            return "🤖 You're very welcome! Is there anything else I can assist you with?"
        else:
            return f"🤖 Thank you for your inquiry regarding: '{prompt}'. As an AI assistant, I'm here to help. If you need dedicated human support, please click 'Speak to Support Agent' or type /support."
