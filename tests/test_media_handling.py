import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from app.core.config import settings

@pytest.mark.asyncio
async def test_telegram_webhook_photo_payload(client: AsyncClient):
    """Test receiving incoming Telegram photo payload on webhook."""
    webhook_payload = {
        "update_id": 100003,
        "message": {
            "message_id": 52,
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
            "date": 1600000010,
            "caption": "Check my issue screenshot",
            "photo": [
                {"file_id": "photo_small", "file_unique_id": "u1", "width": 100, "height": 100},
                {"file_id": "photo_large", "file_unique_id": "u2", "width": 800, "height": 800}
            ]
        }
    }
    
    headers = {"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM_WEBHOOK_SECRET}
    
    with patch("app.services.telegram_service.TelegramService.download_telegram_photo", new_callable=AsyncMock) as mock_download:
        mock_download.return_value = "/uploads/test_photo.jpg"
        response = await client.post("/api/v1/telegram/webhook", json=webhook_payload, headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_download.assert_called_once_with("photo_large")

@pytest.mark.asyncio
async def test_upload_media_endpoint(client: AsyncClient):
    """Test agent file upload endpoint /api/v1/conversations/upload-media."""
    # 1. Register & login agent to get JWT token
    register_payload = {
        "email": "mediaagent@support.com",
        "password": "Password123!",
        "full_name": "Media Agent"
    }
    await client.post("/api/v1/auth/register", json=register_payload)
    login_response = await client.post("/api/v1/auth/login", json={"email": "mediaagent@support.com", "password": "Password123!"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Post file upload with auth header
    files = {"file": ("test.png", b"fake_image_bytes", "image/png")}
    response = await client.post("/api/v1/conversations/upload-media", files=files, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "media_url" in data["data"]
    assert data["data"]["media_type"] == "image"
    assert data["data"]["media_url"].startswith("/uploads/")
