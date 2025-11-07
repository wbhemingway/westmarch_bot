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
