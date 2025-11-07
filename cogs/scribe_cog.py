import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from bot import DnDBot
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
    )
    @app_commands.checks.has_role(config.SCRIBE_ROLE_ID)
    async def create_character(
        self, interaction: discord.Interaction, new_user: discord.Member, char_name: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            player_id = new_user.id

            char_data = await self.sheet_manager.create_new_character(
                char_name,
                player_id,
                config.STARTING_CURRENCY,
                config.STARTING_EXPERIENCE,
                config.STARTING_LEVEL,
            )

            embed = discord.Embed(
                title="New character successflly created!", color=discord.Color.blue()
            )
            embed.set_author(
                name=interaction.user.display_name, icon_url=interaction.user.avatar.url
            )

            embed.add_field(
                name="Name",
                value=char_data[self.sheet_manager.C_H_CHAR_NAME],
                inline=True,
            )
            embed.add_field(
                name="Level",
                value=str(char_data[self.sheet_manager.C_H_LEVEL]),
                inline=True,
            )
            embed.add_field(
                name="XP", value=str(char_data[self.sheet_manager.C_H_XP]), inline=True
            )
            embed.add_field(
                name="Currency",
                value=f"{char_data[self.sheet_manager.C_H_CURRENCY]}",
                inline=True,
            )
            embed.add_field(
                name="Character ID",
                value=f"`{char_data[self.sheet_manager.C_H_CHAR_ID]}`",
                inline=False,
            )
            embed.add_field(
                name="Player ID",
                value=f"`{char_data[self.sheet_manager.C_H_PLAYER_ID]}`",
                inline=False,
            )

            await interaction.followup.send(embed=embed)
        except CharacterAlreadyExists:
            await interaction.followup.send(
                "This user already has a character. Cannot create a new one."
            )
        except Exception as e:
            logger.error(
                f"Error in create_character command for {new_user.id}: {e}",
                exc_info=True,
            )
            await interaction.followup.send(
                "An error occurred while making the character. Please contact a staff member."
            )


async def setup(bot: DnDBot):

    await bot.add_cog(ScribeCog(bot))
