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
        """Master offline response engine for OTP & SMS verification queries when external AI APIs are unavailable."""
        lower_prompt = prompt.lower().strip()

        # Greetings
        if any(word in lower_prompt for word in ["hello", "hi", "hey", "greetings", "start"]):
            return (
                "🤖 Hello! Welcome to our SMS & OTP Verification Service. "
                "How can I assist you today? You can ask about buying numbers, OTP delays, pricing, or refunds."
            )

        # OTP Delivery / Delayed Code / Code not coming
        elif any(phrase in lower_prompt for phrase in ["otp", "code", "sms", "not receive", "delay", "waiting", "didn't get", "haven't got", "where is"]):
            return (
                "🤖 **OTP Delivery Info:** SMS codes usually arrive within 1-3 minutes. "
                "If your code has not arrived after 3 minutes, please click **Cancel** on your dashboard number order. "
                "Your balance will be instantly refunded 100%, and you can try purchasing another number or selecting a different country/server."
            )

        # Refund / Balance / Billing / Charged
        elif any(word in lower_prompt for word in ["refund", "balance", "money", "charged", "credit", "cost", "free"]):
            return (
                "🤖 **Billing & Refund Policy:** You are **only charged if an SMS code is successfully received**! "
                "If you cancel an unused number or if the timer expires without receiving an OTP, your money is automatically credited back to your account balance immediately."
            )

        # Buying / Purchasing numbers / How to use
        elif any(word in lower_prompt for word in ["buy", "purchase", "number", "how to", "get number", "service", "country"]):
            return (
                "🤖 **How to Buy a Number:**\n"
                "1. Go to the main dashboard.\n"
                "2. Select your target service (e.g. WhatsApp, Telegram, Google, Tinder, etc.) and country.\n"
                "3. Click **Buy Number**.\n"
                "4. Copy the virtual number into your app/website and request the OTP!"
            )

        # Banned or Invalid Number
        elif any(word in lower_prompt for word in ["banned", "invalid", "blocked", "used", "error"]):
            return (
                "🤖 **Invalid / Banned Number:** If the service indicates the number is already registered or banned, "
                "simply click **Cancel** on your order tab immediately to get a full refund, then purchase a fresh number."
            )

        # Pricing & Rates
        elif any(word in lower_prompt for word in ["price", "pricing", "rate", "fee"]):
            return (
                "🤖 **Pricing Details:** Rates vary depending on the chosen service and country. "
                "You can view live prices per SMS directly on the dashboard service selection menu."
            )

        # Hours / Support
        elif any(word in lower_prompt for word in ["hours", "support", "human", "agent", "person", "real"]):
            return (
                "🤖 Our live support team is available 24/7! "
                "To speak directly with a support agent, click the **'Speak to Support Agent'** button or type `/support`."
            )

        # Gratitude
        elif any(word in lower_prompt for word in ["thank", "thanks", "ok", "okay", "great"]):
            return "🤖 You're very welcome! Let me know if you have any other questions regarding your OTP orders."

        # General Fallback
        else:
            return (
                f"🤖 Thank you for your inquiry: '{prompt}'. "
                "As an SMS Support Assistant, I am here to help with your OTP orders, numbers, and balance. "
                "If you need dedicated live agent assistance, please click **'Speak to Support Agent'** or type `/support`."
            )
