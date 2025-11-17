import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from bot import DnDBot
from utils.exceptions import CharacterNotFound

logger = logging.getLogger(__name__)


class DMCog(commands.Cog):
    dm = app_commands.Group(name="dm", description="DM-only commands", guild_only=True)

    def __init__(self, bot: DnDBot):
        self.bot = bot
        self.sheet_manager = bot.sheet_manager

    @dm.command(
        name="log_game",
        description="Log a completed game into the sheet",
    )
    @app_commands.describe(
        p1="Player 1",
        p2="Player 2",
        p3="Player 3",
        p4="Player 4",
        p5="Player 5",
        p6="Player 6",
    )
    @app_commands.checks.has_role(config.DM_ROLE_ID)
    async def log_game(
        self,
        interaction: discord.Interaction,
        p1: discord.Member,
        p2: discord.Member,
        p3: discord.Member,
        p4: Optional[discord.Member],
        p5: Optional[discord.Member],
        p6: Optional[discord.Member],
    ):
        await interaction.response.defer(ephemeral=True)

        player_ids = [p.id for p in [p1, p2, p3, p4, p5, p6] if p is not None]
        characters = await self.sheet_manager.get_characters_by_ids(player_ids)

        await self.sheet_manager.log_game(interaction.user.id, characters)
        await interaction.followup.send(f"Game logged for {len(characters)} players.")

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handles errors for all commands in this cog."""
        user_error_map = {
            app_commands.MissingRole: "You do not have the required 'DM' role to use this command.",
            CharacterNotFound: "One of the specified players does not have a character. Please get a scribe to create one for them.",
        }
        original_error = getattr(error, "original", error)

        for error_type, message in user_error_map.items():
            if isinstance(original_error, error_type):
                await interaction.followup.send(message, ephemeral=True)
                return

        logger.error(f"An unhandled error occurred in DMCog: {error}", exc_info=True)
        await interaction.followup.send(
            "An unexpected error occurred. Please contact a staff member.",
            ephemeral=True,
        )


async def setup(bot: DnDBot):

    await bot.add_cog(DMCog(bot))
