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
