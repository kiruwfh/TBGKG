import discord
from discord.ext import commands
import os
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_bot():
    """Initialize and configure the Discord bot."""
    # Set intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    
    # Create bot instance with a prefix that won't be used (we'll only use slash commands)
    bot = commands.Bot(command_prefix="/", intents=intents)
    
    # Add channel IDs to bot for shared access across cogs
    bot.log_channel_id = 1299929217328349234  # Канал для логов операций с ключами
    bot.status_channel_id = 1363695347699810515  # Канал для сообщений о статусе бота
    
    @bot.event
    async def on_ready():
        """Event triggered when the bot is ready and connected to Discord."""
        logger.info(f"Bot is ready! Logged in as {bot.user.name} ({bot.user.id})")
        
        # Load cogs
        await load_extensions(bot)
        
        # Sync application commands with Discord
        try:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            
        # Set bot activity status
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="premium keys"
        ))
        
        # Send startup message to status channel
        try:
            status_channel = bot.get_channel(bot.status_channel_id)
            if status_channel:
                startup_embed = discord.Embed(
                    title="🤖 Bot Online",
                    description="Premium key management bot is now online and ready to use!",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                startup_embed.set_footer(text=f"Bot ID: {bot.user.id}")
                await status_channel.send(embed=startup_embed)
                logger.info(f"Sent startup message to status channel {bot.status_channel_id}")
            else:
                logger.warning(f"Status channel with ID {bot.status_channel_id} not found")
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")

    @bot.event
    async def on_command_error(ctx, error):
        """Global error handler for bot commands."""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I don't have the necessary permissions to execute this command.")
        else:
            logger.error(f"Command error: {error}")
            await ctx.send(f"An error occurred: {error}")
    
    return bot

async def load_extensions(bot):
    """Load all cogs for the bot."""
    cogs = [
        "cogs.key_management",
        "cogs.admin_commands"
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"Loaded extension: {cog}")
        except Exception as e:
            logger.error(f"Failed to load extension {cog}: {e}")
