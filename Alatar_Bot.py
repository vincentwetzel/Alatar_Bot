"""
Alatar Bot - A modern Discord bot for server management.

Features:
- User activity monitoring and logging
- Automated voice channel organization
- Welcome system and role management
- Admin notification system
- Fun commands (insults, invites)
"""

import asyncio
import json
import logging
import os
import sys
from bisect import bisect
from collections import defaultdict, deque
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from discord.ext import commands
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_FILE: str = "discord.log"
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB per log file
LOG_BACKUP_COUNT: int = 5  # Keep 5 rotated log files

SETTINGS_FILE: str = "settings.json"

CHANNEL_NAME_WELCOME: str = "welcome"
CHANNEL_NAME_ADMIN: str = "admin"
CHANNEL_NAME_VOICE_CATEGORY: str = "Voice Channels"
CHANNEL_NAME_GENERAL_VOICE: str = "General"
CHANNEL_NAME_PUBG_VOICE: str = "PUBG Rage-Fest"
CHANNEL_NAME_LOL_VOICE: str = "Teemo's Treehouse"

PLEB_ROLE_NAME: str = "Plebs"

MEMBER_ROLE_EVERYONE: str = "@everyone"

GAME_VOICE_CHANNEL_MAPPING: dict[str, str] = {
    "PLAYERUNKNOWN'S BATTLEGROUNDS": CHANNEL_NAME_PUBG_VOICE,
    "PUBG": CHANNEL_NAME_PUBG_VOICE,
    "League of Legends": CHANNEL_NAME_LOL_VOICE,
}

PLAYMATE_CLEANUP_DELAY: float = 15.0
VOICE_CHANNEL_BITRATE: int = 64000
VOICE_CHANNEL_USER_LIMIT: int = 10
VOICE_INVITE_MAX_AGE: int = 3600

LOG_SEPARATOR_COUNT: int = 75


# ---------------------------------------------------------------------------
# Logger configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
_log_handler = RotatingFileHandler(
    filename=LOG_FILE,
    encoding="utf-8",
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
)
_log_handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(_log_handler)


# ---------------------------------------------------------------------------
# Bot state container
# ---------------------------------------------------------------------------

class BotState:
    """Encapsulates all mutable runtime state."""

    def __init__(self) -> None:
        self.admin_discord_id: int = 0
        self.notifications_enabled: bool = True
        self.pending_notification_queue: deque[str] = deque()
        self.ignored_member_names: list[str] = []
        self.members_seeking_playmates: defaultdict[str, list[discord.Member]] = defaultdict(list)
        self.settings: dict[str, str | int | list[str]] = {}


bot_state = BotState()


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

_DEFAULT_SETTINGS: dict[str, str | int | list[str]] = {
    "discord_token": "",
    "admin_discord_id": "",
    "log_max_bytes": LOG_MAX_BYTES,
    "log_backup_count": LOG_BACKUP_COUNT,
    "ignored_members": [],
}


def load_settings(config_path: str = SETTINGS_FILE) -> dict[str, str | int | list[str]]:
    """Load settings from a JSON file, creating defaults if missing."""
    if not os.path.exists(config_path):
        logger.info("Settings file '%s' not found. Creating defaults.", config_path)
        save_settings(_DEFAULT_SETTINGS.copy(), config_path)
        return _DEFAULT_SETTINGS.copy()

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            loaded_settings: dict[str, str | int | list[str]] = json.load(config_file)
        for config_key, default_value in _DEFAULT_SETTINGS.items():
            loaded_settings.setdefault(config_key, default_value)
        return loaded_settings
    except (json.JSONDecodeError, OSError) as parse_error:
        logger.warning("Error reading '%s': %s. Using defaults.", config_path, parse_error)
        save_settings(_DEFAULT_SETTINGS.copy(), config_path)
        return _DEFAULT_SETTINGS.copy()


def save_settings(settings_to_save: dict[str, str | int | list[str]], config_path: str = SETTINGS_FILE) -> None:
    """Persist settings to a JSON file."""
    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(settings_to_save, config_file, indent=4)


