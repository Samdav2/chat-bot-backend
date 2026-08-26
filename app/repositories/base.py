from typing import Generic, TypeVar, Type, Optional, List, Any, Sequence
from sqlmodel import SQLModel, select, func
from sqlmodel.ext.asyncio.session import AsyncSession

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing CRUD operations for SQLModel entities."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Fetch a single record by primary key asynchronously."""
        return await self.session.get(self.model, id)

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        """Fetch all records with pagination asynchronously."""
        statement = select(self.model).offset(skip).limit(limit)
        result = await self.session.exec(statement)
        return result.all()

    async def create(self, entity: ModelType) -> ModelType:
        """Create and persist a new record asynchronously."""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing record asynchronously."""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: Any) -> bool:
        """Delete a record by primary key asynchronously."""
        entity = await self.get_by_id(id)
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False

    async def count(self) -> int:
        """Count total records asynchronously."""
        statement = select(func.count()).select_from(self.model)
        result = await self.session.exec(statement)
        return result.one() or 0
