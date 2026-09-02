from typing import Sequence
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.quick_response import QuickResponse
from app.repositories.base import BaseRepository


class QuickResponseRepository(BaseRepository[QuickResponse]):
    """Async Repository for Quick Responses (Canned Snippets) operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(QuickResponse, session)

    async def get_all_ordered(self) -> Sequence[QuickResponse]:
        """Fetch all quick responses ordered chronologically by title."""
        statement = select(QuickResponse).order_by(QuickResponse.title.asc())
        result = await self.session.exec(statement)
        return result.all()
