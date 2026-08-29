import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from app.services.ai_service import AIService
from app.services.conversation_service import ConversationService
from app.services.telegram_service import TelegramService
from app.models.message import SenderRole


class MockTelegramService(TelegramService):
    def __init__(self):
        super().__init__(bot_token="mock_bot_token")
        self.sent_messages = []

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode="Markdown"):
        self.sent_messages.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return {"ok": True, "result": {"message_id": 123}}


@pytest.mark.asyncio
async def test_ai_service_fallback():
    ai = AIService(openai_api_key="", gemini_api_key="", provider="auto")
    resp = await ai.generate_response("Hello there!")
    assert "🤖" in resp
    assert "AI assistant" in resp


@pytest.mark.asyncio
async def test_bot_mode_ai_response_routing(db_session: AsyncSession):
    mock_tg = MockTelegramService()
    ai = AIService(openai_api_key="", gemini_api_key="", provider="auto")
    service = ConversationService(session=db_session, telegram_service=mock_tg, ai_service=ai)

    telegram_id = 999111222
    await service.route_user_message(telegram_id=telegram_id, text="What are your hours?")

    # Verify AI bot message sent to Telegram
    assert len(mock_tg.sent_messages) == 1
    assert "24/7" in mock_tg.sent_messages[0]["text"]
    assert mock_tg.sent_messages[0]["reply_markup"] is not None


@pytest.mark.asyncio
async def test_admin_message_default_sends_to_telegram(db_session: AsyncSession):
    mock_tg = MockTelegramService()
    service = ConversationService(session=db_session, telegram_service=mock_tg)

    # First escalate and claim conversation
    conv = await service.escalate_to_human(telegram_id=888777666, text_trigger="/support")
    await service.claim_conversation(telegram_id=888777666, agent_id=1)
    mock_tg.sent_messages.clear()

    # Send agent message from dashboard with default send_to_telegram=True
    msg = await service.send_agent_message(
        conversation_id=conv.id,
        agent_id=1,
        content="Hello customer, how can I help you?",
    )

    assert msg is not None
    assert msg.sender_role == SenderRole.AGENT
    # Verify Telegram message WAS delivered to user on Telegram!
    assert len(mock_tg.sent_messages) == 1
    assert "Hello customer, how can I help you?" in mock_tg.sent_messages[0]["text"]


@pytest.mark.asyncio
async def test_admin_message_opt_out_telegram(db_session: AsyncSession):
    mock_tg = MockTelegramService()
    service = ConversationService(session=db_session, telegram_service=mock_tg)

    conv = await service.escalate_to_human(telegram_id=777666555, text_trigger="/support")
    await service.claim_conversation(telegram_id=777666555, agent_id=1)
    mock_tg.sent_messages.clear()

    # Send agent message with explicit send_to_telegram=False
    msg = await service.send_agent_message(
        conversation_id=conv.id,
        agent_id=1,
        content="Internal note only",
        send_to_telegram=False,
    )

    assert msg is not None
    assert len(mock_tg.sent_messages) == 0


@pytest.mark.asyncio
async def test_human_active_suppresses_bot_and_ai_replies(db_session: AsyncSession):
    mock_tg = MockTelegramService()
    ai = AIService(openai_api_key="", gemini_api_key="", provider="auto")
    service = ConversationService(session=db_session, telegram_service=mock_tg, ai_service=ai)

    telegram_id = 555444333
    conv = await service.escalate_to_human(telegram_id=telegram_id, text_trigger="/support")
    await service.claim_conversation(telegram_id=telegram_id, agent_id=1)
    mock_tg.sent_messages.clear()

    # Customer sends message while talking to human agent
    await service.route_user_message(telegram_id=telegram_id, text="I have a question about my order")

    # Verify NO bot or AI auto-reply was sent to Telegram!
    assert len(mock_tg.sent_messages) == 0
