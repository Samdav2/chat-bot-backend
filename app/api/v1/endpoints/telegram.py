import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.services.conversation_service import ConversationService
from app.services.telegram_service import TelegramService
from app.services.state_manager import SessionStateManager

from app.models.conversation import ConversationStatus

from app.core.constants import FAQ_COMMANDS, get_faq_inline_keyboard, get_single_other_question_keyboard

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

    # 1. Handle Inline Callback Queries (e.g., FAQ commands, Staff Group ticket claim, customer rating)
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

        elif cb_data == "show_commands":
            # 1st click on "Other question" -> Displays full list of commands/questions + "Other question" escalation button
            chat_id = from_user["id"]
            help_text = (
                "📋 **Frequently Asked Questions & Commands**\n\n"
                "Please select a question below to get instant answers, or click **❓ Other question** to speak directly with customer support:"
            )
            await telegram_service.answer_callback_query(cb_id, text="Opening commands list...")
            await telegram_service.send_message(
                chat_id=chat_id,
                text=help_text,
                reply_markup=get_faq_inline_keyboard(),
            )

        elif cb_data == "request_support":
            # 2nd click on "Other question" inside the command list -> Triggers live human agent support escalation
            chat_id = from_user["id"]
            await service.escalate_to_human(
                telegram_id=chat_id,
                username=from_user.get("username"),
                first_name=from_user.get("first_name"),
                text_trigger="Inline Button Escalation",
            )
            await telegram_service.answer_callback_query(cb_id, text="Connecting you to live support...")

        elif cb_data in FAQ_COMMANDS:
            # Customer clicked an FAQ command button -> Answers question & keeps chat clean with single 'Other question' button
            chat_id = from_user["id"]
            faq_item = FAQ_COMMANDS[cb_data]
            answer_text = f"**{faq_item['title']}**\n\n{faq_item['response']}"
            await telegram_service.answer_callback_query(cb_id, text=f"Answer: {faq_item['title']}")
            await telegram_service.send_message(
                chat_id=chat_id,
                text=answer_text,
                reply_markup=get_single_other_question_keyboard(),
            )

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

    media_url = None
    media_type = None

    # Handle incoming photos sent by Telegram user
    if "photo" in message and isinstance(message["photo"], list) and len(message["photo"]) > 0:
        photo_info = message["photo"][-1]  # Highest resolution photo
        file_id = photo_info.get("file_id")
        if file_id:
            media_url = await telegram_service.download_telegram_photo(file_id)
            media_type = "image"
            if not text:
                text = message.get("caption", "") or "[Image Attachment]"

    # Check active conversation status in DB and Redis
    user = await service.user_repo.get_by_telegram_id(chat_id)
    active_conv = await service.conv_repo.get_active_by_user_id(user.id) if user else None
    current_state = await state_manager.get_user_state(chat_id)
    is_human_active = (active_conv and active_conv.status == ConversationStatus.HUMAN_ACTIVE) or current_state == "HUMAN_ACTIVE"

    # Command Trigger check for FAQ menu (/command, /commands, /help, /start)
    normalized_text = text.strip().lower()
    if not is_human_active and normalized_text in ["/command", "/commands", "/help", "/start"]:
        help_text = (
            "📋 **Frequently Asked Questions & Commands**\n\n"
            "Please select a question below to get instant answers, or click **❓ Other question** to speak directly with customer support:"
        )
        await telegram_service.send_message(
            chat_id=chat_id,
            text=help_text,
            reply_markup=get_faq_inline_keyboard(),
        )
        return {"status": "ok"}

    # Command Trigger check for Escalation (/support, "talk to human", "agent", "human")
    escalation_triggers = ["/support", "talk to human", "agent", "human", "speak to agent", "help human"]

    if not is_human_active and any(trigger in normalized_text for trigger in escalation_triggers):
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
        media_url=media_url,
        media_type=media_type,
    )

    return {"status": "ok"}


@router.post("/set-webhook")
async def set_telegram_webhook(webhook_url: str) -> Dict[str, Any]:
    """Register or update Telegram webhook URL with Telegram API."""
    telegram_service = TelegramService()
    return await telegram_service.set_webhook(webhook_url)


@router.get("/webhook-info")
async def get_telegram_webhook_info() -> Dict[str, Any]:
    """Check current webhook registration status from Telegram API."""
    telegram_service = TelegramService()
    return await telegram_service.get_webhook_info()


