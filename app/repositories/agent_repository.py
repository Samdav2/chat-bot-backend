from typing import Optional, Sequence
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.agent import Agent
from app.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    """Async Repository for Support Agent operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Agent, session)

    async def get_by_email(self, email: str) -> Optional[Agent]:
        """Fetch agent by email address."""
        statement = select(Agent).where(Agent.email == email.lower())
        result = await self.session.exec(statement)
        return result.first()

    async def get_online_agents(self) -> Sequence[Agent]:
        """Fetch all currently online agents."""
        statement = select(Agent).where(Agent.is_online == True)
        result = await self.session.exec(statement)
        return result.all()

    async def set_online_status(self, agent_id: int, is_online: bool) -> Optional[Agent]:
        """Update online status of an agent."""
        agent = await self.get_by_id(agent_id)
        if agent:
            agent.is_online = is_online
            return await self.update(agent)
        return None

    async def get_agents_with_telegram(self) -> Sequence[Agent]:
        """Fetch all agents who have a configured telegram_chat_id or telegram_username."""
        from sqlmodel import or_
        statement = select(Agent).where(
            or_(
                Agent.telegram_chat_id.is_not(None),
                Agent.telegram_username.is_not(None),
            )
        )
        result = await self.session.exec(statement)
        return result.all()

    async def update_agent_profile(
        self,
        agent_id: int,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        hashed_password: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        telegram_username: Optional[str] = None,
    ) -> Optional[Agent]:
        """Update profile information for an agent."""
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None

        if full_name is not None:
            agent.full_name = full_name
        if email is not None:
            agent.email = email.lower()
        if hashed_password is not None:
            agent.hashed_password = hashed_password
        if telegram_chat_id is not None:
            agent.telegram_chat_id = telegram_chat_id
        if telegram_username is not None:
            agent.telegram_username = telegram_username

        return await self.update(agent)

