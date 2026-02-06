"""
Message Processor
=================

Handles the actual sending of anonymized messages.
Supports all Telegram media types with proper error handling.
"""

import logging
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from bot.utils.helpers import get_message_type

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Processes and sends anonymized messages.

    Handles all supported media types and preserves
    reply chains where applicable.

    Attributes:
        bot: Aiogram Bot instance
        error_notifications: Whether to send error messages
    """

    # Error messages for different failure scenarios
    ERRORS = {
        "delete_failed": "⚠️ Failed to anonymize — insufficient permissions",
        "too_old": "⚠️ Telegram doesn't allow deleting this message (>48h)",
        "media_error": "⚠️ Error processing media, please try again",
        "unknown": "⚠️ An error occurred, please try again",
    }

    def __init__(self, bot: Bot, error_notifications: bool = True):
        """
        Initialize message processor.

        Args:
            bot: Aiogram Bot instance
            error_notifications: Send errors to chat
        """
        self.bot = bot
        self.error_notifications = error_notifications

    async def send_anonymous(
            self,
            message: Message,
            text: str | None = None,
            reply_to_message_id: int | None = None
    ) -> bool:
        """
        Send anonymized copy of the message.

        Determines message type and calls appropriate send method.
        Preserves reply chain if specified.

        Args:
            message: Original message to anonymize
            text: Cleaned text/caption (without prefix)
            reply_to_message_id: Message ID to reply to

        Returns:
            True if message was sent successfully
        """
        chat_id = message.chat.id
        reply_to = reply_to_message_id or (
            message.reply_to_message.message_id
            if message.reply_to_message else None
        )

        try:
            msg_type = get_message_type(message)
            logger.info(
                "Processing %s message in chat %d",
                msg_type, chat_id
            )

            # Route to appropriate handler
            handlers = {
                "text": self._send_text,
                "photo": self._send_photo,
                "video": self._send_video,
                "animation": self._send_animation,
                "document": self._send_document,
                "audio": self._send_audio,
                "voice": self._send_voice,
                "video_note": self._send_video_note,
                "sticker": self._send_sticker,
            }

            handler = handlers.get(msg_type)
            if handler:
                await handler(message, text, reply_to)
                return True
            else:
                logger.warning("Unsupported message type: %s", msg_type)
                return False

        except TelegramAPIError as e:
            logger.error("Telegram API error: %s", e)
            if self.error_notifications:
                await self._send_error(chat_id, "unknown")
            return False

    async def delete_original(self, message: Message) -> bool:
        """
        Delete the original message.

        Args:
            message: Message to delete

        Returns:
            True if deletion was successful
        """
        try:
            await message.delete()
            logger.debug(
                "Deleted message %d in chat %d",
                message.message_id, message.chat.id
            )
            return True

        except TelegramForbiddenError:
            logger.warning(
                "No permission to delete in chat %d",
                message.chat.id
            )
            if self.error_notifications:
                await self._send_error(message.chat.id, "delete_failed")
            return False

        except TelegramAPIError as e:
            if "message to delete not found" in str(e).lower():
                # Message already deleted, that's fine
                return True
            if "message can't be deleted" in str(e).lower():
                if self.error_notifications:
                    await self._send_error(message.chat.id, "too_old")
                return False
            logger.error("Delete error: %s", e)
            return False

    # =========================================
    # Private methods for each message type
    # =========================================

    async def _send_text(
            self,
            message: Message,
            text: str | None,
            reply_to: int | None
    ) -> None:
        """Send text message."""
        await self.bot.send_message(
            chat_id=message.chat.id,
            text=text or message.text or "",
            reply_to_message_id=reply_to,
            parse_mode=None  # Preserve original formatting
        )

    async def _send_photo(
            self,
            message: Message,
            text: str | None,
            reply_to: int | None
    ) -> None:
        """Send photo with optional caption."""
        # Get highest resolution photo
        photo = message.photo[-1]
        await self.bot.send_photo(
            chat_id=message.chat.id,
            photo=photo.file_id,
            caption=text,
            reply_to_message_id=reply_to
        )

    async def _send_video(
            self,
            message: Message,
            text: str | None,
            reply_to: int | None
    ) -> None:
        """Send video with optional caption."""
        await self.bot.send_video(
            chat_id=message.chat.id,
            video=message.video.file_id,
            caption=text,
            reply_to_message_id=reply_to
        )

    async def _send_animation(
            self,
            message: Message,
            text: str | None,
            reply_to: int | None
    ) -> None:
        """Send GIF/animation with optional caption."""
        await self.bot.send_animation(
            chat_id=message.chat.id,
            animation=message.animation.file_id,
            caption=text,
            reply_to_message_id=reply_to
        )

    async def _send_document(
            self,
            message: Message,
            text: str | None,
            reply_to: int | None
    ) -> None:
        """Send document with optional caption."""
        await self.bot.send_document(
            chat_id=message.chat.id,
            document=message.document.file_id,
            caption=text,
            reply_to_message_id=reply_to
        )

    async def _send_audio(
            self,
            message: Message,
            text: str | None,
            reply_to: int | None
    ) -> None:
        """Send audio file with optional caption."""
        await self.bot.send_audio(
            chat_id=message.chat.id,
            audio=message.audio.file_id,
            caption=text,
            reply_to_message_id=reply_to
        )

    async def _send_voice(
            self,
            message: Message,
            text: str | None,  # Ignored, voice has no caption
            reply_to: int | None
    ) -> None:
        """Send voice message."""
        await self.bot.send_voice(
            chat_id=message.chat.id,
            voice=message.voice.file_id,
            reply_to_message_id=reply_to
        )

    async def _send_video_note(
            self,
            message: Message,
            text: str | None,  # Ignored, video_note has no caption
            reply_to: int | None
    ) -> None:
        """Send video note (circle video)."""
        await self.bot.send_video_note(
            chat_id=message.chat.id,
            video_note=message.video_note.file_id,
            reply_to_message_id=reply_to
        )

    async def _send_sticker(
            self,
            message: Message,
            text: str | None,  # Ignored, sticker has no caption
            reply_to: int | None
    ) -> None:
        """Send sticker."""
        await self.bot.send_sticker(
            chat_id=message.chat.id,
            sticker=message.sticker.file_id,
            reply_to_message_id=reply_to
        )

    async def _send_error(self, chat_id: int, error_key: str) -> None:
        """
        Send error notification to chat.

        Error message auto-deletes after 10 seconds.

        Args:
            chat_id: Chat to send error to
            error_key: Key for error message lookup
        """
        try:
            error_msg = await self.bot.send_message(
                chat_id=chat_id,
                text=self.ERRORS.get(error_key, self.ERRORS["unknown"])
            )
            # Schedule deletion after 10 seconds
            import asyncio
            asyncio.create_task(self._delayed_delete(error_msg, 10))
        except TelegramAPIError:
            pass  # Can't send error message, ignore

    async def _delayed_delete(self, message: Message, delay: int) -> None:
        """Delete message after delay."""
        import asyncio
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except TelegramAPIError:
            pass