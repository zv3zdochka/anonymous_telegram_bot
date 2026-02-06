"""
Configuration Module
====================

Handles all configuration settings using pydantic-settings.
Loads values from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        bot_token: Telegram Bot API token from @BotFather
        command_prefix: Trigger word for anonymization (default: @anon)
        queue_timeout: Seconds to wait for follow-up message (default: 60)
        error_notifications: Whether to send error messages to chat
        redis_url: Optional Redis URL for distributed queue
    """

    bot_token: str = Field(
        ...,
        description="Telegram Bot API token"
    )

    command_prefix: str = Field(
        default="@anon",
        description="Command prefix to trigger anonymization"
    )

    queue_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Queue timeout in seconds"
    )

    error_notifications: bool = Field(
        default=True,
        description="Show error notifications in chat"
    )

    redis_url: str | None = Field(
        default=None,
        description="Redis URL for distributed queue"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses LRU cache to avoid re-reading environment variables
    on every access. Thread-safe singleton pattern.

    Returns:
        Settings: Application configuration object
    """
    return Settings()
