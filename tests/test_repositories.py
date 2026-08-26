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
