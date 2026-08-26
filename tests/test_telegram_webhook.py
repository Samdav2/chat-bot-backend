import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_telegram_webhook_bot_reply(client: AsyncClient):
    """Test receiving incoming Telegram update message on webhook."""
    webhook_payload = {
        "update_id": 100001,
        "message": {
            "message_id": 50,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Alice",
                "username": "alice_user"
            },
            "chat": {
                "id": 987654321,
                "type": "private",
                "first_name": "Alice"
            },
            "date": 1600000000,
            "text": "Hello bot"
        }
    }
    
    headers = {"X-Telegram-Bot-Api-Secret-Token": "dev_secret_token"}
    response = await client.post("/api/v1/telegram/webhook", json=webhook_payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_telegram_webhook_support_escalation(client: AsyncClient):
    """Test /support command escalation trigger via Telegram webhook."""
    webhook_payload = {
        "update_id": 100002,
        "message": {
            "message_id": 51,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "Alice",
                "username": "alice_user"
            },
            "chat": {
                "id": 987654321,
                "type": "private"
            },
            "date": 1600000005,
            "text": "/support"
        }
    }
    
    headers = {"X-Telegram-Bot-Api-Secret-Token": "dev_secret_token"}
    response = await client.post("/api/v1/telegram/webhook", json=webhook_payload, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
