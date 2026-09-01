import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.conversation import ConversationStatus
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.models.message import SenderRole


@pytest.mark.asyncio
async def test_user_and_conversation_repositories(db_session: AsyncSession):
    """Test async CRUD operations in UserRepository, ConversationRepository, and MessageRepository."""
    user_repo = UserRepository(db_session)
    conv_repo = ConversationRepository(db_session)
    msg_repo = MessageRepository(db_session)

    # 1. Get or Create User
    user = await user_repo.get_or_create_user(
        telegram_id=12345678,
        username="johndoe",
        first_name="John",
        last_name="Doe",
    )
    assert user.id is not None
    assert user.telegram_id == 12345678

    # 2. Escalate & Create Conversation
    from app.models.conversation import Conversation
    conv = Conversation(
        user_id=user.id,
        status=ConversationStatus.PENDING_AGENT,
    )
    conv = await conv_repo.create(conv)
    assert conv.id is not None
    assert conv.status == ConversationStatus.PENDING_AGENT

    # 3. Add message
    msg = await msg_repo.add_message(
        conversation_id=conv.id,
        sender_role=SenderRole.USER,
        sender_id=12345678,
        content="I need help with my account",
    )
    assert msg.id is not None
    assert msg.content == "I need help with my account"

    # 4. Fetch details
    conv_details = await conv_repo.get_with_details(conv.id)
    assert conv_details is not None
    assert conv_details.user.username == "johndoe"


@pytest.mark.asyncio
async def test_claim_and_close_bot_active_conversation(db_session: AsyncSession):
    """Test claiming and closing a BOT_ACTIVE conversation via ConversationService."""
    from unittest.mock import AsyncMock
    from app.services.conversation_service import ConversationService
    from app.models.conversation import Conversation

    user_repo = UserRepository(db_session)
    conv_repo = ConversationRepository(db_session)

    # 1. Create User and BOT_ACTIVE Conversation
    user = await user_repo.get_or_create_user(
        telegram_id=87654321,
        username="botuser",
        first_name="Bot",
        last_name="User",
    )
    bot_conv = Conversation(
        user_id=user.id,
        status=ConversationStatus.BOT_ACTIVE,
    )
    bot_conv = await conv_repo.create(bot_conv)
    assert bot_conv.status == ConversationStatus.BOT_ACTIVE

    # 2. Mock state manager and telegram service
    state_manager = AsyncMock()
    telegram_service = AsyncMock()
    service = ConversationService(
        session=db_session,
        state_manager=state_manager,
        telegram_service=telegram_service,
    )

    # 3. Claim BOT_ACTIVE conversation
    claimed = await service.claim_conversation(conversation_id=bot_conv.id, agent_id=1)
    assert claimed is not None
    assert claimed.status == ConversationStatus.HUMAN_ACTIVE
    assert claimed.assigned_agent_id == 1
    state_manager.set_user_state.assert_called_with(87654321, "HUMAN_ACTIVE")

    # 4. Close conversation
    closed = await service.close_conversation(conversation_id=bot_conv.id, agent_id=1)
    assert closed is not None
    assert closed.status == ConversationStatus.CLOSED
    state_manager.clear_session.assert_called_with(87654321)

