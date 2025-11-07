import discord
from discord import app_commands
from discord.ext import commands

import logging

from utils.exceptions import CharacterNotFound
from bot import DnDBot

logger = logging.getLogger(__name__)
class CharacterCog(commands.Cog):
    def __init__(self, bot: DnDBot):
        self.bot = bot
        self.sheet_manager = bot.sheet_manager

    @app_commands.command(
        name="character_info",
        description="Check stats of your active character",
    )
    async def character_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            player_id = interaction.user.id

            char_data = await self.sheet_manager.get_character_information(
                player_id
            )


            char_name = char_data.name

            embed = discord.Embed(
                title=f"Character Stats: {char_name}", color=discord.Color.blue()
            )
            embed.set_author(
                name=interaction.user.display_name, icon_url=interaction.user.avatar.url
            )

            embed.add_field(
                name="Level", value=str(char_data.lvl), inline=True
            )
            embed.add_field(
                name="XP", value=str(char_data.xp), inline=True
            )
            embed.add_field(
                name="Currency",
                value=f"{char_data.cur}",
                inline=True,
            )

            embed.add_field(
                name="Character ID",
                value=f"`{char_data.char_id}`",
                inline=False,
            )

            await interaction.followup.send(embed=embed)
        except CharacterNotFound:
            await interaction.followup.send(
                "I couldn't find a character registered to your Discord account. "
                "Contact a staff member to get a character"
            )
        except Exception as e:
            logger.error(f"Error in character_info command for {player_id}: {e}", exc_info=True)
            await interaction.followup.send(
                "An error occurred while fetching your data. Please contact a staff member."
            )


async def setup(bot: DnDBot):
    await bot.add_cog(CharacterCog(bot))
