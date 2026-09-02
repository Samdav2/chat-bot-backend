import logging
from typing import Optional, List, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, SenderRole
from app.models.user import User
from app.models.agent import Agent
from app.repositories.user_repository import UserRepository
from app.repositories.agent_repository import AgentRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.services.state_manager import SessionStateManager
from app.services.telegram_service import TelegramService
from app.services.websocket_manager import ws_manager
from app.services.ai_service import AIService
from app.core.constants import get_faq_inline_keyboard, get_single_other_question_keyboard

logger = logging.getLogger("service.conversation")


class ConversationService:
    """Async business orchestrator for customer support ticket lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        state_manager: Optional[SessionStateManager] = None,
        telegram_service: Optional[TelegramService] = None,
        ai_service: Optional[AIService] = None,
    ):
        self.session = session
        self.user_repo = UserRepository(session)
        self.agent_repo = AgentRepository(session)
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.state_manager = state_manager or SessionStateManager()
        self.telegram_service = telegram_service or TelegramService()
        self.ai_service = ai_service or AIService()

    async def escalate_to_human(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        text_trigger: str = "/support",
    ) -> Conversation:
        """Escalate customer interaction from automated bot to human agent queue."""
        # 1. Update DB user profile
        user = await self.user_repo.get_or_create_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        # 2. Get or create active conversation
        conversation = await self.conv_repo.get_active_by_user_id(user.id)
        if not conversation:
            conversation = Conversation(
                user_id=user.id,
                status=ConversationStatus.PENDING_AGENT,
            )
            conversation = await self.conv_repo.create(conversation)
        else:
            conversation = await self.conv_repo.update_status(
                conversation.id, ConversationStatus.PENDING_AGENT
            )

        # 3. Store incoming request message
        await self.msg_repo.add_message(
            conversation_id=conversation.id,
            sender_role=SenderRole.USER,
            sender_id=telegram_id,
            content=text_trigger,
        )

        # 4. Set Redis Session State
        await self.state_manager.set_user_state(telegram_id, "PENDING_AGENT")

        # 5. Notify customer & Send Telegram Staff Alert
        await self.telegram_service.send_message(
            chat_id=telegram_id,
            text="**Support Requested**: You have been placed in line for a human support agent. An agent will be with you shortly!",
        )
        
        display_name = first_name or username or f"User {telegram_id}"
        await self.telegram_service.send_staff_alert(
            customer_id=telegram_id,
            customer_name=display_name,
            initial_text=text_trigger,
        )

        return conversation

    async def claim_conversation(
        self,
        telegram_id: Optional[int] = None,
        agent_id: int = 1,
        conversation_id: Optional[int] = None,
    ) -> Optional[Conversation]:
        """Claim ticket by Support Agent (via Telegram Staff Button or Dashboard API). Supports claiming BOT_ACTIVE conversations."""
        conversation = None
        if conversation_id:
            conversation = await self.conv_repo.get_with_details(conversation_id)
            if conversation and conversation.user:
                telegram_id = conversation.user.telegram_id
        elif telegram_id:
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if user:
                conversation = await self.conv_repo.get_active_by_user_id(user.id)

        if not conversation or not telegram_id:
            logger.warning(f"No valid conversation found to claim (telegram_id: {telegram_id}, conversation_id: {conversation_id})")
            return None

        # Update Conversation status and assigned agent in DB
        conversation = await self.conv_repo.assign_agent(conversation.id, agent_id)

        # Update Redis session state & agent assignment
        await self.state_manager.set_user_state(telegram_id, "HUMAN_ACTIVE")
        await self.state_manager.assign_agent(telegram_id, agent_id)

        # Fetch agent details for notification
        agent = await self.agent_repo.get_by_id(agent_id)
        agent_name = agent.full_name if agent else "Support Agent"

        # Notify Customer on Telegram
        await self.telegram_service.send_message(
            chat_id=telegram_id,
            text=f"**Agent Connected**: You are now speaking directly with **{agent_name}**. How can we help you today?",
        )

        return conversation

    async def close_conversation(
        self, conversation_id: int, agent_id: Optional[int] = None
    ) -> Optional[Conversation]:
        """Close active support session and restore bot auto-replies."""
        conversation = await self.conv_repo.get_with_details(conversation_id)
        if not conversation or not conversation.user:
            return None

        telegram_id = conversation.user.telegram_id

        # Update DB status to CLOSED
        conversation = await self.conv_repo.update_status(
            conversation_id, ConversationStatus.CLOSED
        )

        # Clear Redis session state
        await self.state_manager.clear_session(telegram_id)

        # Send closing & rating message to customer
        rating_markup = {
            "inline_keyboard": [
                [
                    {"text": "1", "callback_data": "rate_1"},
                    {"text": "2", "callback_data": "rate_2"},
                    {"text": "3", "callback_data": "rate_3"},
                    {"text": "4", "callback_data": "rate_4"},
                    {"text": "5", "callback_data": "rate_5"},
                ]
            ]
        }
        await self.telegram_service.send_message(
            chat_id=telegram_id,
            text="**Chat Resolved**: Your support ticket has been closed. Please rate your support experience below:",
            reply_markup=rating_markup,
        )

        return conversation

    async def route_user_message(
        self,
        telegram_id: int,
        text: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ):
        """Route customer Telegram text message depending on active conversation state."""
        user = await self.user_repo.get_or_create_user(
            telegram_id=telegram_id, username=username, first_name=first_name
        )
        conversation = await self.conv_repo.get_active_by_user_id(user.id)
        current_state = await self.state_manager.get_user_state(telegram_id)

        # DB conversation status is source of truth
        if conversation and conversation.status == ConversationStatus.HUMAN_ACTIVE:
            effective_state = "HUMAN_ACTIVE"
        elif conversation and conversation.status == ConversationStatus.PENDING_AGENT:
            effective_state = "PENDING_AGENT"
        else:
            effective_state = current_state or "BOT_ACTIVE"

        if effective_state == "HUMAN_ACTIVE" and conversation:
            # Sync Redis state if needed
            if current_state != "HUMAN_ACTIVE":
                await self.state_manager.set_user_state(telegram_id, "HUMAN_ACTIVE")

            # Save message to DB
            message = await self.msg_repo.add_message(
                conversation_id=conversation.id,
                sender_role=SenderRole.USER,
                sender_id=telegram_id,
                content=text,
                media_url=media_url,
                media_type=media_type,
            )

            # Broadcast to dashboard agent WebSocket & Redis
            payload = {
                "id": message.id,
                "conversationId": conversation.id,
                "conversation_id": conversation.id,
                "senderRole": "USER",
                "sender_role": "USER",
                "senderId": telegram_id,
                "sender_id": telegram_id,
                "content": text,
                "mediaUrl": media_url,
                "media_url": media_url,
                "mediaType": media_type,
                "media_type": media_type,
                "timestamp": message.created_at.isoformat(),
                "created_at": message.created_at.isoformat(),
            }
            await ws_manager.broadcast_to_conversation(conversation.id, payload)
            await ws_manager.publish_to_redis(conversation.id, payload)
            return

        elif effective_state == "PENDING_AGENT" and conversation:
            # Sync Redis state if needed
            if current_state != "PENDING_AGENT":
                await self.state_manager.set_user_state(telegram_id, "PENDING_AGENT")

            # Save incoming user message to DB as well so agent can read queue messages
            message = await self.msg_repo.add_message(
                conversation_id=conversation.id,
                sender_role=SenderRole.USER,
                sender_id=telegram_id,
                content=text,
                media_url=media_url,
                media_type=media_type,
            )

            payload = {
                "id": message.id,
                "conversationId": conversation.id,
                "conversation_id": conversation.id,
                "senderRole": "USER",
                "sender_role": "USER",
                "senderId": telegram_id,
                "sender_id": telegram_id,
                "content": text,
                "mediaUrl": media_url,
                "media_url": media_url,
                "mediaType": media_type,
                "media_type": media_type,
                "timestamp": message.created_at.isoformat(),
                "created_at": message.created_at.isoformat(),
            }
            await ws_manager.broadcast_to_conversation(conversation.id, payload)
            await ws_manager.publish_to_redis(conversation.id, payload)

            await self.telegram_service.send_message(
                chat_id=telegram_id,
                text="⏳ You are still in queue. An agent will connect shortly. Thank you for your patience!",
            )
            return

        else:
            # BOT_ACTIVE AI mode logic
            is_new_conversation = False
            if not conversation:
                conversation = Conversation(
                    user_id=user.id,
                    status=ConversationStatus.BOT_ACTIVE,
                )
                conversation = await self.conv_repo.create(conversation)
                is_new_conversation = True

            # Check existing message count prior to adding the new message
            existing_messages = await self.msg_repo.get_by_conversation_id(conversation.id)
            is_first_message = is_new_conversation or len(existing_messages) == 0

            # Save incoming user message to DB
            user_msg = await self.msg_repo.add_message(
                conversation_id=conversation.id,
                sender_role=SenderRole.USER,
                sender_id=telegram_id,
                content=text,
                media_url=media_url,
                media_type=media_type,
            )

            # Broadcast user message to WS & Redis
            user_payload = {
                "id": user_msg.id,
                "conversationId": conversation.id,
                "conversation_id": conversation.id,
                "senderRole": "USER",
                "sender_role": "USER",
                "senderId": telegram_id,
                "sender_id": telegram_id,
                "content": text,
                "mediaUrl": media_url,
                "media_url": media_url,
                "mediaType": media_type,
                "media_type": media_type,
                "timestamp": user_msg.created_at.isoformat(),
                "created_at": user_msg.created_at.isoformat(),
            }
            await ws_manager.broadcast_to_conversation(conversation.id, user_payload)
            await ws_manager.publish_to_redis(conversation.id, user_payload)

            # Notify admins on Telegram ONLY on the first message of a session
            if is_first_message:
                try:
                    agents_with_tg = await self.agent_repo.get_agents_with_telegram()
                    admin_chat_ids = [
                        a.telegram_chat_id or a.telegram_username for a in agents_with_tg if (a.telegram_chat_id or a.telegram_username)
                    ]
                    customer_display_name = first_name or username or f"User {telegram_id}"
                    await self.telegram_service.send_new_message_alert(
                        customer_id=telegram_id,
                        customer_name=customer_display_name,
                        message_text=text,
                        recipient_chat_ids=admin_chat_ids,
                    )
                except Exception as e:
                    logger.error(f"Error notifying admins on Telegram: {e}")

            # Fetch recent message history for AI context
            history_msgs = await self.msg_repo.get_by_conversation_id(conversation.id)
            formatted_history = []
            for m in history_msgs[:-1]:  # exclude the current message we just added
                formatted_history.append({
                    "role": "assistant" if m.sender_role in [SenderRole.BOT, SenderRole.AGENT] else "user",
                    "content": m.content,
                })

            # Generate AI response
            reply_text = await self.ai_service.generate_response(
                prompt=text, history=formatted_history
            )

            # Save AI response message to DB
            bot_msg = await self.msg_repo.add_message(
                conversation_id=conversation.id,
                sender_role=SenderRole.BOT,
                sender_id=0,
                content=reply_text,
            )

            # Dispatch to Telegram with single 'Other question' button (opens command list)
            keyboard = get_single_other_question_keyboard()
            await self.telegram_service.send_message(
                chat_id=telegram_id, text=reply_text, reply_markup=keyboard
            )

            # Broadcast Bot response to WS & Redis
            bot_payload = {
                "id": bot_msg.id,
                "conversationId": conversation.id,
                "conversation_id": conversation.id,
                "senderRole": "BOT",
                "sender_role": "BOT",
                "senderId": 0,
                "sender_id": 0,
                "content": reply_text,
                "timestamp": bot_msg.created_at.isoformat(),
                "created_at": bot_msg.created_at.isoformat(),
            }
            await ws_manager.broadcast_to_conversation(conversation.id, bot_payload)
            await ws_manager.publish_to_redis(conversation.id, bot_payload)

    async def send_agent_message(
        self,
        conversation_id: int,
        agent_id: int,
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
        send_to_telegram: bool = True,
    ) -> Optional[Message]:
        """Send message from support agent (Web Dashboard or Staff Group) to customer's chat."""
        conversation = await self.conv_repo.get_with_details(conversation_id)
        if not conversation or not conversation.user:
            return None

        telegram_id = conversation.user.telegram_id

        # Auto-claim conversation and transition state to HUMAN_ACTIVE if not already active
        if conversation.status != ConversationStatus.HUMAN_ACTIVE or conversation.assigned_agent_id != agent_id:
            await self.conv_repo.assign_agent(conversation_id, agent_id)
            await self.state_manager.set_user_state(telegram_id, "HUMAN_ACTIVE")
            await self.state_manager.assign_agent(telegram_id, agent_id)

        # 1. Save agent message to DB
        message = await self.msg_repo.add_message(
            conversation_id=conversation_id,
            sender_role=SenderRole.AGENT,
            sender_id=agent_id,
            content=content,
            media_url=media_url,
            media_type=media_type,
        )

        # 2. Dispatch to customer Telegram chat window
        if send_to_telegram:
            if media_url:
                caption = f"**Agent Response:**\n{content}" if content else "**Agent Response**"
                await self.telegram_service.send_photo(
                    chat_id=telegram_id,
                    photo_url_or_path=media_url,
                    caption=caption,
                )
            else:
                await self.telegram_service.send_message(
                    chat_id=telegram_id,
                    text=f"**Agent Response:**\n{content}",
                )

        # 3. Broadcast to all active WebSocket listeners
        payload = {
            "id": message.id,
            "conversationId": conversation_id,
            "conversation_id": conversation_id,
            "senderRole": "AGENT",
            "sender_role": "AGENT",
            "senderId": agent_id,
            "sender_id": agent_id,
            "content": content,
            "mediaUrl": media_url,
            "media_url": media_url,
            "mediaType": media_type,
            "media_type": media_type,
            "timestamp": message.created_at.isoformat(),
            "created_at": message.created_at.isoformat(),
        }
        await ws_manager.broadcast_to_conversation(conversation_id, payload)
        await ws_manager.publish_to_redis(conversation_id, payload)

        return message


