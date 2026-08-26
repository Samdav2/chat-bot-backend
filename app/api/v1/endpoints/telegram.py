import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.services.conversation_service import ConversationService
from app.services.telegram_service import TelegramService
from app.services.state_manager import SessionStateManager

router = APIRouter()
logger = logging.getLogger("api.telegram_webhook")


@router.post("/webhook")
async def handle_telegram_update(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, str]:
    """
    Main Telegram Webhook endpoint.
    Processes incoming text messages, escalations, and staff inline callback queries asynchronously.
    """
    try:
        update = await request.json()
    except Exception as e:
        logger.error(f"Error parsing Telegram update JSON: {e}")
        return {"status": "ok"}

    service = ConversationService(session)
    telegram_service = TelegramService()
    state_manager = SessionStateManager()

    # 1. Handle Inline Callback Queries (e.g., Staff Group ticket claim, customer rating)
    if "callback_query" in update:
        cb = update["callback_query"]
        cb_id = cb["id"]
        cb_data = cb.get("data", "")
        from_user = cb["from"]

        if cb_data.startswith("claim_"):
            # Telegram Staff member pressed [Claim Ticket]
            try:
                target_chat_id = int(cb_data.split("_")[1])
                staff_name = from_user.get("first_name", "Staff Member")
                
                # Check if customer session is already claimed
                current_state = await state_manager.get_user_state(target_chat_id)
                if current_state == "HUMAN_ACTIVE":
                    await telegram_service.answer_callback_query(
                        cb_id, text="⚠️ Ticket has already been claimed by another agent!", show_alert=True
                    )
                else:
                    # Note: Using default fallback staff agent ID 1 if claimed from Telegram
                    await service.claim_conversation(telegram_id=target_chat_id, agent_id=1)
                    await telegram_service.answer_callback_query(
                        cb_id, text=f"✅ You have claimed ticket for customer {target_chat_id}!"
                    )
                    # Notify Staff Group
                    if "message" in cb:
                        message_id = cb["message"]["message_id"]
                        chat_id = cb["message"]["chat"]["id"]
                        await telegram_service.send_message(
                            chat_id=chat_id,
                            text=f"✅ **Ticket Claimed!** Agent **{staff_name}** has claimed ticket `{target_chat_id}`."
                        )
            except Exception as ex:
                logger.error(f"Error handling callback claim: {ex}")

        elif cb_data == "request_support":
            # Customer pressed inline "Speak to Support" button
            chat_id = from_user["id"]
            await service.escalate_to_human(
                telegram_id=chat_id,
                username=from_user.get("username"),
                first_name=from_user.get("first_name"),
                text_trigger="Inline Button Escalation",
            )
            await telegram_service.answer_callback_query(cb_id, text="Connecting you to support...")

        elif cb_data.startswith("rate_"):
            rating = cb_data.split("_")[1]
            await telegram_service.answer_callback_query(
                cb_id, text=f"Thank you for rating us {rating}/5 stars! ⭐", show_alert=True
            )

        return {"status": "ok"}

    # 2. Handle Text Messages
    if "message" not in update:
        return {"status": "ok"}

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    from_user = message.get("from", {})

    username = from_user.get("username")
    first_name = from_user.get("first_name")
    last_name = from_user.get("last_name")

    # Command Trigger check for Escalation (/support, "talk to human", "agent", "human")
    normalized_text = text.strip().lower()
    escalation_triggers = ["/support", "talk to human", "agent", "human", "speak to agent", "help human"]

    if any(trigger in normalized_text for trigger in escalation_triggers):
        await service.escalate_to_human(
            telegram_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            text_trigger=text,
        )
        return {"status": "ok"}

    # State-based message routing
    await service.route_user_message(
        telegram_id=chat_id,
        text=text,
        username=username,
        first_name=first_name,
    )

    return {"status": "ok"}
