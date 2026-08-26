import pytest
from app.services.state_manager import SessionStateManager


class MockRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int = 86400):
        self.store[key] = str(value)

    async def delete(self, key: str):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_session_state_manager_flow():
    """Test Redis session state transitions (BOT_ACTIVE, PENDING_AGENT, HUMAN_ACTIVE, CLOSED)."""
    mock_redis = MockRedis()
    manager = SessionStateManager(redis_client=mock_redis)

    telegram_id = 99887766

    # Default state
    state = await manager.get_user_state(telegram_id)
    assert state == "BOT_ACTIVE"

    # Set state to PENDING_AGENT
    await manager.set_user_state(telegram_id, "PENDING_AGENT")
    assert await manager.get_user_state(telegram_id) == "PENDING_AGENT"

    # Assign agent & set to HUMAN_ACTIVE
    await manager.set_user_state(telegram_id, "HUMAN_ACTIVE")
    await manager.assign_agent(telegram_id, agent_id=42)

    assert await manager.get_user_state(telegram_id) == "HUMAN_ACTIVE"
    assert await manager.get_assigned_agent(telegram_id) == 42

    # Clear session
    await manager.clear_session(telegram_id)
    assert await manager.get_user_state(telegram_id) == "BOT_ACTIVE"
    assert await manager.get_assigned_agent(telegram_id) is None
