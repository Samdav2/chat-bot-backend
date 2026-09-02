from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_async_session
from app.api.v1.endpoints.auth import get_current_agent
from app.models.quick_response import QuickResponse
from app.repositories.quick_response_repository import QuickResponseRepository
from app.schemas.common import ResponseSchema
from app.schemas.quick_response import QuickResponseCreateSchema, QuickResponseReadSchema

router = APIRouter()


@router.get("", response_model=ResponseSchema[List[QuickResponseReadSchema]])
async def list_quick_responses(
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Fetch all saved quick response snippets."""
    repo = QuickResponseRepository(session)
    items = await repo.get_all_ordered()
    return ResponseSchema(
        success=True,
        message=f"Retrieved {len(items)} quick responses.",
        data=items,
    )


@router.post("", response_model=ResponseSchema[QuickResponseReadSchema])
async def create_quick_response(
    payload: QuickResponseCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Create a new quick response snippet."""
    repo = QuickResponseRepository(session)
    entity = QuickResponse(
        title=payload.title.strip(),
        content=payload.content.strip(),
    )
    created = await repo.create(entity)
    return ResponseSchema(
        success=True,
        message="Quick response snippet created successfully.",
        data=created,
    )


@router.delete("/{id}", response_model=ResponseSchema[dict])
async def delete_quick_response(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Delete a saved quick response snippet."""
    repo = QuickResponseRepository(session)
    deleted = await repo.delete(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quick response with ID {id} not found.",
        )
    return ResponseSchema(
        success=True,
        message="Quick response deleted successfully.",
        data={"id": id},
    )
