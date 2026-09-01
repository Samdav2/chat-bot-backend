from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import AgentLoginSchema, AgentCreateSchema, AgentUpdateSchema, AgentReadSchema, TokenSchema
from app.schemas.common import ResponseSchema

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_agent(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
):
    """Dependency to retrieve currently authenticated support agent from JWT token."""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    agent_repo = AgentRepository(session)
    agent = await agent_repo.get_by_id(int(payload["sub"]))
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support agent not found"
        )
    return agent


@router.post("/login", response_model=TokenSchema)
async def login_agent(
    login_data: AgentLoginSchema,
    session: AsyncSession = Depends(get_async_session)
) -> Any:
    """Authenticate support agent and return JWT access token."""
    agent_repo = AgentRepository(session)
    agent = await agent_repo.get_by_email(login_data.email)
    
    if not agent or not verify_password(login_data.password, agent.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Mark agent online
    await agent_repo.set_online_status(agent.id, True)
    access_token = create_access_token(subject=agent.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "agent": agent
    }


@router.post("/register", response_model=ResponseSchema[AgentReadSchema])
async def register_agent(
    agent_in: AgentCreateSchema,
    session: AsyncSession = Depends(get_async_session)
) -> Any:
    """Register a new support agent account."""
    agent_repo = AgentRepository(session)
    existing = await agent_repo.get_by_email(agent_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An agent account with this email already exists."
        )
    
    hashed_pwd = get_password_hash(agent_in.password)
    from app.models.agent import Agent
    new_agent = Agent(
        email=agent_in.email.lower(),
        hashed_password=hashed_pwd,
        full_name=agent_in.full_name,
        telegram_chat_id=agent_in.telegram_chat_id,
        telegram_username=agent_in.telegram_username,
        is_online=False
    )
    created_agent = await agent_repo.create(new_agent)
    return ResponseSchema(
        success=True,
        message="Agent registered successfully",
        data=created_agent
    )


@router.get("/me", response_model=ResponseSchema[AgentReadSchema])
async def get_agent_profile(
    current_agent = Depends(get_current_agent)
) -> Any:
    """Get logged in agent profile."""
    return ResponseSchema(
        success=True,
        message="Agent profile retrieved successfully",
        data=current_agent
    )


@router.put("/me", response_model=ResponseSchema[AgentReadSchema])
async def update_agent_profile(
    profile_in: AgentUpdateSchema,
    current_agent = Depends(get_current_agent),
    session: AsyncSession = Depends(get_async_session)
) -> Any:
    """Update logged-in support agent profile details including Telegram handle and chat ID."""
    agent_repo = AgentRepository(session)
    hashed_pwd = get_password_hash(profile_in.password) if profile_in.password else None

    updated_agent = await agent_repo.update_agent_profile(
        agent_id=current_agent.id,
        full_name=profile_in.full_name,
        email=profile_in.email,
        hashed_password=hashed_pwd,
        telegram_chat_id=profile_in.telegram_chat_id,
        telegram_username=profile_in.telegram_username,
    )

    return ResponseSchema(
        success=True,
        message="Agent profile updated successfully",
        data=updated_agent
    )

