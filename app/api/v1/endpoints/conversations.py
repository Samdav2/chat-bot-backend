from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.models.conversation import ConversationStatus
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    ConversationReadSchema,
    ConversationDetailSchema,
    MessageCreateSchema,
    MessageReadSchema,
)
from app.schemas.common import ResponseSchema
from app.api.v1.endpoints.auth import get_current_agent

router = APIRouter()


@router.get("", response_model=ResponseSchema[List[ConversationReadSchema]])
async def list_conversations(
    status_filter: Optional[ConversationStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """List support conversations for the agent dashboard with optional status filtering."""
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)
    
    conversations = await conv_repo.get_by_status(status=status_filter, skip=skip, limit=limit)
    
    results = []
    for conv in conversations:
        latest_msg = await msg_repo.get_latest_message(conv.id)
        conv_read = ConversationReadSchema.model_validate(conv)
        if latest_msg:
            conv_read.latest_message = MessageReadSchema.model_validate(latest_msg)
        results.append(conv_read)
        
    return ResponseSchema(
        success=True,
        message=f"Retrieved {len(results)} conversations.",
        data=results,
    )


@router.get("/{id}", response_model=ResponseSchema[ConversationDetailSchema])
async def get_conversation_detail(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Fetch complete details and message history of a single conversation."""
    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)
    
    conversation = await conv_repo.get_with_details(id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation ticket not found."
        )
    
    messages = await msg_repo.get_by_conversation_id(id)
    detail = ConversationDetailSchema.model_validate(conversation)
    detail.messages = [MessageReadSchema.model_validate(m) for m in messages]
    
    return ResponseSchema(
        success=True,
        message="Conversation detail retrieved.",
        data=detail,
    )


@router.post("/{id}/claim", response_model=ResponseSchema[ConversationReadSchema])
async def claim_conversation(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Claim a pending conversation ticket for the authenticated agent."""
    conv_repo = ConversationRepository(session)
    conversation = await conv_repo.get_with_details(id)
    if not conversation or not conversation.user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or missing associated user."
        )
        
    service = ConversationService(session)
    claimed_conv = await service.claim_conversation(
        conversation_id=id,
        agent_id=current_agent.id,
    )
    
    if not claimed_conv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not claim conversation."
        )
        
    return ResponseSchema(
        success=True,
        message="Conversation successfully claimed.",
        data=ConversationReadSchema.model_validate(claimed_conv),
    )


@router.post("/{id}/close", response_model=ResponseSchema[ConversationReadSchema])
async def close_conversation(
    id: int,
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Close an active support conversation and reset user session state to BOT_ACTIVE."""
    service = ConversationService(session)
    closed_conv = await service.close_conversation(conversation_id=id, agent_id=current_agent.id)
    
    if not closed_conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or already closed."
        )
        
    return ResponseSchema(
        success=True,
        message="Conversation closed successfully.",
        data=ConversationReadSchema.model_validate(closed_conv),
    )


@router.post("/{id}/messages", response_model=ResponseSchema[MessageReadSchema])
async def send_agent_message(
    id: int,
    message_in: MessageCreateSchema,
    session: AsyncSession = Depends(get_async_session),
    current_agent = Depends(get_current_agent),
) -> Any:
    """Send message from support agent dashboard directly to user's chat window."""
    service = ConversationService(session)
    message = await service.send_agent_message(
        conversation_id=id,
        agent_id=current_agent.id,
        content=message_in.content,
        send_to_telegram=message_in.send_to_telegram,
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send message to user."
        )
        
    return ResponseSchema(
        success=True,
        message="Message dispatched to customer chat.",
        data=MessageReadSchema.model_validate(message),
    )

