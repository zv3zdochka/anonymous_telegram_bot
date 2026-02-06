"""
Message Handler
===============

Main handler for processing incoming messages.
Implements both direct and delayed anonymization modes.
Privacy-focused: no user identifiers logged.
"""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Filter

from bot.config import get_settings
from bot.services.queue_manager import QueueManager
from bot.services.message_processor import MessageProcessor
from bot.utils.helpers import (
    extract_text_after_prefix,
    is_media_with_caption,
    has_any_content
)

logger = logging.getLogger(__name__)
router = Router(name="message_handler")

# Global instances (initialized in setup)
queue_manager: QueueManager | None = None
message_processor: MessageProcessor | None = None


def setup_handler(bot: Bot, queue: QueueManager) -> None:
    """
    Initialize handler with required dependencies.

    Args:
        bot: Aiogram Bot instance
        queue: Queue manager instance
    """
    global queue_manager, message_processor
    queue_manager = queue
    settings = get_settings()
    message_processor = MessageProcessor(
        bot=bot,
        error_notifications=settings.error_notifications
    )
    logger.info("Message handler initialized")


class StartsWithAnon(Filter):
    """
    Custom filter to check if message starts with @anon prefix.

    Checks both text messages and media captions.
    Case-insensitive matching.
    """

    async def __call__(self, message: Message) -> bool:
        settings = get_settings()
        prefix = settings.command_prefix.lower()

        # Check text or caption
        text = message.text or message.caption or ""
        return text.lower().startswith(prefix)


class InQueue(Filter):
    """
    Custom filter to check if user is in the pending queue.

    Only matches if user has a valid (non-expired) queue entry
    for the current chat.
    """

    async def __call__(self, message: Message) -> bool:
        if not queue_manager:
            return False
        return await queue_manager.check(
            user_id=message.from_user.id,
            chat_id=message.chat.id
        )


# =========================================
# Handler: Direct anonymization mode
# =========================================

@router.message(StartsWithAnon(), F.chat.type.in_({"group", "supergroup"}))
async def handle_anon_command(message: Message) -> None:
    """
    Handle messages starting with @anon prefix.

    Two scenarios:
    1. @anon + content -> immediate anonymization
    2. @anon only -> add to queue for delayed mode

    Args:
        message: Incoming Telegram message
    """
    if not message_processor or not queue_manager:
        logger.error("Handler not initialized!")
        return

    settings = get_settings()
    prefix = settings.command_prefix

    # Extract text after prefix
    text = message.text or message.caption or ""
    cleaned_text = extract_text_after_prefix(text, prefix)

    # Check if there's actual content to anonymize
    has_text = bool(cleaned_text)
    has_media = is_media_with_caption(message) or bool(
        message.voice or message.video_note or message.sticker
    )

    if has_text or has_media:
        # MODE 1: Direct anonymization
        logger.debug("Processing direct anonymization")

        # Delete original first
        deleted = await message_processor.delete_original(message)
        if not deleted:
            return  # Error already sent

        # Send anonymous copy
        await message_processor.send_anonymous(
            message=message,
            text=cleaned_text,
            reply_to_message_id=None  # Will use message's own reply_to
        )
    else:
        # MODE 2: Add to queue for delayed anonymization
        logger.debug("Queuing for delayed anonymization")

        # Get reply_to if this @anon was replying to something
        reply_to = (
            message.reply_to_message.message_id
            if message.reply_to_message else None
        )

        # Delete the @anon message
        await message_processor.delete_original(message)

        # Add to queue
        await queue_manager.add(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            reply_to_message_id=reply_to
        )


# =========================================
# Handler: Delayed anonymization mode
# =========================================

@router.message(
    InQueue(),
    F.chat.type.in_({"group", "supergroup"})
)
async def handle_queued_message(message: Message) -> None:
    """
    Handle follow-up message from user in queue.

    Triggered when user sends any message after @anon
    and is still within the timeout window.

    Args:
        message: Incoming Telegram message
    """
    if not message_processor or not queue_manager:
        logger.error("Handler not initialized!")
        return

    # Don't process if it's another @anon command
    settings = get_settings()
    prefix = settings.command_prefix.lower()
    text = (message.text or message.caption or "").lower()
    if text.startswith(prefix):
        return  # Let the other handler deal with it

    # Check if message has any content
    if not has_any_content(message):
        return

    # Pop from queue (also validates timeout)
    entry = await queue_manager.pop(
        user_id=message.from_user.id,
        chat_id=message.chat.id
    )

    if not entry:
        return  # Expired or already processed

    logger.debug("Processing queued message")

    # Delete original
    deleted = await message_processor.delete_original(message)
    if not deleted:
        return

    # Send anonymous copy with preserved reply
    await message_processor.send_anonymous(
        message=message,
        text=message.text or message.caption,  # Keep original text
        reply_to_message_id=entry.reply_to_message_id
    )
