import logging

import discord
from discord import app_commands
from discord.ext import commands

from bot import DnDBot
from utils.embeds import create_character_embed, create_items_embed
from utils.exceptions import CharacterNotFound, InsufficientFunds, ItemNotFound

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
        player_id = interaction.user.id
        char_data = await self.sheet_manager.get_character_information(player_id)
        embed = create_character_embed(interaction, char_data, "Character Stats")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="buy_item", description="buy an item for your character")
    @app_commands.autocomplete(item_name=item_autocomplete)
    async def buy_item(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer(ephemeral=True)
        try:
            player_id = interaction.user.id
            item = await self.sheet_manager.get_item(item_name)

            player_info = await self.sheet_manager.get_character_information(player_id)
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
        except (InsufficientFunds, ItemNotFound) as e:
            await interaction.followup.send(str(e))

    @app_commands.command(
        name="character_items",
        description="check the items that your character currently has",
    )
    async def character_items(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player_id = interaction.user.id
        character_information = await self.sheet_manager.get_character_information(
            player_id
        )
        records = await self.sheet_manager.get_all_market_log_entries()
        player_records = [
            record
            for record in records
            if record.char_id == character_information.char_id
        ]
        item_counter = {}
        for record in player_records:
            item_counter[record.item_name] = (
                item_counter.get(record.item_name, 0) + record.quantity
            )
        items_embed = create_items_embed(
            interaction, character_information, item_counter
        )
        await interaction.followup.send(embed=items_embed)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        """Handles errors for all commands in this cog."""
        user_error_map = {
            CharacterNotFound: "I couldn't find a character registered to your Discord account. Contact a staff member to get a character.",
            InsufficientFunds: "You don't have enough gold for that.",
            ItemNotFound: "That item could not be found.",
        }

        original_error = getattr(error, "original", error)

        for error_type, message in user_error_map.items():
            if isinstance(original_error, error_type):
                await interaction.followup.send(message, ephemeral=True)
                return

        logger.error(
            f"An unhandled error occurred in CharacterCog: {error}", exc_info=True
        )
        await interaction.followup.send(
            "An unexpected error occurred. Please contact a staff member.",
            ephemeral=True,
        )


async def setup(bot: DnDBot):
    await bot.add_cog(CharacterCog(bot))
