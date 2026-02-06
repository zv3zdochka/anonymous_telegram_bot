"""
Queue Manager
=============

Manages the pending anonymization queue for delayed mode.
Privacy-focused: no user identifiers in logs.
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

    Note: This data is kept only in memory and auto-expires.
    Nothing is persisted to disk or external storage.
    """
    user_id: int
    chat_id: int
    expires_at: datetime
    reply_to_message_id: int | None = None


class QueueManager:
    """
    Thread-safe queue manager for delayed anonymization.

    Privacy guarantees:
    - All data is in-memory only (no persistence)
    - Entries auto-expire after timeout
    - No user identifiers are logged
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

        # No logging of user/chat IDs for privacy
        logger.debug("Entry added to queue")

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
            logger.debug("Entry popped from queue")
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
            except Exception:
                # Silent error handling - no details logged
                logger.error("Cleanup error occurred")

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
