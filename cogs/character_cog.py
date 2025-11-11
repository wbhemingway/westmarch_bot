import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot import DnDBot
from utils.embeds import create_character_embed
from utils.exceptions import CharacterNotFound, InsufficientFunds, ItemNotFound
from utils.models import Character, Item

logger = logging.getLogger(__name__)


class CharacterCog(commands.Cog):
    def __init__(self, bot: DnDBot):
        self.bot = bot
        self.sheet_manager = bot.sheet_manager

    async def item_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """An autocomplete function for items."""
        try:
            items = await self.sheet_manager.get_all_items()
            item_names = [item.name for item in items]
            choices = [
                app_commands.Choice(name=name, value=name)
                for name in item_names
                if current.lower() in name.lower()
            ]
            return choices[:25]
        except Exception as e:
            logger.error(f"Error in item_name_autocomplete: {e}", exc_info=True)
            return []

    @app_commands.command(
        name="character_info",
        description="Check stats of your active character",
    )
    async def character_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            player_id = interaction.user.id

            char_data = await self.sheet_manager.get_character_information(player_id)

            embed = create_character_embed(interaction, char_data, "Character Stats")

            await interaction.followup.send(embed=embed)
        except CharacterNotFound:
            await interaction.followup.send(
                "I couldn't find a character registered to your Discord account. "
                "Contact a staff member to get a character"
            )
        except Exception as e:
            logger.error(
                f"Error in character_info command for {player_id}: {e}", exc_info=True
            )
            await interaction.followup.send(
                "An error occurred while fetching your data. Please contact a staff member."
            )

    @app_commands.command(name="buy_item", description="buy an item for your character")
    @app_commands.autocomplete(item_name=item_autocomplete)
    async def buy_item(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            player_id = interaction.user.id
            item: Item = await self.sheet_manager.get_item(item_name)

            player_info: Character = await self.sheet_manager.get_character_information(
                player_id
            )
            player_gold = player_info.cur

            if player_gold < item.cost:
                raise InsufficientFunds

            await self.sheet_manager.set_character_currency(
                player_id, player_gold - item.cost
            )
            await self.sheet_manager.new_market_log_entry(
                player_info, item, 1, "Player Bought"
            )
            await interaction.followup.send(f"You successfully bought {item.name}!")
        except InsufficientFunds:
            await interaction.followup.send(
                "You don't have enough gold to buy this item."
            )
        except ItemNotFound:
            await interaction.followup.send(f"The item '{item_name}' does not exist.")
        except Exception as e:
            logger.error(
                f"Error in character_info command for {player_id}: {e}", exc_info=True
            )
            await interaction.followup.send(
                "An error occurred while processing your purchase. Please contact a staff member."
            )


async def setup(bot: DnDBot):
    await bot.add_cog(CharacterCog(bot))
