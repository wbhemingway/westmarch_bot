import asyncio
import logging
import logging.handlers
import os

import discord
from dotenv import load_dotenv

from bot import DnDBot


def setup_logging():
    """Configures the root logger for the bot."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.handlers.RotatingFileHandler(
                "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


async def main():

    logger = setup_logging()

    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        logger.critical(
            "FATAL: DISCORD_TOKEN not found in .env file. Bot cannot start."
        )
        return

    bot = DnDBot()

    try:
        logger.info("Bot is starting...")
        await bot.start(TOKEN)
    except discord.LoginFailure:
        logger.critical("FATAL: Invalid Discord token. Please check your .env file.")
    except Exception as e:
        logger.critical(
            f"FATAL: Bot crashed with an unhandled exception: {e}", exc_info=True
        )
    finally:
        logger.warning("Bot is shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
