"""
Queue Manager
=============

Manages the pending anonymization queue for delayed mode.
Supports both in-memory and Redis-based storage.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueueEntry:
    """
    Represents a pending anonymization request.

    Attributes:
        user_id: Telegram user ID
        chat_id: Chat where request was made
        expires_at: When this entry becomes invalid
        reply_to_message_id: Optional message ID to reply to
    """
    user_id: int
    chat_id: int
    expires_at: datetime
    reply_to_message_id: int | None = None


class QueueManager:
    """
    Thread-safe queue manager for delayed anonymization.

    Uses composite key (chat_id, user_id) to allow same user
    to have pending requests in different chats.

    Attributes:
        timeout: Seconds before queue entry expires
        _queue: Internal storage dict
        _cleanup_task: Background cleanup task
    """

    def __init__(self, timeout: int = 60):
        """
        Initialize queue manager.

        Args:
            timeout: Seconds before entries expire
        """
        self.timeout = timeout
        self._queue: Dict[tuple[int, int], QueueEntry] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Queue manager started with %ds timeout", self.timeout)

    async def stop(self) -> None:
        """Stop the background cleanup task gracefully."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Queue manager stopped")

    async def add(
            self,
            user_id: int,
            chat_id: int,
            reply_to_message_id: int | None = None
    ) -> None:
        """
        Add user to the pending queue.

        If user already has a pending request in this chat,
        it will be replaced with a new one.

        Args:
            user_id: Telegram user ID
            chat_id: Chat ID where request was made
            reply_to_message_id: Optional message to reply to
        """
        key = (chat_id, user_id)
        expires_at = datetime.now() + timedelta(seconds=self.timeout)

        async with self._lock:
            self._queue[key] = QueueEntry(
                user_id=user_id,
                chat_id=chat_id,
                expires_at=expires_at,
                reply_to_message_id=reply_to_message_id
            )

        logger.debug(
            "Added to queue: user=%d chat=%d expires=%s",
            user_id, chat_id, expires_at.isoformat()
        )

    async def pop(self, user_id: int, chat_id: int) -> QueueEntry | None:
        """
        Remove and return queue entry if exists and not expired.

        Args:
            user_id: Telegram user ID
            chat_id: Chat ID to check

        Returns:
            QueueEntry if found and valid, None otherwise
        """
        key = (chat_id, user_id)

        async with self._lock:
            entry = self._queue.pop(key, None)

        if entry and entry.expires_at > datetime.now():
            logger.debug("Popped from queue: user=%d chat=%d", user_id, chat_id)
            return entry

        return None

    async def check(self, user_id: int, chat_id: int) -> bool:
        """
        Check if user has a valid pending request.

        Args:
            user_id: Telegram user ID
            chat_id: Chat ID to check

        Returns:
            True if user has valid pending request
        """
        key = (chat_id, user_id)

        async with self._lock:
            entry = self._queue.get(key)

        return entry is not None and entry.expires_at > datetime.now()

    async def _cleanup_loop(self) -> None:
        """
        Background task to remove expired entries.

        Runs every 10 seconds to clean up expired queue entries.
        This prevents memory leaks from abandoned requests.
        """
        while True:
            try:
                await asyncio.sleep(10)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Cleanup error: %s", e)

    async def _cleanup_expired(self) -> None:
        """Remove all expired entries from queue."""
        now = datetime.now()
        expired_keys = []

        async with self._lock:
            for key, entry in self._queue.items():
                if entry.expires_at <= now:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._queue[key]

        if expired_keys:
            logger.debug("Cleaned up %d expired entries", len(expired_keys))