import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent import Agent
from app.repositories.agent_repository import AgentRepository
from app.services.conversation_service import ConversationService
from app.services.telegram_service import TelegramService


@pytest.mark.asyncio
async def test_agent_telegram_profile_update(client: AsyncClient, db_session: AsyncSession):
    """Test updating agent profile with telegram_chat_id and telegram_username via PUT /api/v1/auth/me."""
    # Register agent
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "telegram_admin@example.com",
            "password": "Password123!",
            "full_name": "Telegram Admin",
            "telegram_chat_id": "987654321",
            "telegram_username": "@admin_tg",
        },
    )
    assert reg_response.status_code == 200
    reg_data = reg_response.json()["data"]
    assert reg_data["telegram_chat_id"] == "987654321"
    assert reg_data["telegram_username"] == "@admin_tg"

    # Login agent
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "telegram_admin@example.com", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Update profile with new telegram_chat_id
    update_response = await client.put(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "full_name": "Updated Admin Name",
            "telegram_chat_id": "1122334455",
            "telegram_username": "@updated_handle",
        },
    )
    assert update_response.status_code == 200
    updated_data = update_response.json()["data"]
    assert updated_data["full_name"] == "Updated Admin Name"
    assert updated_data["telegram_chat_id"] == "1122334455"
    assert updated_data["telegram_username"] == "@updated_handle"

    # Verify GET /me returns updated details
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["telegram_chat_id"] == "1122334455"


@pytest.mark.asyncio
async def test_get_agents_with_telegram(db_session: AsyncSession):
    """Test querying agents with configured telegram details."""
    agent_repo = AgentRepository(db_session)
    agent1 = Agent(
        email="tg_agent1@test.com",
        hashed_password="hash",
        full_name="Agent One",
        telegram_chat_id="12345",
    )
    agent2 = Agent(
        email="no_tg_agent@test.com",
        hashed_password="hash",
        full_name="Agent Two",
    )
    await agent_repo.create(agent1)
    await agent_repo.create(agent2)

    agents_with_tg = await agent_repo.get_agents_with_telegram()
    tg_emails = [a.email for a in agents_with_tg]
    assert "tg_agent1@test.com" in tg_emails
    assert "no_tg_agent@test.com" not in tg_emails


@pytest.mark.asyncio
async def test_send_new_message_alert():
    """Test dispatching new customer message alert via TelegramService."""
    service = TelegramService(bot_token="mock_bot_token")
    results = await service.send_new_message_alert(
        customer_id=999888,
        customer_name="John Doe",
        message_text="Hello, I have a question about pricing!",
        recipient_chat_ids=["123456789", "@admin_handle"],
    )
    assert len(results) >= 2
    for r in results:
        assert r.get("ok") is True


@pytest.mark.asyncio
async def test_route_user_message_triggers_admin_alert(db_session: AsyncSession):
    """Test that customer message to AI Chatbot triggers Telegram notification to configured admins."""
    agent_repo = AgentRepository(db_session)
    admin = Agent(
        email="notified_admin@test.com",
        hashed_password="hash",
        full_name="Notified Admin",
        telegram_chat_id="555444333",
    )
    await agent_repo.create(admin)

    conv_service = ConversationService(db_session)

    with patch.object(TelegramService, "send_new_message_alert", new_callable=AsyncMock) as mock_alert:
        mock_alert.return_value = [{"ok": True}]

        await conv_service.route_user_message(
            telegram_id=888777,
            text="Need information regarding services",
            first_name="Alice",
            username="alice_user",
        )

        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args.kwargs
        assert call_kwargs["customer_id"] == 888777
        assert call_kwargs["customer_name"] == "Alice"
        assert call_kwargs["message_text"] == "Need information regarding services"
        assert "555444333" in call_kwargs["recipient_chat_ids"]
