import logging
import os

import discord
from discord.ext import commands

import config
from utils.sheet_manager import SheetManager


class DnDBot(commands.Bot):
    """
    The main bot class, inheriting from commands.Bot.
    This holds the sheet_manager and setup logic.
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(command_prefix="!", intents=intents)

        self.sheet_manager: SheetManager | None = None
        self.logger = logging.getLogger(__name__)

    async def on_ready(self):
        """Called when the bot is logged in and ready."""
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info("Bot is online and ready!")

    async def load_cogs(self):
        """Finds and loads all cog files in the 'cogs' directory."""
        self.logger.info("Loading cogs...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    self.logger.info(f"Successfully loaded cog: {filename}")
                except Exception:
                    self.logger.error(f"Failed to load cog {filename}", exc_info=True)
        self.logger.info("All cogs loaded.")

    async def setup_hook(self):
        """Runs before the bot fully connects."""
        self.sheet_manager = SheetManager(
            config.CREDENTIALS_FILE, config.GOOGLE_SHEET_NAME
        )

        try:
            self.logger.info("Attempting to connect to Google Sheets...")
            await self.sheet_manager._connect()
            self.logger.info("SheetManager connection successful.")
        except Exception as e:
            self.logger.critical(
                f"FATAL: Failed to connect to Google Sheets: {e}", exc_info=True
            )
            await self.close()

        await self.load_cogs()

        try:
            self.logger.info("Syncing application (slash) commands...")
            synced = await self.tree.sync()
            self.logger.info(f"Synced {len(synced)} application commands.")
        except Exception:
            self.logger.error("Failed to sync application commands", exc_info=True)
