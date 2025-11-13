import discord

from .models import Character


def create_character_embed(
    interaction: discord.Interaction, char_data: Character, title: str
) -> discord.Embed:
    """Creates a standardized embed for character information."""
    embed = discord.Embed(title=title, color=discord.Color.blue())
    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.avatar.url
    )

    embed.add_field(
        name="Name",
        value=char_data.name,
        inline=True,
    )
    embed.add_field(
        name="Level",
        value=str(char_data.lvl),
        inline=True,
    )
    embed.add_field(name="XP", value=str(char_data.xp), inline=True)
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
    embed.add_field(name="Player ID", value=f"`{char_data.player_id}`", inline=False)
    return embed


def create_items_embed(
    interaction: discord.Interaction,
    char_data: Character,
    items: dict[str, int],
) -> discord.Embed:
    """Creates a standardized embed for character items."""
    embed = discord.Embed(title=f"{char_data.name}'s Items", color=discord.Color.blue())
    embed.set_author(
        name=interaction.user.display_name, icon_url=interaction.user.avatar.url
    )
    embed.add_field(
        name=char_data.name,
        value=f"`{char_data.char_id}`",
        inline=False,
    )
    item_list = []
    for item_name, quantity in items.items():
        item_list.append(f"{item_name}: {quantity}")
    items_string = "\n".join(item_list)
    embed.add_field(name="Items", value=items_string, inline=False)
    return embed
