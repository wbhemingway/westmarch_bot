import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
from bot import DnDBot
from utils.embeds import create_character_embed
from utils.exceptions import CharacterAlreadyExists

logger = logging.getLogger(__name__)


class ScribeCog(commands.Cog):
    scribe = app_commands.Group(
        name="scribe", description="Scribe-only commands", guild_only=True
    )

    def __init__(self, bot: DnDBot):
        self.bot = bot
        self.sheet_manager = bot.sheet_manager

    @scribe.command(
        name="create_character",
        description="Creates a character for a player",
    )
    @app_commands.describe(
        new_user="The player to make a character for",
        char_name="The name of the new character",
        start_lvl="lvl for new character, default is 5",
    )
    @app_commands.checks.has_role(config.SCRIBE_ROLE_ID)
    async def create_character(
        self,
        interaction: discord.Interaction,
        new_user: discord.Member,
        char_name: str,
        start_lvl: Optional[int],
    ):
        await interaction.response.defer(ephemeral=True)
        player_id = new_user.id
        char_data = await self.sheet_manager.create_new_character(
            char_name, player_id, start_lvl
        )
        embed = create_character_embed(
            interaction, char_data, "New character successfully created!"
        )
        await interaction.followup.send(embed=embed)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handles errors for all commands in this cog."""
        user_error_map = {
            app_commands.MissingRole: "You do not have the required 'Scribe' role to use this command.",
            CharacterAlreadyExists: "This user already has a character. Cannot create a new one.",
        }
        original_error = getattr(error, "original", error)

        for error_type, message in user_error_map.items():
            if isinstance(original_error, error_type):
                await interaction.followup.send(message, ephemeral=True)
                return

        logger.error(
            f"An unhandled error occurred in ScribeCog: {error}", exc_info=True
        )
        await interaction.followup.send(
            "An error occurred while making the character. Please contact a staff member.",
            ephemeral=True,
        )


async def setup(bot: DnDBot):

    await bot.add_cog(ScribeCog(bot))