def initialize_bot_token(current_settings: dict[str, str | int | list[str]]) -> str:
    """Return the bot token from settings, env var, or prompt the user."""
    stored_token = current_settings.get("discord_token", "")

    # Check environment variable first
    env_token = os.environ.get("DISCORD_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN")
    if env_token:
        logger.info("Using bot token from environment variable.")
        current_settings["discord_token"] = env_token
        save_settings(current_settings)
        return env_token

    if stored_token:
        return str(stored_token)

    # Only prompt if running interactively
    if sys.stdin.isatty():
        stored_token = input("Discord bot token not found in settings. Enter token: ")
        current_settings["discord_token"] = stored_token
        save_settings(current_settings)
        return stored_token

    raise ValueError(
        "Bot token is not configured. "
        "Set DISCORD_TOKEN environment variable, "
        "add discord_token to settings.json, "
        "or run the bot interactively to be prompted."
    )


def initialize_admin_discord_id(current_settings: dict[str, str | int | list[str]]) -> int:
    """Return the admin Discord ID from settings, env var, or prompt the user."""
    stored_admin_id = current_settings.get("admin_discord_id", "")

    # Check environment variable first
    env_admin_id = os.environ.get("ADMIN_DISCORD_ID")
    if env_admin_id:
        logger.info("Using admin ID from environment variable.")
        current_settings["admin_discord_id"] = env_admin_id
        save_settings(current_settings)
        return int(env_admin_id)

    if stored_admin_id and len(str(stored_admin_id)) == 18:
        try:
            return int(str(stored_admin_id))
        except ValueError:
            logger.error("Invalid admin ID format in settings.")
            raise ValueError("Invalid admin ID format in settings.") from None

    # Only prompt if running interactively
    if sys.stdin.isatty():
        admin_id_prompt: str = input("Enter the Discord ID of the admin the bot should report to: ")
        current_settings["admin_discord_id"] = admin_id_prompt
        save_settings(current_settings)
        return int(admin_id_prompt)

    raise ValueError(
        "Admin Discord ID is not configured. "
        "Set ADMIN_DISCORD_ID environment variable, "
        "add admin_discord_id to settings.json, "
        "or run the bot interactively to be prompted."
    )


# ---------------------------------------------------------------------------
# Bot initialization
# ---------------------------------------------------------------------------

BOT_DESCRIPTION: str = "Vincent's Bot for server management. Use /command syntax for slash commands."
BOT_INTENTS: discord.Intents = discord.Intents.default()
BOT_INTENTS.members = True
BOT_INTENTS.presences = True
BOT_INTENTS.message_content = True
BOT_INTENTS.guilds = True
BOT_INTENTS.voice_states = True

