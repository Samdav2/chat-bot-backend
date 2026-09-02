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

    async def download_telegram_photo(self, file_id: str) -> Optional[str]:
        """Download photo from Telegram API and save locally in public/uploads/."""
        if not file_id or self.bot_token == "mock_bot_token":
            logger.info(f"[MOCK TELEGRAM PHOTO DOWNLOAD] FileID: {file_id}")
            return f"/uploads/mock_photo_{file_id}.jpg"

        get_file_url = f"{self.api_url}/getFile?file_id={file_id}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.get(get_file_url)
                res_data = res.json()
                if not res_data.get("ok"):
                    logger.error(f"Failed to get file path from Telegram: {res_data}")
                    return None

                file_path = res_data["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
                
                img_res = await client.get(download_url)
                if img_res.status_code == 200:
                    import os, time
                    os.makedirs("public/uploads", exist_ok=True)
                    ext = os.path.splitext(file_path)[1] or ".jpg"
                    filename = f"tg_{int(time.time())}_{file_id[:8]}{ext}"
                    filepath = os.path.join("public", "uploads", filename)
                    with open(filepath, "wb") as f:
                        f.write(img_res.content)
                    return f"/uploads/{filename}"
            except Exception as e:
                logger.error(f"Error downloading photo from Telegram file_id {file_id}: {e}")
                return None
        return None

    async def send_photo(
        self,
        chat_id: int | str,
        photo_url_or_path: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send a photo asynchronously to a Telegram chat."""
        if self.bot_token == "mock_bot_token":
            logger.info(f"[MOCK TELEGRAM PHOTO OUTBOUND] ChatID: {chat_id} | Photo: {photo_url_or_path} | Caption: {caption}")
            return {"ok": True, "result": {"message_id": 9999}}

        url = f"{self.api_url}/sendPhoto"
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                import os
                clean_path = photo_url_or_path.lstrip("/")
                if os.path.exists(clean_path):
                    with open(clean_path, "rb") as photo_file:
                        files = {"photo": photo_file}
                        data = {"chat_id": str(chat_id)}
                        if caption:
                            data["caption"] = caption
                        if reply_markup:
                            import json
                            data["reply_markup"] = json.dumps(reply_markup)
                        response = await client.post(url, data=data, files=files)
                        return response.json()
                elif os.path.exists(os.path.join("public", photo_url_or_path.lstrip("/"))):
                    local_p = os.path.join("public", photo_url_or_path.lstrip("/"))
                    with open(local_p, "rb") as photo_file:
                        files = {"photo": photo_file}
                        data = {"chat_id": str(chat_id)}
                        if caption:
                            data["caption"] = caption
                        if reply_markup:
                            import json
                            data["reply_markup"] = json.dumps(reply_markup)
                        response = await client.post(url, data=data, files=files)
                        return response.json()
                else:
                    payload = {
                        "chat_id": chat_id,
                        "photo": photo_url_or_path,
                    }
                    if caption:
                        payload["caption"] = caption
                    if reply_markup:
                        payload["reply_markup"] = reply_markup
                    response = await client.post(url, json=payload)
                    return response.json()
            except Exception as e:
                logger.error(f"HTTP error sending Telegram photo to {chat_id}: {e}")
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
            f"**New Customer Support Escalation!**\n\n"
            f"**Customer:** {customer_name}\n"
            f"**Telegram ID:** `{customer_id}`\n"
            f"**Message:** _{initial_text}_\n\n"
            f"Click below to claim this support request!"
        )
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "Claim Ticket",
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
            f"**New Customer Message on Chatbot!**\n\n"
            f"**Customer Name:** {customer_name}\n"
            f"**Customer ID:** `{customer_id}`\n"
            f"**Message:** _{message_text}_\n\n"
            f"*Check dashboard to review and reply!*"
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

    async def set_webhook(self, webhook_url: str, secret_token: Optional[str] = None) -> Dict[str, Any]:
        """Register or update Telegram Bot Webhook URL with Telegram API."""
        if self.bot_token == "mock_bot_token":
            logger.info(f"[MOCK WEBHOOK SET] URL: {webhook_url}")
            return {"ok": True, "result": True, "description": "Mock webhook updated"}

        url = f"{self.api_url}/setWebhook"
        secret = secret_token or settings.TELEGRAM_WEBHOOK_SECRET
        payload = {
            "url": webhook_url,
            "secret_token": secret,
            "allowed_updates": ["message", "callback_query"]
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload)
                return response.json()
            except Exception as e:
                logger.error(f"Error setting Telegram webhook URL to {webhook_url}: {e}")
                return {"ok": False, "error": str(e)}

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Fetch current Telegram Bot Webhook status from Telegram API."""
        if self.bot_token == "mock_bot_token":
            return {"ok": True, "result": {"url": "mock_url"}}

        url = f"{self.api_url}/getWebhookInfo"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                return response.json()
            except Exception as e:
                logger.error(f"Error fetching Telegram webhook info: {e}")
                return {"ok": False, "error": str(e)}


