import discord
import logging

logger = logging.getLogger(__name__)

def build_embed(title=None, description=None, color=None, fields=None, footer=None, thumbnail=None, image=None, author=None, timestamp=None):
    """
    Build a Discord embed with the given parameters.
    
    Args:
        title (str, optional): Embed title
        description (str, optional): Embed description
        color (discord.Color, optional): Embed color
        fields (list, optional): List of field dictionaries with name, value, and inline keys
        footer (dict, optional): Footer dictionary with text and icon_url keys
        thumbnail (str, optional): URL for the thumbnail
        image (str, optional): URL for the image
        author (dict, optional): Author dictionary with name, url, and icon_url keys
        timestamp (datetime, optional): Timestamp for the embed
    
    Returns:
        discord.Embed: The constructed embed
    """
    embed = discord.Embed()
    
    if title:
        embed.title = title
    
    if description:
        embed.description = description
    
    if color:
        embed.color = color
    else:
        embed.color = discord.Color.blue()
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', 'Field'),
                value=field.get('value', 'No value'),
                inline=field.get('inline', False)
            )
    
    if footer:
        embed.set_footer(
            text=footer.get('text', ''),
            icon_url=footer.get('icon_url')
        )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    if author:
        embed.set_author(
            name=author.get('name', ''),
            url=author.get('url'),
            icon_url=author.get('icon_url')
        )
    
    if timestamp:
        embed.timestamp = timestamp
    
    return embed
