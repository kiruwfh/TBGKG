import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from utils.embed_builder import build_embed
from utils.time_utils import parse_duration, format_timestamp, format_duration
from data.keys_database import KeysDatabase

logger = logging.getLogger(__name__)

class KeyManagement(commands.Cog):
    """Cog for managing premium role keys generation and redemption."""
    
    def __init__(self, bot):
        self.bot = bot
        self.keys_db = KeysDatabase()
        self.premium_role_id = 1302915891444580372  # Premium role ID from request
        
    async def log_to_channel(self, embed):
        """Send log embed to the designated log channel."""
        try:
            log_channel = self.bot.get_channel(self.bot.log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
            else:
                logger.warning(f"Log channel with ID {self.bot.log_channel_id} not found")
        except Exception as e:
            logger.error(f"Error sending log to channel: {e}")
    
    @app_commands.command(name="generate", description="Generate a premium role key with specified duration")
    @app_commands.describe(duration="Duration format: 1d, 7d, 1w, 1m, etc.")
    @app_commands.default_permissions(manage_roles=True)
    async def generate_key(self, interaction: discord.Interaction, duration: str):
        """Generate a new premium key with the specified duration."""
        # Importing here to avoid circular imports
        try:
            from utils.sync_keys import sync_db_to_json
        except ImportError:
            pass
        await interaction.response.defer(ephemeral=True)
        
        # Parse duration string
        try:
            duration_seconds = parse_duration(duration)
            if duration_seconds <= 0:
                error_embed = build_embed(
                    title="❌ Invalid Duration",
                    description="Duration must be positive.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return
                
            expiry_date = datetime.now() + timedelta(seconds=duration_seconds)
        except ValueError as e:
            error_embed = build_embed(
                title="❌ Invalid Format",
                description=f"Invalid duration format: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        
        # Generate unique key
        key = str(uuid.uuid4())
        
        # Store key in database
        self.keys_db.add_key(key, duration_seconds, expiry_date, interaction.user.id, None)
        
        # Sync to database
        try:
            from utils.sync_keys import sync_db_to_json
            sync_db_to_json()
        except Exception as e:
            logger.error(f"Error syncing to database: {e}")
        
        # Calculate exact expiration time and relative time
        now = datetime.now()
        time_until_expiry = expiry_date - now
        days = time_until_expiry.days
        hours = time_until_expiry.seconds // 3600
        minutes = (time_until_expiry.seconds // 60) % 60
        
        # Format relative time description
        relative_time = []
        if days > 0:
            relative_time.append(f"{days} {'day' if days == 1 else 'days'}")
        if hours > 0 or days > 0:
            relative_time.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
        if minutes > 0 or hours > 0 or days > 0:
            relative_time.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
        
        relative_time_str = ", ".join(relative_time)
        
        # Create and send embed to user via DM with improved visual appearance
        key_embed = build_embed(
            title="🔑 Premium Key Generated",
            description=f"You have successfully generated a premium key!\nShare this key with someone to give them premium access.",
            color=discord.Color.gold(),
            fields=[
                {
                    'name': '🔐 Key',
                    'value': f"```{key}```\n*This is the full key that needs to be entered*",
                    'inline': False
                },
                {
                    'name': '⏱️ Duration',
                    'value': f"`{format_duration(duration_seconds)}` ({relative_time_str})",
                    'inline': False
                },
                {
                    'name': '📅 Valid Until',
                    'value': f"`{format_timestamp(expiry_date)}`",
                    'inline': True
                },
                {
                    'name': '🕑 Generated At',
                    'value': f"`{format_timestamp(now)}`",
                    'inline': True
                },
                {
                    'name': '📋 How to Redeem',
                    'value': "Use the `/redeem` command in the server and enter this key when prompted.",
                    'inline': False
                }
            ],
            footer={
                'text': f'Generated by {interaction.user.display_name}',
                'icon_url': interaction.user.display_avatar.url
            },
            timestamp=datetime.now()
        )
        
        confirmation_embed = build_embed(
            title="✅ Key Generated Successfully",
            description="A premium key has been generated and sent to your DMs!",
            color=discord.Color.green()
        )
        
        try:
            await interaction.user.send(embed=key_embed)
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
            logger.info(f"User {interaction.user.name} (ID: {interaction.user.id}) generated a premium key: {key}")
            
            # Log key generation to the log channel
            log_embed = build_embed(
                title="🔑 Premium Key Generated",
                description=f"A new premium key has been generated by an admin.",
                color=discord.Color.gold(),
                fields=[
                    {
                        'name': '👤 Generated By',
                        'value': f"{interaction.user.mention} (`{interaction.user.name}` ID: `{interaction.user.id}`)",
                        'inline': False
                    },
                    {
                        'name': '⏱️ Duration',
                        'value': f"`{format_duration(duration_seconds)}`",
                        'inline': True
                    },
                    {
                        'name': '📅 Expires',
                        'value': f"`{format_timestamp(expiry_date)}`",
                        'inline': True
                    },
                    {
                        'name': '🔐 Key ID',
                        'value': f"`{key[:8]}...{key[-8:]}`",
                        'inline': False
                    }
                ],
                footer={
                    'text': f'Server: {interaction.guild.name}',
                    'icon_url': interaction.guild.icon.url if interaction.guild.icon else None
                },
                timestamp=datetime.now()
            )
            await self.log_to_channel(log_embed)
            
        except discord.Forbidden:
            # If we can't DM the user, show the key in the channel response
            error_note = build_embed(
                title="⚠️ DM Error",
                description="I couldn't send you a DM. Here's your key (only visible to you):",
                color=discord.Color.yellow()
            )
            await interaction.followup.send(embeds=[error_note, key_embed], ephemeral=True)
    
    @app_commands.command(name="redeem", description="Redeem a premium role key")
    async def redeem_key(self, interaction: discord.Interaction):
        """Command to redeem a premium key."""
        # Create a more visually appealing embed with instructions
        embed = build_embed(
            title="🔓 Redeem Premium Key",
            description="Enter your premium key to activate your premium role and unlock exclusive benefits!",
            color=discord.Color.blue(),
            fields=[
                {
                    'name': '📝 Instructions',
                    'value': "1. Enter your 36-character premium key\n"
                            "2. Your premium role will be activated immediately\n"
                            "3. Enjoy your premium benefits!",
                    'inline': False
                }
            ],
            footer={
                'text': 'Your key will be kept confidential and is only visible to you'
            }
        )
        
        # Create modal for key input
        class KeyRedeemModal(discord.ui.Modal, title="Redeem Premium Key"):
            key_input = discord.ui.TextInput(
                label="Premium Key",
                placeholder="Enter your premium key here",
                required=True,
                min_length=36,  # UUID length
                max_length=36
            )
            
            def __init__(self, cog):
                super().__init__()
                self.cog = cog
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                await modal_interaction.response.defer(ephemeral=True)
                
                key = self.key_input.value.strip()
                
                # Validate key
                key_data = self.cog.keys_db.get_key(key)
                if not key_data:
                    error_embed = build_embed(
                        title="❌ Key Redemption Failed",
                        description="The key you entered is invalid or does not exist.",
                        color=discord.Color.red(),
                        fields=[
                            {
                                'name': '❓ What happened?',
                                'value': "The key you entered was not found in our database. Double-check that you've entered the correct key.",
                                'inline': False
                            },
                            {
                                'name': '🔍 Key Entered',
                                'value': f"`{key[:8]}...{key[-8:] if len(key) > 16 else key}`",
                                'inline': False
                            }
                        ],
                        footer={
                            'text': 'If you believe this is an error, please contact an administrator'
                        }
                    )
                    await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                    
                    # Log failed redemption attempt to detailed log channel
                    try:
                        log_channel = self.cog.bot.get_channel(self.cog.bot.log_channel_id)
                        if log_channel:
                            log_embed = build_embed(
                                title="❌ Failed Key Redemption Attempt",
                                description=f"A user attempted to redeem a non-existent key",
                                color=discord.Color.red(),
                                fields=[
                                    {
                                        'name': '👤 User',
                                        'value': f"{modal_interaction.user.mention} (`{modal_interaction.user.name}` ID: `{modal_interaction.user.id}`)",
                                        'inline': False
                                    },
                                    {
                                        'name': '🔑 Key Fragment',
                                        'value': f"`{key[:8]}...{key[-8:] if len(key) > 16 else key}`",
                                        'inline': False
                                    },
                                    {
                                        'name': '📍 Server',
                                        'value': f"{modal_interaction.guild.name} (ID: `{modal_interaction.guild.id}`)",
                                        'inline': False
                                    }
                                ],
                                timestamp=datetime.now()
                            )
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        logger.error(f"Error sending key redemption failure log: {e}")
                    
                    return
                
                # Check if key is already redeemed
                if key_data.get('user_id_redeemed'):
                    redeemer_id = key_data.get('user_id_redeemed')
                    # Try to get the username of the person who redeemed
                    redeemer_name = "another user"
                    
                    try:
                        # Try to find the user in any mutual guild
                        redeemer = None
                        for guild in self.cog.bot.guilds:
                            redeemer = guild.get_member(redeemer_id)
                            if redeemer:
                                redeemer_name = redeemer.name
                                break
                    except:
                        pass
                    
                    error_embed = build_embed(
                        title="❌ Key Already Redeemed",
                        description=f"This premium key has already been activated by {redeemer_name}.",
                        color=discord.Color.red(),
                        fields=[
                            {
                                'name': '❓ What happened?',
                                'value': "Each premium key can only be used once. This key has already been redeemed and is no longer valid.",
                                'inline': False
                            },
                            {
                                'name': '🔑 Key',
                                'value': f"`{key[:8]}...{key[-8:]}`",
                                'inline': False
                            },
                            {
                                'name': '🔄 What can you do?',
                                'value': "Ask an administrator to generate a new premium key for you using the `/generate` command.",
                                'inline': False
                            }
                        ],
                        footer={
                            'text': 'If you believe this is an error, please contact an administrator'
                        }
                    )
                    await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                    
                    # Log duplicate redemption attempt
                    try:
                        log_channel = self.cog.bot.get_channel(self.cog.bot.log_channel_id)
                        if log_channel:
                            log_embed = build_embed(
                                title="⚠️ Duplicate Key Redemption Attempt",
                                description=f"A user attempted to redeem an already used key",
                                color=discord.Color.gold(),
                                fields=[
                                    {
                                        'name': '👤 User Attempting',
                                        'value': f"{modal_interaction.user.mention} (`{modal_interaction.user.name}` ID: `{modal_interaction.user.id}`)",
                                        'inline': False
                                    },
                                    {
                                        'name': '👤 Original Redeemer',
                                        'value': f"<@{redeemer_id}> (ID: `{redeemer_id}`)",
                                        'inline': False
                                    },
                                    {
                                        'name': '🔑 Key',
                                        'value': f"`{key}`",
                                        'inline': False
                                    }
                                ],
                                timestamp=datetime.now()
                            )
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        logger.error(f"Error sending duplicate redemption log: {e}")
                    
                    return
                
                # Check if key is expired
                now = datetime.now()
                expiry_date = key_data.get('expiry_date')
                if now > expiry_date:
                    # Calculate how long ago it expired
                    time_since_expiry = now - expiry_date
                    days_ago = time_since_expiry.days
                    hours_ago = time_since_expiry.seconds // 3600
                    minutes_ago = (time_since_expiry.seconds // 60) % 60
                    
                    # Format relative time description
                    expired_time = []
                    if days_ago > 0:
                        expired_time.append(f"{days_ago} {'day' if days_ago == 1 else 'days'}")
                    if hours_ago > 0 or days_ago > 0:
                        expired_time.append(f"{hours_ago} {'hour' if hours_ago == 1 else 'hours'}")
                    if minutes_ago > 0 or hours_ago > 0 or days_ago > 0:
                        expired_time.append(f"{minutes_ago} {'minute' if minutes_ago == 1 else 'minutes'}")
                    
                    expired_time_str = ", ".join(expired_time) + " ago"
                    
                    error_embed = build_embed(
                        title="❌ Key Expired",
                        description=f"This premium key has expired and is no longer valid.",
                        color=discord.Color.red(),
                        fields=[
                            {
                                'name': '⏰ Expired',
                                'value': f"{expired_time_str} ({format_timestamp(expiry_date)})",
                                'inline': False
                            },
                            {
                                'name': '🔑 Key',
                                'value': f"`{key[:8]}...{key[-8:]}`",
                                'inline': False
                            },
                            {
                                'name': '🔄 What can you do?',
                                'value': "Ask an administrator to generate a new premium key for you using the `/generate` command.",
                                'inline': False
                            }
                        ],
                        footer={
                            'text': 'Premium keys cannot be used after they expire'
                        }
                    )
                    await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                    
                    # Log expired key attempt
                    try:
                        log_channel = self.cog.bot.get_channel(self.cog.bot.log_channel_id)
                        if log_channel:
                            creator_id = key_data.get('user_id_created')
                            creator = f"<@{creator_id}>" if creator_id else "Unknown"
                            
                            log_embed = build_embed(
                                title="⚠️ Expired Key Redemption Attempt",
                                description=f"A user attempted to redeem an expired key",
                                color=discord.Color.orange(),
                                fields=[
                                    {
                                        'name': '👤 User',
                                        'value': f"{modal_interaction.user.mention} (`{modal_interaction.user.name}` ID: `{modal_interaction.user.id}`)",
                                        'inline': False
                                    },
                                    {
                                        'name': '🔑 Key',
                                        'value': f"`{key}`",
                                        'inline': True
                                    },
                                    {
                                        'name': '👑 Created By',
                                        'value': creator,
                                        'inline': True
                                    },
                                    {
                                        'name': '📅 Expired On',
                                        'value': f"`{format_timestamp(expiry_date)}`",
                                        'inline': False
                                    }
                                ],
                                timestamp=datetime.now()
                            )
                            await log_channel.send(embed=log_embed)
                    except Exception as e:
                        logger.error(f"Error sending expired key log: {e}")
                    
                    return
                
                # Get premium role
                guild = modal_interaction.guild
                premium_role = guild.get_role(self.cog.premium_role_id)
                if not premium_role:
                    error_embed = build_embed(
                        title="❌ Role Not Found",
                        description="The premium role could not be found. Please contact an administrator.",
                        color=discord.Color.red()
                    )
                    await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                    return
                
                # Update key with user who redeemed it
                self.cog.keys_db.update_key_redeemed(key, modal_interaction.user.id)
                
                # Sync to database
                try:
                    from utils.sync_keys import sync_db_to_json
                    sync_db_to_json()
                except Exception as e:
                    logger.error(f"Error syncing to database: {e}")
                
                # Add premium role to user
                try:
                    await modal_interaction.user.add_roles(premium_role)
                    
                    # Calculate exact expiration time and relative time
                    now = datetime.now()
                    expiry_date = key_data.get('expiry_date')
                    time_until_expiry = expiry_date - now
                    days = time_until_expiry.days
                    hours = time_until_expiry.seconds // 3600
                    minutes = (time_until_expiry.seconds // 60) % 60
                    
                    # Format relative time description
                    relative_time = []
                    if days > 0:
                        relative_time.append(f"{days} {'day' if days == 1 else 'days'}")
                    if hours > 0 or days > 0:
                        relative_time.append(f"{hours} {'hour' if hours == 1 else 'hours'}")
                    if minutes > 0 or hours > 0 or days > 0:
                        relative_time.append(f"{minutes} {'minute' if minutes == 1 else 'minutes'}")
                    
                    relative_time_str = ", ".join(relative_time)
                    
                    # Create a visual success embed
                    success_embed = build_embed(
                        title="✅ Premium Activated Successfully!",
                        description=f"Thank you for activating premium! You now have access to all premium features.",
                        color=discord.Color.green(),
                        thumbnail=modal_interaction.user.display_avatar.url,
                        fields=[
                            {
                                'name': '⭐ Premium Status',
                                'value': f"**ACTIVE**",
                                'inline': False
                            },
                            {
                                'name': '⏱️ Duration',
                                'value': f"`{key_data.get('duration_str')}`",
                                'inline': True
                            },
                            {
                                'name': '⌛ Remaining Time',
                                'value': f"{relative_time_str}",
                                'inline': True
                            },
                            {
                                'name': '📅 Valid Until',
                                'value': f"`{format_timestamp(expiry_date)}`",
                                'inline': False
                            },
                            {
                                'name': '🔑 Key',
                                'value': f"`{key[:8]}...{key[-8:]}`",
                                'inline': False
                            }
                        ],
                        footer={
                            'text': f'Redeemed by {modal_interaction.user.display_name}',
                            'icon_url': modal_interaction.user.display_avatar.url
                        },
                        timestamp=datetime.now()
                    )
                    
                    # Send success message
                    await modal_interaction.followup.send(embed=success_embed, ephemeral=True)
                    
                    # Log the successful redemption
                    logger.info(f"User {modal_interaction.user.name} (ID: {modal_interaction.user.id}) redeemed premium key {key}")
                    
                    # Log key redemption to channel
                    creator_id = key_data.get('user_id_created')
                    creator = f"<@{creator_id}>" if creator_id else "Unknown"
                    
                    # Prepare log message for the log channel
                    log_embed = build_embed(
                        title="✅ Premium Key Redeemed",
                        description=f"A premium key has been successfully activated.",
                        color=discord.Color.green(),
                        fields=[
                            {
                                'name': '👤 Redeemed By',
                                'value': f"{modal_interaction.user.mention} (`{modal_interaction.user.name}` ID: `{modal_interaction.user.id}`)",
                                'inline': False
                            },
                            {
                                'name': '👑 Generated By',
                                'value': creator,
                                'inline': True
                            },
                            {
                                'name': '⏱️ Duration',
                                'value': f"`{key_data.get('duration_str')}`",
                                'inline': True
                            },
                            {
                                'name': '📅 Expires',
                                'value': f"`{format_timestamp(key_data.get('expiry_date'))}`",
                                'inline': True
                            },
                            {
                                'name': '🔑 Key',
                                'value': f"`{key[:8]}...{key[-8:]}`",
                                'inline': False
                            }
                        ],
                        footer={
                            'text': f'Server: {modal_interaction.guild.name}',
                            'icon_url': modal_interaction.guild.icon.url if modal_interaction.guild.icon else None
                        },
                        timestamp=datetime.now()
                    )
                    
                    # Get log channel directly instead of using the method
                    try:
                        log_channel_id = self.cog.bot.log_channel_id
                        log_channel = self.cog.bot.get_channel(log_channel_id)
                        if log_channel:
                            await log_channel.send(embed=log_embed)
                        else:
                            logger.warning(f"Log channel with ID {log_channel_id} not found")
                    except Exception as e:
                        logger.error(f"Error sending log to channel: {e}")
                    
                except discord.Forbidden:
                    error_embed = build_embed(
                        title="❌ Permission Error",
                        description="I don't have permission to assign roles. Please contact an administrator.",
                        color=discord.Color.red()
                    )
                    await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                except Exception as e:
                    logger.error(f"Error assigning premium role: {e}")
                    error_embed = build_embed(
                        title="❌ Error Occurred",
                        description=f"An error occurred while assigning the premium role:\n```{str(e)}```\nPlease contact an administrator.",
                        color=discord.Color.red()
                    )
                    await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
        
        # Create and send the modal with the cog reference
        modal = KeyRedeemModal(self)
        await interaction.response.send_modal(modal)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Start background task for checking expired premium keys."""
        self.bot.loop.create_task(self.check_expired_keys())
    
    async def check_expired_keys(self):
        """Background task to check and remove expired premium roles and synchronize database."""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                # Sync any new keys to database
                try:
                    from utils.sync_keys import sync_db_to_json
                    sync_db_to_json()
                    logger.info("Database synchronized during scheduled check")
                except Exception as e:
                    logger.error(f"Error syncing keys to database: {e}")
            
                # Get all expired keys
                expired_keys = self.keys_db.get_expired_keys()
                
                for key_data in expired_keys:
                    user_id = key_data.get('user_id_redeemed')
                    if not user_id:
                        continue
                    
                    # For each guild the bot is in
                    for guild in self.bot.guilds:
                        member = guild.get_member(user_id)
                        if not member:
                            continue
                        
                        premium_role = guild.get_role(self.premium_role_id)
                        if not premium_role:
                            continue
                        
                        if premium_role in member.roles:
                            try:
                                await member.remove_roles(premium_role)
                                logger.info(f"Removed premium role from {member.name} (ID: {member.id}) due to key expiration")
                                
                                # Log key expiration to channel
                                key = key_data.get('key', 'Unknown')
                                creator_id = key_data.get('user_id_created')
                                creator = f"<@{creator_id}>" if creator_id else "Unknown"
                                
                                expiry_log_embed = build_embed(
                                    title="⏰ Premium Membership Expired",
                                    description=f"A premium membership has expired and the role has been removed.",
                                    color=discord.Color.orange(),
                                    fields=[
                                        {
                                            'name': '👤 User',
                                            'value': f"{member.mention} (`{member.name}` ID: `{member.id}`)",
                                            'inline': False
                                        },
                                        {
                                            'name': '👑 Generated By',
                                            'value': creator,
                                            'inline': True
                                        },
                                        {
                                            'name': '⏱️ Duration',
                                            'value': f"`{key_data.get('duration_str')}`",
                                            'inline': True
                                        },
                                        {
                                            'name': '📅 Expired On',
                                            'value': f"`{format_timestamp(key_data.get('expiry_date'))}`",
                                            'inline': True
                                        },
                                        {
                                            'name': '🔑 Key',
                                            'value': f"`{key[:8]}...{key[-8:]}`" if len(key) > 16 else f"`{key}`",
                                            'inline': False
                                        }
                                    ],
                                    footer={
                                        'text': f'Server: {guild.name}',
                                        'icon_url': guild.icon.url if guild.icon else None
                                    },
                                    timestamp=datetime.now()
                                )
                                # Get log channel directly
                                try:
                                    log_channel_id = self.bot.log_channel_id
                                    log_channel = self.bot.get_channel(log_channel_id)
                                    if log_channel:
                                        await log_channel.send(embed=expiry_log_embed)
                                    else:
                                        logger.warning(f"Log channel with ID {log_channel_id} not found")
                                except Exception as e:
                                    logger.error(f"Error sending expiry log to channel: {e}")
                                
                                # Notify user about premium expiration
                                try:
                                    expire_embed = build_embed(
                                        title="⏰ Premium Membership Expired",
                                        description="Your premium role has expired. Thank you for being a premium member!",
                                        color=discord.Color.orange(),
                                        fields=[
                                            {
                                                'name': '🔄 Want to Renew?',
                                                'value': "Ask an administrator to generate a new premium key for you using the `/generate` command.",
                                                'inline': False
                                            }
                                        ],
                                        footer={
                                            'text': f'{guild.name} • Premium Membership',
                                            'icon_url': guild.icon.url if guild.icon else None
                                        },
                                        timestamp=datetime.now()
                                    )
                                    await member.send(embed=expire_embed)
                                    logger.info(f"Sent expiration notification to {member.name} (ID: {member.id})")
                                except discord.Forbidden:
                                    # Can't send DM to user
                                    logger.warning(f"Could not send expiration DM to {member.name} (ID: {member.id})")
                                    pass
                            except Exception as e:
                                logger.error(f"Error removing premium role: {e}")
                
                # Clean up expired keys
                self.keys_db.cleanup_expired_keys()
                
            except Exception as e:
                logger.error(f"Error in check_expired_keys task: {e}")
            
            # Sync again after cleanup to ensure web interface stays updated
            try:
                from utils.sync_keys import sync_db_to_json
                sync_db_to_json()
            except Exception as e:
                logger.error(f"Error syncing keys to database after cleanup: {e}")
            
            # Run check every 10 minutes instead of hourly to ensure timely synchronization
            await asyncio.sleep(600)

async def setup(bot):
    await bot.add_cog(KeyManagement(bot))