BOT_CLIENT: commands.Bot = commands.Bot(
    command_prefix="!",
    description=BOT_DESCRIPTION,
    intents=BOT_INTENTS,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _get_utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(UTC)


def format_log_timestamp(message_content: str) -> str:
    """Prepend a UTC timestamp to *message_content*."""
    current_timestamp = _get_utc_now()
    return f"{current_timestamp.strftime('%m-%d-%y')}\t{current_timestamp.strftime('%I:%M:%S%p')}\t{message_content}"


def pad_log_message(message_content: str, include_timestamp: bool = True, separator_count: int = LOG_SEPARATOR_COUNT) -> str:
    """Wrap *message_content* in a banner of dashes, optionally with a timestamp."""
    body = format_log_timestamp(message_content) if include_timestamp else message_content
    separator = "-" * separator_count
    return f"\n{separator}\n{body}\n{separator}\n"


async def send_admin_notification(
    notification_message: str,
    include_timestamp: bool = True,
    enable_tts: bool = False,
) -> None:
    """Send a DM to the bot owner, queueing if notifications are off."""
    formatted_message = format_log_timestamp(notification_message) if include_timestamp else notification_message
    if bot_state.notifications_enabled:
        bot_owner = await BOT_CLIENT.fetch_user(bot_state.admin_discord_id)
        await bot_owner.send(formatted_message, tts=enable_tts)
    else:
        bot_state.pending_notification_queue.append(formatted_message)


async def log_member_activity_to_file(member_display_name: str, activity_message: str) -> None:
    """Append *activity_message* to a per-member log file."""
    formatted_activity = format_log_timestamp(activity_message)
    os.makedirs("logs", exist_ok=True)
    log_file_path = os.path.join("logs", f"{member_display_name}.txt")
    with open(log_file_path, "a", encoding="utf-8") as activity_log:
        activity_log.write(formatted_activity + "\n")


async def get_or_create_text_channel(
    target_guild: discord.Guild,
    channel_display_name: str,
    creation_reason: str = "Requested by bot",
) -> discord.TextChannel:
    """Return an existing text channel or create one."""
    existing_channel = discord.utils.get(target_guild.text_channels, name=channel_display_name)
    if existing_channel:
        return existing_channel
    return await target_guild.create_text_channel(channel_display_name, reason=creation_reason)


async def assign_pleb_role(target_member: discord.Member) -> None:
    """Assign the 'Plebs' role to *target_member*, creating it if necessary."""
    pleb_role = discord.utils.get(target_member.guild.roles, name=PLEB_ROLE_NAME)
    if pleb_role is None:
        pleb_role = await target_member.guild.create_role(
            name=PLEB_ROLE_NAME,
            hoist=True,
            mentionable=True,
            reason="Default role for new members",
        )
        logger.info("Created '%s' role in %s", PLEB_ROLE_NAME, target_member.guild.name)
        await send_admin_notification(f"The {PLEB_ROLE_NAME} role did not exist and was created.")
    await target_member.add_roles(pleb_role, reason="Auto-assigned on join")


# ---------------------------------------------------------------------------
# Voice-channel playmate helpers
# ---------------------------------------------------------------------------

async def invite_members_to_voice_channel(
    matching_members: list[discord.Member],
    target_channel_name: str,
) -> None:
    """Invite/move *matching_members* to a voice channel, creating it if needed."""
    source_guild: discord.Guild = matching_members[0].guild
    target_voice_channel: discord.VoiceChannel | None = discord.utils.get(
        source_guild.voice_channels, name=target_channel_name
    )

    if target_voice_channel is None:
        voice_category: discord.CategoryChannel | None = discord.utils.get(
            source_guild.categories, name=CHANNEL_NAME_VOICE_CATEGORY
        )
        if voice_category is None:
            voice_category = await source_guild.create_category(
                CHANNEL_NAME_VOICE_CATEGORY,
                reason="Category for auto-managed voice channels",
            )
            await send_admin_notification(f"Created '{CHANNEL_NAME_VOICE_CATEGORY}' category.")
        else:
            await send_admin_notification(f"Using existing '{CHANNEL_NAME_VOICE_CATEGORY}' category.")

        target_voice_channel = await source_guild.create_voice_channel(
            target_channel_name,
            bitrate=VOICE_CHANNEL_BITRATE,
            user_limit=VOICE_CHANNEL_USER_LIMIT,
            category=voice_category,
            reason="Auto-created for members playing the same game",
        )

    voice_invite: discord.Invite = await target_voice_channel.create_invite(
        reason="Members playing the same game grouped by bot",
        max_age=VOICE_INVITE_MAX_AGE,
    )

    current_activity_name = matching_members[0].activities[0].name if matching_members[0].activities else "an activity"

    for target_member in matching_members:
        if target_member.voice and target_member.voice.channel == target_voice_channel:
            continue
        if target_member.voice is None:
            try:
                await target_member.send(
                    f"You're not the only person playing **{current_activity_name}**. "
                    f"Join here: https://discord.gg/{voice_invite.code}",
                    tts=True,
                )
            except discord.Forbidden:
                logger.warning("Cannot DM %s for voice invite.", target_member.display_name)
            log_action = f"{target_member.display_name} was INVITED to {target_voice_channel.name}"
        else:
            try:
                await target_member.move_to(target_voice_channel, reason="Grouping players")
                await target_member.send(
                    f"Hey {target_member.display_name}! Since you're playing **{current_activity_name}**, "
                    f"I moved you to {target_voice_channel.name} to join your friends.",
                    tts=True,
                )
            except (discord.Forbidden, discord.HTTPException) as voice_move_error:
                logger.warning("Failed to move %s: %s", target_member.display_name, voice_move_error)
                continue
            log_action = f"{target_member.display_name} was MOVED to {target_voice_channel.name}"

        await send_admin_notification(log_action)
        await log_member_activity_to_file(target_member.display_name, log_action)


def remove_member_from_playmate_seek(target_member: discord.Member, current_activity: discord.Activity) -> None:
    """Remove *target_member* from the playmate seek list (used by delayed task)."""
    activity_name = current_activity.name
    if activity_name is None:
        return
    playmate_list = bot_state.members_seeking_playmates.get(activity_name)
    if playmate_list and target_member in playmate_list:
        playmate_list.remove(target_member)
        if not playmate_list:
            bot_state.members_seeking_playmates.pop(activity_name, None)


# ---------------------------------------------------------------------------
# Event listeners
# ---------------------------------------------------------------------------

@BOT_CLIENT.event
async def on_ready() -> None:
    """Called when the bot is ready."""
    if BOT_CLIENT.user is None:
        return

    logger.info("Logged in as %s (ID: %s)", BOT_CLIENT.user, BOT_CLIENT.user.id)
    logger.info("Discord.py version: %s", discord.__version__)
    logger.info("-" * 30)

    await send_admin_notification("Alatar Bot is now online!", include_timestamp=False)

    # Load ignore list from settings
    ignored_members_config = bot_state.settings.get("ignored_members", [])
    bot_state.ignored_member_names = list(ignored_members_config) if isinstance(ignored_members_config, list) else []

    # Ensure everyone has the Pleb role
    for connected_guild in BOT_CLIENT.guilds:
        for guild_member in connected_guild.members:
            if len(guild_member.roles) == 1:
                await assign_pleb_role(guild_member)

    # Sync slash commands
    try:
        registered_commands: list[app_commands.AppCommand] = await BOT_CLIENT.tree.sync()
        logger.info("Synced %d application commands.", len(registered_commands))
    except Exception as sync_error:
        logger.error("Failed to sync commands: %s", sync_error)


@BOT_CLIENT.event
async def on_message(received_message: discord.Message) -> None:
    """Process incoming messages."""
    if received_message.author == BOT_CLIENT.user:
        return
    await BOT_CLIENT.process_commands(received_message)


@BOT_CLIENT.event
async def on_member_update(previous_state: discord.Member, current_state: discord.Member) -> None:
    """Handle member status, activity, nickname, role changes."""
    activity_log_message: str = ""

    # -- Status change --
    if previous_state.status != current_state.status:
        device_suffix: str = ""
        previous_client_status = getattr(previous_state, "client_status", {})
        current_client_status = getattr(current_state, "client_status", {})
        if previous_client_status != current_client_status:
            for device in ("mobile", "web", "desktop"):
                if previous_client_status.get(device) != current_client_status.get(device):
                    device_suffix = f" ({device.upper()})"
                    break

        activity_log_message = (
            f"{previous_state.display_name} is now: {current_state.status.name.upper()}{device_suffix}, "
            f"was {previous_state.status.name.upper()}{device_suffix}"
        )

    # -- Activity change --
    elif previous_state.activities != current_state.activities:
        new_activity: discord.Activity | None = None
        previous_activity: discord.Activity | None = None

        # Extract first activity if it's an Activity type (not Spotify/CustomActivity)
        if current_state.activities and isinstance(current_state.activities[0], discord.Activity):
            new_activity = current_state.activities[0]
        if previous_state.activities and isinstance(previous_state.activities[0], discord.Activity):
            previous_activity = previous_state.activities[0]

        if new_activity is None and previous_activity:
            activity_log_message = f"{previous_state.display_name} STOPPED playing: {previous_activity.name}"
        elif new_activity and new_activity.name:
            activity_log_message = f"{previous_state.display_name} STARTED playing: {new_activity.name}"
            activity_name = new_activity.name

            if current_state not in bot_state.members_seeking_playmates.get(activity_name, []):
                bot_state.members_seeking_playmates.setdefault(activity_name, []).append(current_state)

                members_with_matching_activity: list[discord.Member] = [
                    seeking_member
                    for seeking_member in bot_state.members_seeking_playmates.get(activity_name, [])
                    if seeking_member.activities
                    and isinstance(seeking_member.activities[0], discord.Activity)
                    and seeking_member.activities[0].name == activity_name
                    and seeking_member.guild == current_state.guild
                ]

                if len(members_with_matching_activity) > 1:
                    target_voice_channel_name: str = GAME_VOICE_CHANNEL_MAPPING.get(activity_name, CHANNEL_NAME_GENERAL_VOICE)
                    asyncio.create_task(
                        invite_members_to_voice_channel(members_with_matching_activity, target_voice_channel_name)
                    )

                # Schedule cleanup
                asyncio.create_task(
                    _delayed_playmate_cleanup(current_state, new_activity, delay_seconds=PLAYMATE_CLEANUP_DELAY)
                )

            # Clean stale entries for other activities
            for stale_activity_name in list(bot_state.members_seeking_playmates.keys()):
                if current_state in bot_state.members_seeking_playmates[stale_activity_name] and stale_activity_name != activity_name:
                    bot_state.members_seeking_playmates[stale_activity_name].remove(current_state)
                    await send_admin_notification(
                        f"Cleaned up playmate list for {current_state.name} (was in '{stale_activity_name}')"
                    )
                    if not bot_state.members_seeking_playmates[stale_activity_name]:
                        bot_state.members_seeking_playmates.pop(stale_activity_name, None)
        else:
            activity_log_message = f"{previous_state.display_name}'s activity changed (no activity)."

    # -- Display name change (nickname or global name) --
    elif previous_state.display_name != current_state.display_name:
        activity_log_message = f"{previous_state.display_name}'s display name changed to: {current_state.display_name}"

    # -- Role change --
    elif previous_state.roles != current_state.roles:
        current_role_names: list[str] = [role.name for role in current_state.roles if role.name != MEMBER_ROLE_EVERYONE]
        activity_log_message = f"{previous_state.display_name}'s roles are now: {', '.join(current_role_names) if current_role_names else 'None'}"

    else:
        activity_log_message = f"ERROR! {current_state.display_name} triggered on_member_update with no detectable change."

    await log_member_activity_to_file(previous_state.display_name, activity_log_message)
    if current_state.display_name not in bot_state.ignored_member_names:
        await send_admin_notification(activity_log_message)


async def _delayed_playmate_cleanup(
    target_member: discord.Member,
    target_activity: discord.Activity,
    delay_seconds: float,
) -> None:
    """Async wrapper for delayed playmate list cleanup."""
    await asyncio.sleep(delay_seconds)
    remove_member_from_playmate_seek(target_member, target_activity)


@BOT_CLIENT.event
async def on_member_join(new_member: discord.Member) -> None:
    """Welcome new members and assign the Pleb role."""
    welcome_channel: discord.TextChannel = await get_or_create_text_channel(new_member.guild, CHANNEL_NAME_WELCOME)
    await welcome_channel.send(f"Welcome {new_member.mention} to **{new_member.guild.name}**!", tts=True)

    join_log_message: str = f"{new_member.display_name} has joined {new_member.guild.name}!"
    await send_admin_notification(join_log_message)
    await log_member_activity_to_file(new_member.display_name, join_log_message)
    await assign_pleb_role(new_member)


@BOT_CLIENT.event
async def on_member_remove(departing_member: discord.Member) -> None:
    """Log member removal."""
    leave_log_message: str = f"{departing_member.display_name} has left {departing_member.guild.name}."
    welcome_channel: discord.TextChannel = await get_or_create_text_channel(departing_member.guild, CHANNEL_NAME_WELCOME)
    await welcome_channel.send(leave_log_message)
    await send_admin_notification(leave_log_message)
    await log_member_activity_to_file(departing_member.display_name, leave_log_message)


@BOT_CLIENT.event
async def on_member_ban(guild: discord.Guild, user: discord.User) -> None:
    """Log member bans."""
    banned_display_name: str = user.display_name

    ban_log_message = (
        f"Holy cats, **{banned_display_name}** just received the full wrath of the ban hammer! "
        f"Bye bye nerd! Don't come back to {guild.name}!"
    )
    welcome_channel: discord.TextChannel = await get_or_create_text_channel(guild, CHANNEL_NAME_WELCOME)
    await welcome_channel.send(ban_log_message, tts=True)
    await send_admin_notification(ban_log_message)
    await log_member_activity_to_file(banned_display_name, ban_log_message)


@BOT_CLIENT.event
async def on_voice_state_update(
    updated_member: discord.Member,
    previous_voice_state: discord.VoiceState,
    current_voice_state: discord.VoiceState,
) -> None:
    """Log voice state changes."""
    voice_log_message: str
    if current_voice_state.channel:
        voice_log_message = f"{updated_member.display_name} joined voice channel: {current_voice_state.channel.name}"
    elif previous_voice_state.channel:
        voice_log_message = f"{updated_member.display_name} left voice channel: {previous_voice_state.channel.name}"
    else:
        return  # No change to log

    await send_admin_notification(voice_log_message)
    await log_member_activity_to_file(updated_member.display_name, voice_log_message)


@BOT_CLIENT.event
async def on_guild_channel_create(created_channel: discord.abc.GuildChannel) -> None:
    """Log channel creation."""
    channel_log_message: str = f'A new channel named "{created_channel.name}" has been created.'
    admin_text_channel: discord.TextChannel = await get_or_create_text_channel(created_channel.guild, CHANNEL_NAME_ADMIN)
    await admin_text_channel.send(channel_log_message)
    await send_admin_notification(channel_log_message)


@BOT_CLIENT.event
async def on_guild_channel_delete(deleted_channel: discord.abc.GuildChannel) -> None:
    """Log channel deletion."""
    channel_log_message: str = f'The channel "{deleted_channel.name}" has been deleted.'
    admin_text_channel: discord.TextChannel = await get_or_create_text_channel(deleted_channel.guild, CHANNEL_NAME_ADMIN)
    await admin_text_channel.send(channel_log_message)
    await send_admin_notification(channel_log_message)


# ---------------------------------------------------------------------------
# Permission checks
# ---------------------------------------------------------------------------

def is_owner_ctx_check(command_context: commands.Context) -> bool:
    """Check if the command invoker is the bot owner (for prefix commands)."""
    return command_context.author.id == bot_state.admin_discord_id


def is_owner_interaction_check(interaction: discord.Interaction) -> bool:
    """Check if the interaction user is the bot owner (for slash commands)."""
    return interaction.user.id == bot_state.admin_discord_id


# -- Admin-only text commands (kept as prefix for simplicity) --

@BOT_CLIENT.command(name="on", hidden=True)
@commands.check(is_owner_ctx_check)
async def cmd_enable_notifications(command_context: commands.Context) -> None:
    """Turn admin notifications ON."""
    bot_state.notifications_enabled = True
    await send_admin_notification("Notifications are ON", include_timestamp=False)

    if bot_state.pending_notification_queue:
        await send_admin_notification(
            pad_log_message("Suppressed Notifications", include_timestamp=False),
            include_timestamp=False,
        )
        while bot_state.pending_notification_queue:
            await send_admin_notification(
                bot_state.pending_notification_queue.popleft(), include_timestamp=False
            )
        await send_admin_notification(
            pad_log_message("End", include_timestamp=False), include_timestamp=False,
        )

    await command_context.send("✅ Notifications are now **ON**.")


@BOT_CLIENT.command(name="off", hidden=True)
@commands.check(is_owner_ctx_check)
async def cmd_disable_notifications(command_context: commands.Context, seconds_delay: int = -1) -> None:
    """Turn admin notifications OFF, optionally re-enable after *seconds_delay*."""
    bot_state.notifications_enabled = False
    await send_admin_notification("Notifications are OFF", include_timestamp=False)

    await command_context.send("🔇 Notifications are now **OFF**.")

    if seconds_delay >= 0:
        await asyncio.sleep(seconds_delay)
        bot_state.notifications_enabled = True
        await send_admin_notification("Notifications re-enabled after delay.", include_timestamp=False)
        await command_context.send("✅ Notifications re-enabled.")


@BOT_CLIENT.command(hidden=True)
@commands.check(is_owner_ctx_check)
async def ignore_member(command_context: commands.Context, *, target_member_name: str) -> None:
    """Add a user to the ignore list."""
    if target_member_name in bot_state.ignored_member_names:
        await command_context.send(f"`{target_member_name}` is already being ignored.")
        return

    # Validate member exists in any guild
    member_exists_in_guilds: bool = any(
        guild_member.display_name == target_member_name
        for connected_guild in BOT_CLIENT.guilds
        for guild_member in connected_guild.members
    )
    if not member_exists_in_guilds:
        await command_context.send(f"Could not find a member named `{target_member_name}`.")
        return

    bot_state.ignored_member_names.insert(
        bisect([name.lower() for name in bot_state.ignored_member_names], target_member_name.lower()),
        target_member_name,
    )
    bot_state.settings["ignored_members"] = bot_state.ignored_member_names
    save_settings(bot_state.settings)
    await command_context.send(f"✅ `{target_member_name}` has been ignored.")
    await send_admin_notification(f"{target_member_name} has been added to the ignore list.")


@BOT_CLIENT.command(hidden=True)
@commands.check(is_owner_ctx_check)
async def unignore_member(command_context: commands.Context, *, target_member_name: str) -> None:
    """Remove a user from the ignore list."""
    if target_member_name not in bot_state.ignored_member_names:
        await command_context.send(f"`{target_member_name}` is not being ignored.")
        return

    bot_state.ignored_member_names.remove(target_member_name)
    bot_state.settings["ignored_members"] = bot_state.ignored_member_names
    save_settings(bot_state.settings)
    await command_context.send(f"✅ `{target_member_name}` is no longer being ignored.")
    await send_admin_notification(f"{target_member_name} has been removed from the ignore list.")


@BOT_CLIENT.command(hidden=True)
@commands.check(is_owner_ctx_check)
async def unignore_all_members(command_context: commands.Context) -> None:
    """Clear the entire ignore list."""
    bot_state.ignored_member_names.clear()
    bot_state.settings["ignored_members"] = []
    save_settings(bot_state.settings)
    await command_context.send("✅ Ignore list has been cleared.")
    await send_admin_notification("Ignore list cleared.")


@BOT_CLIENT.command()
async def invite(command_context: commands.Context, invite_target: discord.Member) -> None:
    """Invite a user to your current voice channel."""
    command_author = command_context.author
    if not isinstance(command_author, discord.Member):
        await command_context.send("❌ This command can only be used in a server.")
        return
    if command_author.voice is None or command_author.voice.channel is None:
        await command_context.send("❌ You must be in a voice channel to use this command.")
        return

    author_voice_channel = command_author.voice.channel
    if author_voice_channel is None or not isinstance(author_voice_channel, discord.VoiceChannel):
        await command_context.send("❌ You must be in a standard voice channel.")
        return
    channel_invite_link: discord.Invite = await author_voice_channel.create_invite(
        reason=f"!invite used by {command_author.display_name}",
        max_age=VOICE_INVITE_MAX_AGE,
    )

    try:
        await invite_target.send(
            f"**{command_author.name}** is inviting you to voice: https://discord.gg/{channel_invite_link.code}",
            tts=True,
        )
    except discord.Forbidden:
        await command_context.send(f"❌ Could not DM {invite_target.mention}. They may have DMs disabled.")
        return

    await command_context.send(f"✅ Invited **{invite_target.display_name}** to {author_voice_channel.name}.")
    await send_admin_notification(
        f"{command_author.display_name} invited {invite_target.display_name} to {author_voice_channel.name}"
    )


@BOT_CLIENT.command(hidden=True)
@commands.check(is_owner_ctx_check)
async def print_ignored_members(command_context: commands.Context) -> None:
    """Show the current ignore list."""
    if not bot_state.ignored_member_names:
        await command_context.send("No users are currently being ignored.")
        return

    formatted_ignored_list: str = "\n".join(
        f"• {ignored_name}" for ignored_name in bot_state.ignored_member_names
    )
    await command_context.send(f"**Ignored Members:**\n{formatted_ignored_list}")


@BOT_CLIENT.command(hidden=True)
@commands.check(is_owner_ctx_check)
async def print_tracked_members(command_context: commands.Context) -> None:
    """Show users not on the ignore list."""
    tracked_member_names: list[str] = [
        guild_member.display_name
        for connected_guild in BOT_CLIENT.guilds
        for guild_member in connected_guild.members
        if guild_member.display_name not in bot_state.ignored_member_names
    ]
    if not tracked_member_names:
        await command_context.send("No tracked members found.")
        return

    formatted_tracked_list: str = "\n".join(
        f"• {tracked_name}" for tracked_name in tracked_member_names[:50]
    )  # cap output
    await command_context.send(f"**Tracked Members:**\n{formatted_tracked_list}")


@BOT_CLIENT.command(hidden=True)
@commands.check(is_owner_ctx_check)
async def print_members_seeking(command_context: commands.Context) -> None:
    """Show members currently seeking playmates."""
    if not bot_state.members_seeking_playmates:
        await command_context.send("No members are currently seeking playmates.")
        return

    formatted_seekers: list[str] = []
    for activity_name, seeking_members_list in bot_state.members_seeking_playmates.items():
        formatted_seekers.append(
            f"**{activity_name}**: {', '.join(seeker.display_name for seeker in seeking_members_list)}"
        )
    await command_context.send("\n".join(formatted_seekers))


# -- Slash commands (application commands) --

@BOT_CLIENT.tree.command(name="insult", description="Hurl a random insult at a user.")
@app_commands.check(is_owner_interaction_check)
async def slash_command_insult(interaction: discord.Interaction, insult_target: discord.Member) -> None:
    """Send a random insult to a target user."""
    try:
        insult_content: str = await asyncio.to_thread(fetch_insult_from_api)
    except Exception:
        await interaction.response.send_message(
            "❌ Failed to fetch an insult. Try again later.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(f"{insult_target.mention} {insult_content}")


def fetch_insult_from_api() -> str:
    """Fetch an insult from the Evil Insult API (blocking call)."""
    api_response = requests.get(
        "https://evilinsult.com/generate_insult.php",
        params={"lang": "en", "type": "json"},
        timeout=10,
    )
    api_response.raise_for_status()
    return api_response.json()["insult"]


@BOT_CLIENT.tree.command(name="serverinfo", description="Display information about the current server.")
@app_commands.guild_only()
@app_commands.check(is_owner_interaction_check)
async def slash_command_serverinfo(interaction: discord.Interaction) -> None:
    """Show server info."""
    target_guild = interaction.guild
    assert target_guild is not None, "Guild-only command"

    server_info_embed = discord.Embed(
        title=target_guild.name,
        color=discord.Color.blurple(),
        timestamp=_get_utc_now(),
    )
    if target_guild.icon:
        server_info_embed.set_thumbnail(url=target_guild.icon.url)
    server_info_embed.add_field(name="Owner", value=str(target_guild.owner), inline=False)
    server_info_embed.add_field(name="Members", value=target_guild.member_count or "Unknown", inline=True)
    server_info_embed.add_field(name="Roles", value=len(target_guild.roles), inline=True)
    server_info_embed.add_field(name="Text Channels", value=len(target_guild.text_channels), inline=True)
    server_info_embed.add_field(name="Voice Channels", value=len(target_guild.voice_channels), inline=True)
    server_info_embed.add_field(name="Created", value=target_guild.created_at.strftime("%Y-%m-%d"), inline=True)
    await interaction.response.send_message(embed=server_info_embed)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@BOT_CLIENT.event
async def on_command_error(command_context: commands.Context, command_error: commands.CommandError) -> None:
    """Handle command errors globally."""
    if isinstance(command_error, commands.CommandNotFound):
        return  # ignore unknown prefix commands

    if isinstance(command_error, commands.CheckFailure):
        await command_context.send("❌ You don't have permission to use this command.")
        return

    if isinstance(command_error, commands.MemberNotFound):
        await command_context.send("❌ Could not find that member.")
        return

    logger.error("Error in command %s: %s", command_context.command, command_error, exc_info=command_error)
    await command_context.send("❌ An error occurred while processing this command.")


@BOT_CLIENT.tree.error
async def on_slash_command_error(interaction: discord.Interaction, slash_command_error: app_commands.AppCommandError) -> None:
    """Handle slash command errors globally."""
    if isinstance(slash_command_error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    logger.error("Error in slash command %s: %s", interaction.command, slash_command_error, exc_info=slash_command_error)
    if not interaction.response.is_done():
        await interaction.response.send_message("❌ An error occurred.", ephemeral=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point for Alatar Bot."""
    bot_state.settings = load_settings()

    # Reconfigure logging from settings if provided
    configured_log_max_bytes: int = bot_state.settings.get("log_max_bytes", LOG_MAX_BYTES)  # type: ignore[assignment]
    configured_log_backup_count: int = bot_state.settings.get("log_backup_count", LOG_BACKUP_COUNT)  # type: ignore[assignment]
    for existing_handler in logger.handlers[:]:
        logger.removeHandler(existing_handler)
    configured_log_handler: RotatingFileHandler = RotatingFileHandler(
        filename=LOG_FILE,
        encoding="utf-8",
        maxBytes=configured_log_max_bytes,
        backupCount=configured_log_backup_count,
    )
    configured_log_handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    logger.addHandler(configured_log_handler)

    try:
        bot_state.admin_discord_id = initialize_admin_discord_id(bot_state.settings)
    except (TypeError, ValueError) as initialization_error:
        logger.critical("Failed to initialize admin ID: %s", initialization_error)
        raise SystemExit(1)

    try:
        bot_token: str = initialize_bot_token(bot_state.settings)
    except (TypeError, ValueError) as token_error:
        logger.critical("Failed to initialize bot token: %s", token_error)
        raise SystemExit(1)

    BOT_CLIENT.run(bot_token, log_handler=None)


if __name__ == "__main__":
    main()
