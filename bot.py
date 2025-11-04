import os

from discord.ext import commands
from dotenv import load_dotenv

from utils.sheet_manager import SheetManager

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")


class DnDBot(commands.bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sheet_manager = SheetManager("credentials.json", SHEET_NAME)
