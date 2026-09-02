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
        """Master offline response engine for FAQ queries when external AI APIs are unavailable."""
        lower_prompt = prompt.lower().strip()

        # 1. How to Deposit
        if any(phrase in lower_prompt for phrase in ["how to deposit", "deposit", "top up"]):
            return (
                "Click the “Top up” button and select to pay with bank transfer or cryptocurrency, "
                "after that enter the amount you want to deposit and click the “Proceed to payment” button "
                "an account details we be generated for you to make payment to"
            )

        # 2. How to cancel order
        elif any(phrase in lower_prompt for phrase in ["how to cancel order", "cancel order", "cancel your order"]):
            return (
                "To cancel an order, watch this 1-minute video tutorial on how to cancel your order\n"
                "https://youtube.com/shorts/2ix4ZsYsl2A?si=YvcKaAqj_kD_jJrc"
            )

        # 3. Why am not receiving code / OTP delivery
        elif any(phrase in lower_prompt for phrase in ["why am not receiving code", "not receiving code", "didn't receive code", "receiving code", "where is my otp", "otp code"]):
            return (
                "Make sure you on VPN and set location to the country number you want to buy. "
                "You also have options to buy from different ID if a particular ID is not sending code or out of stock. "
                "(SMS codes usually arrive within 1-3 minutes. If code does not arrive, click Cancel for an instant refund)."
            )

        # 4. Is it compulsory to use VPN or Proxy
        elif any(phrase in lower_prompt for phrase in ["compulsory to use vpn", "vpn or proxy", "use vpn"]):
            return (
                "Yes, we recommend using a VPN or proxy when opening a foreign account to help avoid code delays and immediate suspension."
            )

        # 5. WhatsApp Business
        elif any(phrase in lower_prompt for phrase in ["whatsapp business", "wa business"]):
            return (
                "we recommend you use the normal Whatsapp not Whatsapp business if you want to open a whatsapp account to avoid immediate suspesion"
            )

        # 6. Refund to bank account
        elif any(phrase in lower_prompt for phrase in ["refund to my bank", "bank account", "refund to bank"]):
            return (
                "As outlined in our Terms of Service, refund to bank account is non-refundable which you agree to when signing up, "
                "For more details, please refer to our Terms of Service here —> https://falconotp.com/tos"
            )

        # 7. Payment rejected
        elif any(phrase in lower_prompt for phrase in ["payment been rejected", "payment rejected"]):
            return (
                "Make sure you transfer the exact amount you see on the payment page, Do not send more or less than the specified amount."
            )

        # 8. Refund if number doesn't receive code
        elif any(phrase in lower_prompt for phrase in ["doesn't receive code", "number i bought", "refund policy"]):
            return (
                "Yes! Just Cancel the number, the money we be automatically refund to your balance. "
                "(You are only charged if an SMS code is successfully received)."
            )

        # 9. Are refunds available
        elif any(phrase in lower_prompt for phrase in ["are refunds available", "refunds available"]):
            return (
                "Absolutely! We have a simple rule: If you buy a number but the SMS never arrives, "
                "the system automatically refunds the money to your balance. You only pay for actual results."
            )

        # Buying / Purchasing numbers
        elif any(word in lower_prompt for word in ["buy", "purchase", "how to buy"]):
            return (
                "**How to Buy a Number:**\n"
                "1. Go to the main dashboard.\n"
                "2. Select your target service (e.g. WhatsApp, Telegram, Google, etc.) and country.\n"
                "3. Click **Buy Number**."
            )

        # Hours / Live Support
        elif any(word in lower_prompt for word in ["hours", "support", "human", "agent", "person", "real"]):
            return (
                "Our live support team is available 24/7! "
                "To speak directly with a support agent, click **Other question** or type `/support`."
            )

        # Greetings
        elif any(word in lower_prompt for word in ["hello", "hi", "hey", "greetings", "start"]):
            return (
                "Hello! Welcome to our SMS & OTP Verification Service. "
                "Type /command to view our list of FAQ commands, or click 'Other question' to speak directly with customer support."
            )

        # Gratitude
        elif any(word in lower_prompt for word in ["thank", "thanks", "ok", "okay", "great"]):
            return "You're very welcome! Let me know if you have any other questions regarding your OTP orders."

        # General Fallback
        else:
            return (
                f"Thank you for your inquiry: '{prompt}'. "
                "Type /command to see all FAQ options, or click **Other question** to speak directly with customer support."
            )
