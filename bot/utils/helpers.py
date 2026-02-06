"""
Helper Functions
================

Utility functions for text processing and message analysis.
"""

import re
from aiogram.types import Message


def extract_text_after_prefix(text: str | None, prefix: str) -> str | None:
    """
    Extract and clean text after the command prefix.

    Removes the prefix and any leading/trailing whitespace.
    Returns None if no meaningful text remains.

    Args:
        text: Original message text or caption
        prefix: Command prefix to remove (e.g., "@anon")

    Returns:
        Cleaned text without prefix, or None if empty

    Examples:
        >>> extract_text_after_prefix("@anon Hello!", "@anon")
        'Hello!'
        >>> extract_text_after_prefix("@anon", "@anon")
        None
        >>> extract_text_after_prefix("@anon   Spaced  ", "@anon")
        'Spaced'
    """
    if not text:
        return None

    # Case-insensitive prefix removal
    pattern = re.compile(re.escape(prefix), re.IGNORECASE)
    cleaned = pattern.sub("", text, count=1).strip()

    return cleaned if cleaned else None


def is_media_with_caption(message: Message) -> bool:
    """
    Check if message contains media that supports captions.

    Some media types (stickers, voice, video_note) don't support
    captions in Telegram API.

    Args:
        message: Telegram message object

    Returns:
        True if message has media with caption support
    """
    caption_media = (
        message.photo,
        message.video,
        message.animation,
        message.document,
        message.audio,
    )
    return any(caption_media)


def has_any_content(message: Message) -> bool:
    """
    Check if message has any sendable content.

    Args:
        message: Telegram message object

    Returns:
        True if message contains text or any media type
    """
    return bool(
        message.text or
        message.photo or
        message.video or
        message.animation or
        message.document or
        message.audio or
        message.voice or
        message.video_note or
        message.sticker
    )


def get_message_type(message: Message) -> str:
    """
    Determine the type of message content.

    Args:
        message: Telegram message object

    Returns:
        String identifier of message type
    """
    if message.text:
        return "text"
    elif message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.animation:
        return "animation"
    elif message.document:
        return "document"
    elif message.audio:
        return "audio"
    elif message.voice:
        return "voice"
    elif message.video_note:
        return "video_note"
    elif message.sticker:
        return "sticker"
    else:
        return "unknown"
