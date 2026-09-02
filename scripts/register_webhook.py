import sys
import os
from pathlib import Path
import asyncio
import httpx

# Ensure project root directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/register_webhook.py <WEBHOOK_URL>")
        print("Example: python scripts/register_webhook.py https://api.yourdomain.com/api/v1/telegram/webhook")
        sys.exit(1)

    webhook_url = sys.argv[1]
    bot_token = settings.TELEGRAM_BOT_TOKEN
    secret_token = settings.TELEGRAM_WEBHOOK_SECRET

    if not bot_token or bot_token == "mock_bot_token":
        print("ERROR: TELEGRAM_BOT_TOKEN is not configured in .env!")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {
        "url": webhook_url,
        "secret_token": secret_token,
        "allowed_updates": ["message", "callback_query"]
    }

    print(f"Registering Telegram Webhook to: {webhook_url} ...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(url, json=payload)
        data = res.json()
        print("Response from Telegram:", data)
        if data.get("ok"):
            print("SUCCESS! Telegram Webhook has been updated.")
        else:
            print("FAILED to update Telegram Webhook.")


if __name__ == "__main__":
    asyncio.run(main())
