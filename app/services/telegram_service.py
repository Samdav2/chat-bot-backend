import logging
from typing import Optional, Dict, Any
import httpx
from app.core.config import settings

logger = logging.getLogger("service.telegram")


class TelegramService:
    """Async Telegram Bot API Client utilizing httpx.AsyncClient."""

    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: Optional[Dict[str, Any]] = None,
        parse_mode: str = "Markdown",
    ) -> Optional[Dict[str, Any]]:
        """Send a text message asynchronously to a Telegram chat."""
        if self.bot_token == "mock_bot_token":
            logger.info(f"[MOCK TELEGRAM OUTBOUND] ChatID: {chat_id} | Text: {text}")
            return {"ok": True, "result": {"message_id": 9999}}

        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                response_json = response.json()
                if not response_json.get("ok"):
                    logger.error(f"Telegram API error: {response_json}")
                return response_json
            except Exception as e:
                logger.error(f"HTTP error sending Telegram message to {chat_id}: {e}")
                return None

    async def answer_callback_query(
        self, callback_query_id: str, text: str, show_alert: bool = False
    ) -> bool:
        """Acknowledge a callback query from an inline button asynchronously."""
        if self.bot_token == "mock_bot_token":
            logger.info(f"[MOCK CALLBACK ANSWER] CallbackID: {callback_query_id} | Text: {text}")
            return True

        url = f"{self.api_url}/answerCallbackQuery"
        payload = {
            "callback_query_id": callback_query_id,
            "text": text,
            "show_alert": show_alert,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                return response.json().get("ok", False)
            except Exception as e:
                logger.error(f"HTTP error answering callback query {callback_query_id}: {e}")
                return False

    async def send_staff_alert(
        self, customer_id: int, customer_name: str, initial_text: str
    ) -> Optional[Dict[str, Any]]:
        """Dispatch staff notification alert to the Telegram Staff Group with a [Claim Ticket] inline button."""
        staff_group_id = settings.STAFF_GROUP_ID
        text = (
            f"🚨 **New Customer Support Escalation!**\n\n"
            f"👤 **Customer:** {customer_name}\n"
            f"🆔 **Telegram ID:** `{customer_id}`\n"
            f"💬 **Message:** _{initial_text}_\n\n"
            f"Click below to claim this support request!"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Claim Ticket",
                        "callback_data": f"claim_{customer_id}",
                    }
                ]
            ]
        }
        return await self.send_message(staff_group_id, text, reply_markup=reply_markup)

    async def send_new_message_alert(
        self,
        customer_id: int,
        customer_name: str,
        message_text: str,
        recipient_chat_ids: Optional[list[int | str]] = None,
    ) -> list[Optional[Dict[str, Any]]]:
        """
        Dispatch notification alert to admins via Telegram when a new customer sends a message to the AI Chatbot.
        Sends to recipient admin Telegram chat IDs/handles and the Staff Group.
        """
        text = (
            f"📩 **New Customer Message on Chatbot!**\n\n"
            f"👤 **Customer Name:** {customer_name}\n"
            f"🆔 **Customer ID:** `{customer_id}`\n"
            f"💬 **Message:** _{message_text}_\n\n"
            f"👉 *Check dashboard to review and reply!*"
        )

        targets = set()
        if recipient_chat_ids:
            for cid in recipient_chat_ids:
                if cid:
                    targets.add(cid)

        # Always include STAFF_GROUP_ID if configured
        if settings.STAFF_GROUP_ID:
            targets.add(settings.STAFF_GROUP_ID)

        results = []
        for chat_id in targets:
            res = await self.send_message(chat_id=chat_id, text=text)
            results.append(res)

        return results

