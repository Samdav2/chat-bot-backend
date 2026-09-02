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
    assert "Falconotp Support" in resp

    otp_resp = await ai.generate_response("where is my otp code?")
    assert "1-3 minutes" in otp_resp
    assert "Cancel" in otp_resp

    buy_resp = await ai.generate_response("how do I buy a number?")
    assert "How to Buy a Number" in buy_resp

    refund_resp = await ai.generate_response("what is the refund policy?")
    assert "only charged if an SMS code is successfully received" in refund_resp


@pytest.mark.asyncio
async def test_bot_mode_ai_response_routing(db_session: AsyncSession):
    mock_tg = MockTelegramService()
    ai = AIService(openai_api_key="", gemini_api_key="", provider="auto")
    service = ConversationService(session=db_session, telegram_service=mock_tg, ai_service=ai)

    telegram_id = 999111222
    # Message 1 (Session start): Triggers admin alert (1) + AI response (2) = 2 messages
    await service.route_user_message(telegram_id=telegram_id, text="What are your hours?")
    assert len(mock_tg.sent_messages) == 2
    assert "New Customer Message on Chatbot" in mock_tg.sent_messages[0]["text"]
    assert "24/7" in mock_tg.sent_messages[1]["text"]

    # Message 2 (Subsequent message in same session): Should ONLY trigger AI response (1 new message), NOT admin alert!
    mock_tg.sent_messages.clear()
    await service.route_user_message(telegram_id=telegram_id, text="Where is my OTP code?")
    assert len(mock_tg.sent_messages) == 1
    assert "1-3 minutes" in mock_tg.sent_messages[0]["text"]
    assert "New Customer Message" not in mock_tg.sent_messages[0]["text"]


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


@pytest.mark.asyncio
async def test_claim_bot_active_conversation_and_auto_claim_on_message(db_session: AsyncSession):
    mock_tg = MockTelegramService()
    ai = AIService(openai_api_key="", gemini_api_key="", provider="auto")
    service = ConversationService(session=db_session, telegram_service=mock_tg, ai_service=ai)

    telegram_id = 444333222
    # 1. User starts chat with AI (status: BOT_ACTIVE, user has NOT requested human support)
    await service.route_user_message(telegram_id=telegram_id, text="Hello, how do I buy a number?")

    user = await service.user_repo.get_by_telegram_id(telegram_id)
    conv = await service.conv_repo.get_active_by_user_id(user.id)
    assert conv.status.value == "BOT_ACTIVE"

    # 2. Admin claims the conversation directly via conversation_id even though user didn't request support
    claimed_conv = await service.claim_conversation(conversation_id=conv.id, agent_id=1)
    assert claimed_conv is not None
    assert claimed_conv.status.value == "HUMAN_ACTIVE"
    assert claimed_conv.assigned_agent_id == 1

    # 3. Subsequent user message goes to human queue, bot does NOT auto-reply
    mock_tg.sent_messages.clear()
    await service.route_user_message(telegram_id=telegram_id, text="Is anyone there?")
    assert len(mock_tg.sent_messages) == 0
