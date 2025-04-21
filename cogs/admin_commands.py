import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime, timedelta

from utils.embed_builder import build_embed
from utils.time_utils import parse_duration, format_timestamp
from data.keys_database import KeysDatabase

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    """Cog for admin-only commands for managing premium keys."""
    
    def __init__(self, bot):
        self.bot = bot
        self.keys_db = KeysDatabase()
        self.admin_role_id = 1358003588336582757  # Admin role ID from request
        self.premium_role_id = 1302915891444580372  # Premium role ID from request
    
    def _check_admin_permissions(self, interaction: discord.Interaction) -> bool:
        """Check if a user has admin permissions."""
        if not interaction.guild:
            return False
        
        # Check if user has the admin role
        admin_role = interaction.guild.get_role(self.admin_role_id)
        if admin_role and admin_role in interaction.user.roles:
            return True
        
        # Check if user is a server administrator
        return interaction.user.guild_permissions.administrator
    
    @app_commands.command(name="listkeys", description="[Admin] List all active premium keys")
    @app_commands.default_permissions(administrator=True)
    async def list_keys(self, interaction: discord.Interaction):
        """Command to list all active premium keys (admin only)."""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user has admin permissions
        if not self._check_admin_permissions(interaction):
            error_embed = build_embed(
                title="❌ Access Denied",
                description="You don't have permission to use this admin command.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        
        # Get all active keys
        active_keys = self.keys_db.get_active_keys()
        
        if not active_keys:
            empty_embed = build_embed(
                title="🔍 Premium Keys",
                description="There are no active premium keys in the database.",
                color=discord.Color.blue(),
                fields=[
                    {
                        'name': '💡 How to Generate Keys',
                        'value': "Use the `/generate <duration>` command to create new premium keys.",
                        'inline': False
                    }
                ],
                footer={
                    'text': f'Requested by {interaction.user.display_name}',
                    'icon_url': interaction.user.display_avatar.url
                },
                timestamp=datetime.now()
            )
            await interaction.followup.send(embed=empty_embed, ephemeral=True)
            return
        
        # Create a paginated view for keys
        class KeyPaginationView(discord.ui.View):
            def __init__(self, cog, keys, timeout=180):
                super().__init__(timeout=timeout)
                self.cog = cog
                self.keys = keys
                self.current_page = 0
                self.keys_per_page = 5
                self.total_pages = (len(keys) + self.keys_per_page - 1) // self.keys_per_page
            
            def get_current_page_embed(self):
                start_idx = self.current_page * self.keys_per_page
                end_idx = min(start_idx + self.keys_per_page, len(self.keys))
                
                page_keys = self.keys[start_idx:end_idx]
                
                embed = build_embed(
                    title="🔑 Active Premium Keys",
                    description=f"Showing keys {start_idx+1}-{end_idx} of {len(self.keys)} total active keys",
                    color=discord.Color.gold(),
                    footer={
                        'text': f'Page {self.current_page+1}/{self.total_pages} • Use the buttons below to navigate'
                    },
                    timestamp=datetime.now()
                )
                
                for key_data in page_keys:
                    key = key_data.get('key')
                    creator_id = key_data.get('user_id_created')
                    redeemer_id = key_data.get('user_id_redeemed')
                    duration_str = key_data.get('duration_str')
                    expiry_date = key_data.get('expiry_date')
                    
                    creator = f"<@{creator_id}>" if creator_id else "Unknown"
                    
                    if redeemer_id:
                        status_emoji = "✅"
                        redeemer = f"<@{redeemer_id}>"
                    else:
                        status_emoji = "⏳"
                        redeemer = "Not redeemed yet"
                    
                    # Determine if key is close to expiration
                    now = datetime.now()
                    time_left = expiry_date - now
                    expires_soon = time_left.days < 3 and time_left.days >= 0
                    expired = time_left.days < 0
                    
                    if expired:
                        expiry_text = f"**EXPIRED:** {format_timestamp(expiry_date)}"
                        expiry_emoji = "⚠️"
                    elif expires_soon:
                        expiry_text = f"**EXPIRING SOON:** {format_timestamp(expiry_date)}"
                        expiry_emoji = "⚠️"
                    else:
                        expiry_text = format_timestamp(expiry_date)
                        expiry_emoji = "📅"
                    
                    embed.add_field(
                        name=f"{status_emoji} Key: `{key}`",
                        value=f"👤 **Created by:** {creator}\n"
                              f"👑 **Status:** {redeemer}\n"
                              f"⏱️ **Duration:** `{duration_str}`\n"
                              f"{expiry_emoji} **Expires:** {expiry_text}\n"
                              f"ℹ️ Use `/keyinfo {key}` for detailed management",
                        inline=False
                    )
                return embed
            
            @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
            async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page > 0:
                    self.current_page -= 1
                    await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)
                else:
                    await interaction.response.defer()
            
            @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_page < self.total_pages - 1:
                    self.current_page += 1
                    await interaction.response.edit_message(embed=self.get_current_page_embed(), view=self)
                else:
                    await interaction.response.defer()
        
        # Create the paginated view
        view = KeyPaginationView(self, active_keys)
        await interaction.followup.send(embed=view.get_current_page_embed(), view=view, ephemeral=True)
    
    @app_commands.command(name="keyinfo", description="[Admin] View and manage a specific premium key")
    @app_commands.describe(key="Premium key to manage")
    @app_commands.default_permissions(administrator=True)
    async def key_info(self, interaction: discord.Interaction, key: str):
        """Command to view and manage a specific premium key (admin only)."""
        await interaction.response.defer(ephemeral=True)
        
        # Check if user has admin permissions
        if not self._check_admin_permissions(interaction):
            error_embed = build_embed(
                title="❌ Access Denied",
                description="You don't have permission to use this admin command.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return
        
        # Get key data
        key = key.strip()  # Remove any whitespace
        key_data = self.keys_db.get_key(key)
        
        # Проверим, был ли ключ ранее в базе данных, но истек и был удален
        all_keys = self.keys_db.keys
        expired_keys = self.keys_db.get_expired_keys()
        expired_key_ids = [k.get('key') for k in expired_keys]
        
        if not key_data:
            if key in expired_key_ids:
                error_embed = build_embed(
                    title="⌛ Key Expired",
                    description=f"The key `{key}` has expired and is no longer active.",
                    color=discord.Color.orange(),
                    fields=[
                        {
                            'name': '❓ What happened?',
                            'value': "This key has expired and has been removed from active keys. It can no longer be used.",
                            'inline': False
                        }
                    ],
                    footer={
                        'text': 'You can generate a new key if needed'
                    }
                )
            else:
                error_embed = build_embed(
                    title="❌ Key Not Found",
                    description=f"The key `{key}` does not exist in the database.",
                    color=discord.Color.red(),
                    footer={
                        'text': 'Make sure you entered the key correctly'
                    }
                )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            
            # Log to channel
            try:
                log_channel = self.bot.get_channel(self.bot.log_channel_id)
                if log_channel:
                    log_embed = build_embed(
                        title="❓ Key Lookup Failed",
                        description=f"Admin attempted to view a key that doesn't exist",
                        color=discord.Color.yellow(),
                        fields=[
                            {
                                'name': '👤 Admin',
                                'value': f"{interaction.user.mention} (`{interaction.user.name}` ID: `{interaction.user.id}`)",
                                'inline': False
                            },
                            {
                                'name': '🔑 Key Fragment',
                                'value': f"`{key[:8]}...{key[-8:] if len(key) > 16 else key}`",
                                'inline': False
                            }
                        ],
                        timestamp=datetime.now()
                    )
                    await log_channel.send(embed=log_embed)
            except Exception as e:
                logger.error(f"Error sending key not found log: {e}")
            
            return
        
        creator_id = key_data.get('user_id_created')
        redeemer_id = key_data.get('user_id_redeemed')
        duration_str = key_data.get('duration_str')
        expiry_date = key_data.get('expiry_date')
        created_at = key_data.get('created_at', datetime.now())
        
        creator = f"<@{creator_id}>" if creator_id else "Unknown"
        
        # Determine key status
        now = datetime.now()
        time_left = expiry_date - now
        is_expired = time_left.days < 0
        
        if redeemer_id:
            status = f"✅ Redeemed by <@{redeemer_id}>"
            status_color = discord.Color.green()
        else:
            status = "⏳ Not yet redeemed"
            status_color = discord.Color.gold()
        
        # Create embed for key info with improved visuals
        embed = build_embed(
            title=f"🔑 Premium Key Details",
            description=f"**Key:** `{key}`\n\n{status}",
            color=status_color,
            fields=[
                {
                    'name': '👤 Created By',
                    'value': creator,
                    'inline': True
                },
                {
                    'name': '🕒 Created At',
                    'value': created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else "Unknown",
                    'inline': True
                },
                {
                    'name': '⏱️ Duration',
                    'value': f"`{duration_str}`",
                    'inline': True
                },
                {
                    'name': '📅 Expires' if not is_expired else '⚠️ Expired',
                    'value': f"`{format_timestamp(expiry_date)}`",
                    'inline': True
                },
                {
                    'name': '🛠️ Management Options',
                    'value': "Use the buttons below to manage this premium key",
                    'inline': False
                }
            ],
            footer={
                'text': f'Requested by {interaction.user.display_name}',
                'icon_url': interaction.user.display_avatar.url
            },
            timestamp=datetime.now()
        )
        
        # Create view with buttons for managing the key
        class KeyManagementView(discord.ui.View):
            def __init__(self, cog, key_data, timeout=180):
                super().__init__(timeout=timeout)
                self.cog = cog
                self.key_data = key_data
                
                # If key is not redeemed, disable delete button
                if not key_data.get('user_id_redeemed'):
                    self.delete_button.disabled = True
            
            @discord.ui.button(label="Modify Duration", style=discord.ButtonStyle.primary)
            async def modify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Create modal for entering new duration
                class DurationModal(discord.ui.Modal, title="Modify Key Duration"):
                    duration_input = discord.ui.TextInput(
                        label="New Duration",
                        placeholder="e.g. 7d, 1w, 1m",
                        required=True
                    )
                    
                    async def on_submit(self, modal_interaction: discord.Interaction):
                        await modal_interaction.response.defer(ephemeral=True)
                        
                        try:
                            duration_seconds = parse_duration(self.duration_input.value)
                            if duration_seconds <= 0:
                                await modal_interaction.followup.send("Duration must be positive.", ephemeral=True)
                                return
                            
                            key = self.view.key_data.get('key')
                            new_expiry_date = datetime.now() + timedelta(seconds=duration_seconds)
                            
                            # Update key duration
                            self.view.cog.keys_db.update_key_duration(key, duration_seconds, new_expiry_date)
                            
                            # Save keys to file
                            self.view.cog.keys_db.save_keys()
                            
                            # Отправляем лог об изменении ключа в канал логов
                            try:
                                log_channel = self.view.cog.bot.get_channel(self.view.cog.bot.log_channel_id)
                                if log_channel:
                                    log_embed = build_embed(
                                        title="🔄 Key Duration Modified",
                                        description=f"An admin has modified a premium key's duration.",
                                        color=discord.Color.yellow(),
                                        fields=[
                                            {
                                                'name': '👤 Modified By',
                                                'value': f"{modal_interaction.user.mention} (`{modal_interaction.user.name}` ID: `{modal_interaction.user.id}`)",
                                                'inline': False
                                            },
                                            {
                                                'name': '🔑 Key',
                                                'value': f"`{key}`",
                                                'inline': False
                                            },
                                            {
                                                'name': '⏱️ New Duration',
                                                'value': f"`{format_duration(duration_seconds)}`",
                                                'inline': True
                                            },
                                            {
                                                'name': '📅 New Expiry Date',
                                                'value': f"`{format_timestamp(new_expiry_date)}`",
                                                'inline': True
                                            }
                                        ],
                                        footer={
                                            'text': f'Server: {modal_interaction.guild.name}',
                                            'icon_url': modal_interaction.guild.icon.url if modal_interaction.guild.icon else None
                                        },
                                        timestamp=datetime.now()
                                    )
                                    await log_channel.send(embed=log_embed)
                            except Exception as e:
                                logger.error(f"Error sending key modification log: {e}")
                            
                            # Update user's premium role expiry if the key is redeemed
                            redeemer_id = self.view.key_data.get('user_id_redeemed')
                            creator_id = self.view.key_data.get('user_id_created')
                            created_at = self.view.key_data.get('created_at', datetime.now())
                            
                            # Create a visually appealing success embed
                            success_embed = build_embed(
                                title="✅ Duration Modified Successfully",
                                description=f"The premium key duration has been updated.",
                                color=discord.Color.green(),
                                fields=[
                                    {
                                        'name': '🔑 Key',
                                        'value': f"`{key[:8]}...{key[-8:]}`",
                                        'inline': False
                                    },
                                    {
                                        'name': '⏱️ New Duration',
                                        'value': f"`{format_duration(duration_seconds)}`",
                                        'inline': True
                                    },
                                    {
                                        'name': '📅 New Expiry Date',
                                        'value': f"`{format_timestamp(new_expiry_date)}`",
                                        'inline': True
                                    },
                                    {
                                        'name': '👤 Created By',
                                        'value': f"<@{creator_id}>" if creator_id else "Unknown",
                                        'inline': True
                                    },
                                    {
                                        'name': '👑 Status',
                                        'value': f"Redeemed by <@{redeemer_id}>" if redeemer_id else "Not yet redeemed",
                                        'inline': True
                                    }
                                ],
                                footer={
                                    'text': f'Modified by {modal_interaction.user.display_name}',
                                    'icon_url': modal_interaction.user.display_avatar.url
                                },
                                timestamp=datetime.now()
                            )
                            
                            # For redeemed keys, also add notice about user's role
                            if redeemer_id:
                                success_embed.add_field(
                                    name="🔄 User Role Updated",
                                    value="The premium role expiration has been updated for the user who redeemed this key.",
                                    inline=False
                                )
                                
                            await modal_interaction.followup.send(embed=success_embed, ephemeral=True)
                            logger.info(f"Admin {modal_interaction.user.name} (ID: {modal_interaction.user.id}) modified key {key} duration to {format_duration(duration_seconds)}")
                        except ValueError as e:
                            await modal_interaction.followup.send(f"Invalid duration format: {str(e)}", ephemeral=True)
                
                # Show the duration input modal
                modal = DurationModal()
                modal.view = self
                await interaction.response.send_modal(modal)
            
            @discord.ui.button(label="Delete Key", style=discord.ButtonStyle.danger)
            async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Create confirmation view
                class ConfirmationView(discord.ui.View):
                    def __init__(self, parent_view, timeout=60):
                        super().__init__(timeout=timeout)
                        self.parent_view = parent_view
                    
                    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
                    async def confirm_button(self, confirm_interaction: discord.Interaction, button: discord.ui.Button):
                        key = self.parent_view.key_data.get('key')
                        redeemer_id = self.parent_view.key_data.get('user_id_redeemed')
                        
                        # Delete key from database
                        self.parent_view.cog.keys_db.delete_key(key)
                        
                        # Save keys to file
                        self.parent_view.cog.keys_db.save_keys()
                        
                        # Отправляем лог об удалении ключа в канал логов
                        try:
                            log_channel = self.parent_view.cog.bot.get_channel(self.parent_view.cog.bot.log_channel_id)
                            if log_channel:
                                log_embed = build_embed(
                                    title="❌ Key Deleted",
                                    description=f"An admin has deleted a premium key.",
                                    color=discord.Color.red(),
                                    fields=[
                                        {
                                            'name': '👤 Deleted By',
                                            'value': f"{confirm_interaction.user.mention} (`{confirm_interaction.user.name}` ID: `{confirm_interaction.user.id}`)",
                                            'inline': False
                                        },
                                        {
                                            'name': '🔑 Key',
                                            'value': f"`{key}`",
                                            'inline': False
                                        }
                                    ],
                                    footer={
                                        'text': f'Server: {confirm_interaction.guild.name}',
                                        'icon_url': confirm_interaction.guild.icon.url if confirm_interaction.guild.icon else None
                                    },
                                    timestamp=datetime.now()
                                )
                                
                                # Добавляем информацию о пользователе, если ключ был использован
                                if redeemer_id:
                                    log_embed.add_field(
                                        name='👤 Redeemed By',
                                        value=f"<@{redeemer_id}> (ID: `{redeemer_id}`)",
                                        inline=True
                                    )
                                
                                await log_channel.send(embed=log_embed)
                        except Exception as e:
                            logger.error(f"Error sending key deletion log: {e}")
                        
                        # Инициализируем переменную на случай, если ключ не был погашен
                        has_other_active_keys = False
                        
                        # If key was redeemed, проверяем наличие других активных ключей перед удалением роли
                        if redeemer_id:
                            # Проверяем, есть ли у пользователя другие активные ключи
                            has_other_active_keys = self.parent_view.cog.keys_db.has_active_keys(redeemer_id)
                            
                            # Если нет других активных ключей, удаляем роль
                            if not has_other_active_keys:
                                for guild in self.parent_view.cog.bot.guilds:
                                    member = guild.get_member(redeemer_id)
                                    if not member:
                                        continue
                                    
                                    premium_role = guild.get_role(self.parent_view.cog.premium_role_id)
                                    if not premium_role or premium_role not in member.roles:
                                        continue
                                    
                                    try:
                                        # Удаляем роль
                                        await member.remove_roles(premium_role)
                                        
                                        # Send notification to user
                                        try:
                                            notify_embed = build_embed(
                                                title="⛔ Premium Role Removed",
                                                description="Your premium role has been removed by an administrator.",
                                                color=discord.Color.red(),
                                                fields=[
                                                    {
                                                        'name': '🔄 Want Premium Again?',
                                                        'value': "Contact a server administrator to get a new premium key."
                                                    }
                                                ],
                                                footer={
                                                    'text': 'Thank you for being a premium member!'
                                                },
                                                timestamp=datetime.now()
                                            )
                                            await member.send(embed=notify_embed)
                                            logger.info(f"Sent premium removal notification to {member.name} (ID: {member.id})")
                                        except discord.Forbidden:
                                            # Can't send DM to user
                                            logger.warning(f"Could not send premium removal DM to {member.name} (ID: {member.id})")
                                    except Exception as e:
                                        logger.error(f"Error removing premium role: {e}")
                        
                        # Create success message
                        success_embed = build_embed(
                            title="✅ Key Deleted Successfully",
                            description=f"The premium key has been deleted from the database.",
                            color=discord.Color.green(),
                            fields=[
                                {
                                    'name': '🔑 Key',
                                    'value': f"`{key[:8]}...{key[-8:]}`",
                                    'inline': False
                                }
                            ],
                            footer={
                                'text': f'Deleted by {confirm_interaction.user.display_name}',
                                'icon_url': confirm_interaction.user.display_avatar.url
                            },
                            timestamp=datetime.now()
                        )
                        
                        # Add info about role removal if applicable
                        if redeemer_id:
                            if not has_other_active_keys:
                                success_embed.add_field(
                                    name="👑 Role Removed",
                                    value=f"Premium role has been removed from <@{redeemer_id}> as they have no other active keys.",
                                    inline=False
                                )
                            else:
                                success_embed.add_field(
                                    name="👑 Role Preserved",
                                    value=f"Premium role for <@{redeemer_id}> was preserved as they have other active keys.",
                                    inline=False
                                )
                            
                        logger.info(f"Admin {confirm_interaction.user.name} (ID: {confirm_interaction.user.id}) deleted key {key}")
                        
                        await confirm_interaction.response.edit_message(
                            content=None,
                            embed=success_embed,
                            view=None
                        )
                    
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.gray)
                    async def cancel_button(self, cancel_interaction: discord.Interaction, button: discord.ui.Button):
                        await cancel_interaction.response.edit_message(
                            content="Key deletion cancelled.",
                            embed=self.parent_view.key_data.get('embed'),
                            view=self.parent_view
                        )
                
                # Store current embed for restoring if cancelled
                self.key_data['embed'] = interaction.message.embeds[0]
                
                # Show confirmation view
                confirm_view = ConfirmationView(self)
                await interaction.response.edit_message(
                    content="Are you sure you want to delete this key? If the key is redeemed, the premium role will be removed from the user.",
                    embed=None,
                    view=confirm_view
                )
        
        # Create and send view
        view = KeyManagementView(self, key_data)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))

def format_duration(seconds):
    """Format seconds into a readable duration string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"
