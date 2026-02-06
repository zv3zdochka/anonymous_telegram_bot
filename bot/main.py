"""
Main Entry Point
================

Application entry point. Sets up the bot, registers handlers,
and starts polling for updates.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.handlers.message_handler import router, setup_handler
from bot.services.queue_manager import QueueManager


# =========================================
# Logging Configuration
# =========================================

def setup_logging() -> None:
    """
    Configure logging for the application.

    Sets up formatted console output with timestamps.
    Log level is INFO for production, DEBUG for development.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Reduce noise from external libraries
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


# =========================================
# Lifespan Management
# =========================================

@asynccontextmanager
async def lifespan(bot: Bot, queue: QueueManager):
    """
    Async context manager for application lifespan.

    Handles startup and shutdown tasks:
    - Start queue manager
    - Set bot commands
    - Cleanup on exit

    Args:
        bot: Aiogram Bot instance
        queue: Queue manager instance
    """
    logger = logging.getLogger(__name__)

    # Startup
    logger.info("Starting Anonymous Bot v3.0...")
    await queue.start()

    # Get bot info for logging
    bot_info = await bot.get_me()
    logger.info("Bot started: @%s (ID: %d)", bot_info.username, bot_info.id)

    yield

    # Shutdown
    logger.info("Shutting down...")
    await queue.stop()
    await bot.session.close()
    logger.info("Goodbye!")


# =========================================
# Main Function
# =========================================

async def main() -> None:
    """
    Main async function.

    Creates bot instance, sets up handlers, and starts polling.
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    settings = get_settings()

    # Create bot instance
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    # Create queue manager
    queue = QueueManager(timeout=settings.queue_timeout)

    # Create dispatcher and register handlers
    dp = Dispatcher()
    dp.include_router(router)

    # Initialize handler dependencies
    setup_handler(bot=bot, queue=queue)

    # Run with lifespan management
    async with lifespan(bot, queue):
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=["message"],
            drop_pending_updates=True
        )


# =========================================
# Entry Point
# =========================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)