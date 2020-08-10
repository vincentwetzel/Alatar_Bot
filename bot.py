# TODO: Eliminate all send_message
# TODO: Make the whole damn thing OOP
# TODO: DOCUMENT THIS BITCH
# TODO: verify voice room invites are working
# TODO: Take out stuff from Mike Pence's Electrocution Dungeon
# TODO: Add annotations for everything
# TODO: Move welcome message to 'welcome' channel instead of 'general'
# TODO: verify all str casts and make sure they are needed.
# TODO: Do a MASSIVE update on Event References.
#       https://discordpy.readthedocs.io/en/latest/api.html#utility-functions
# TODO: Make sure that annotations correctly specify between discord.User and discord.Member
# TODO: Make sure all """Admin Command""" BS has been removed.
# TODO: Purge all mentions of "server" and replace with "guild"
# TODO: Add functionality to determine the bot admin at startup. Store this info in a log txt rather than in the script itself.

import discord
from discord.ext import commands
from datetime import datetime
import os.path
import logging
from bisect import bisect
import asyncio
from typing import List

# logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Initialize Bot settings
description = '''This is Vincent's Discord Bot. Use the !command syntax to send a command to the bot.'''
bot = commands.Bot(command_prefix='!', description=description)

# Globals
alertsOn = True
messages_waiting_to_send = []  # TODO: Optimize this by making it a deque, not a list
member_names_to_ignore: List[str] = list()
players_seeking_playmates: List[discord.Member] = list()
admin_discord_id = 251934924196675595
MEMBERS_TO_IGNORE_FILE = "users_to_ignore.txt"


@bot.event
async def on_ready():
    msg = await pad_message("AlatarBot is now online!") + "\n"
    await log_msg_to_Discord_pm(msg, False)

    global member_names_to_ignore
    if os.path.exists(MEMBERS_TO_IGNORE_FILE):
        with open(MEMBERS_TO_IGNORE_FILE, 'r') as f:  # 'r' is reading mode, stream positioned at start of file
            for line in f:
                member_names_to_ignore.append(line.strip('\n'))
    else:
        file = open(MEMBERS_TO_IGNORE_FILE,
                    "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
        file.close()


@bot.event
async def on_message(message: discord.Message):
    """
    This runs when the bot detects a new message.
    :param message:
    :return:
    """
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    # need this line, it prevents the bot from hanging
    await bot.process_commands(message)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # TODO: This method is throwing an error when new members join. Figure out why and fix it.
    # Process sneaky offline mode status changes
    if str(before.status) == "offline" and str(after.status) == "offline":
        msg = str(before.name) + " is in OFFLINE MODE."

    # Process status changes
    elif before.status != after.status:
        msg = (((str(before.name) + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44, ' ')
               + "(was " + str(before.status).upper() + ")")

    # Process activity changes
    elif before.activity != after.activity:
        if after.activity is None:
            msg = str(before.name + " STOPPED playing: ").ljust(35, ' ') + before.activity.name
        else:
            msg = str(before.name + " STARTED playing: ").ljust(35, ' ') + after.activity.name

            global players_seeking_playmates
            if after not in players_seeking_playmates:
                # Voice Room controls
                members_in_same_game = [after]  # initialize list with one member in it

                players_seeking_playmates.append(after)
                for member in players_seeking_playmates:
                    if member != after and member.activity == after.activity and member.server == after.server:
                        members_in_same_game.append(member)

                # If there are more than 1 players in a game, activate voice room controls
                if len(members_in_same_game) > 1:
                    if str(after.activity.name) == "PLAYERUNKNOWN'S BATTLEGROUNDS" or str(
                            after.activity.name) == "PUBG":
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel(335193104703291393))  # PUBG Rage-Fest
                    elif str(after.activity.name) == "League of Legends":
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel(349099177189310475))  # Teemo's Treehouse
                    else:
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel(335188428780208130))  # Ian's Sex Dungeon

                event_loop = asyncio.get_event_loop()
                event_loop.call_later(300.0, pop_member_from_voice_room_seek, after)

    # Process nickname changes
    elif before.nick != after.nick:
        if after.nick is None:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + str(after.name)
        elif before.nick is None:
            msg = (str(before.name) + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)
        else:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)

    # Process member_name changes
    elif str(before.name) != str(after.name):
        msg = str(before.name + "\'s new member_name is: ").ljust(35, ' ') + str(after.name)

    # Process role changes
    elif before.roles != after.roles:
        new_roles = ""
        for x in after.roles:
            if str(x.name) == "@everyone":
                continue
            if new_roles == "":
                new_roles += str(x.name)
            else:
                new_roles += ", " + str(x.name)

        msg = (str(before.name) + "\'s roles are now: ") + (new_roles if new_roles != "" else "None")

    # Process avatar changes
    elif before.avatar != after.avatar:
        msg = str(before.name) + " now has a new avatar!"

    # Process errors
    else:
        msg = "ERROR!!! " + str(after.name) + " has caused an error in on_member_update()."

    await log_user_activity_to_file(str(before.name), msg)

    global member_names_to_ignore
    if after.name not in member_names_to_ignore:
        await log_msg_to_Discord_pm(msg)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    """
    Welcomes new members, assigns them the Pleb role.
    :param member: The new member
    :return: None
    """
    await (await get_default_text_channel(member.guild)).send(
        "Welcome " + member.display_name + " to " + member.guild.name + "!", tts=True)

    msg: str = member.display_name + " has joined " + member.guild.name + "!"
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(member.display_name, msg)

    pleb_role: discord.Role = discord.utils.get(member.guild.roles, name="Plebs")
    if pleb_role is None:
        pleb_role = await member.guild.create_role(name="Plebs", hoist=True, mentionable=True,
                                                   reason="Pleb role for the plebs")
        await log_msg_to_Discord_pm("The Pleb role did not exist, so the bot has created it.")
    await member.add_roles(pleb_role)


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    """
    Event for when a member is removed from the Guild.
    :param member:
    :return:
    """
    msg = str(member.display_name) + " has left " + str(member.guild) + "."

    await (await get_default_text_channel(member.guild)).send(msg)
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_member_ban(guild: discord.Guild, member: discord.Member) -> None:
    """
    Stuff that happens when a member gets banned
    :param member: The person who got banned
    :return: None
    """
    msg = ("Holy cats, " + str(member.display_name)
           + " just received the full wrath of the ban hammer! Bye bye nerd! Don't come back to "
           + str(member.guild) + "!")
    await (await get_default_text_channel(member.guild)).send(msg, tts=True)
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    if after.channel != None:
        msg = member.display_name + " joined voice channel: ".ljust(25, ' ') + after.channel.name
    else:
        msg = member.display_name + " left voice channel: ".ljust(25, ' ') + before.channel.name
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    """
    Handles the event when a new guild channel is created.
    :param channel: The channel that was created
    :return: None
    """
    msg: str = "A new " + str(channel.category) + " channel named \"" + str(channel.name) + "\" has been created."
    await (await get_default_text_channel(channel.guild)).send(msg)
    await log_msg_to_Discord_pm(msg)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    """
    Handles the event when a guild channel is deleted.
    :param channel: The channel that was deleted
    :return: None
    """
    msg: str = "The " + str(channel.category) + " channel \"" + str(channel.name) + "\" has been deleted."
    await (await get_default_text_channel(channel.guild)).send(msg)
    await log_msg_to_Discord_pm(msg)


@bot.command(hidden=True)
async def on(context: discord.ext.commands.Context) -> None:
    """
    Turns logging on
    :param context:
    :return:
    """
    # TODO: Remove globals, make OOP
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_Discord_pm("Notifications are ON")

    # Catch up on notifications waiting to be sent.
    global messages_waiting_to_send
    if messages_waiting_to_send:
        await log_msg_to_Discord_pm(await pad_message("Suppressed Notifications", False), False)
        while messages_waiting_to_send:
            msg = messages_waiting_to_send.pop(0)  # pop from FRONT of list
            await log_msg_to_Discord_pm(msg, False)
        await log_msg_to_Discord_pm(await pad_message("End", False), False)


@bot.command(hidden=True)
async def off(context: discord.ext.commands.Context) -> None:
    """
    Turns logging OFF
    :param context: Context
    :return: None
    """
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_Discord_pm("Notifications are OFF")
    alertsOn = False


@bot.command(hidden=True)
async def ignore(context: discord.ext.commands.Context, member_name_to_ignore: str) -> None:
    """
    Ignores a user from activity logging.
    :param context: The context.
    :param member_name_to_ignore: The name of the Member to ignore.
    :return: None
    """
    # TODO: Make OOP

    # Only allow the admin to use this command
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    # Search to see if the member is already being ignored
    global member_names_to_ignore
    if member_name_to_ignore in member_names_to_ignore:
        await log_msg_to_Discord_pm(member_name_to_ignore + " is already being ignored.")
        return

    # If user is not in any of the bot's servers, ignore the ignore command
    member_found = False
    for guild in bot.guilds:
        for member in guild.members:
            if member.display_name == member_name_to_ignore:
                member_found = True
                break
        if member_found:
            break

    # If the member is not found, return.
    if not member_found:
        await log_msg_to_Discord_pm(member_name_to_ignore + " could not be found.")
        return

    # Add the Member's name to our running list
    member_names_to_ignore.insert(
        bisect([i.lower() for i in member_names_to_ignore], member_name_to_ignore.lower()),
        member_name_to_ignore)

    # Add the Member's name to our persistent file
    with open("users_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        for user in member_names_to_ignore:
            f.write(user + '\n')

    # Log the results
    await log_msg_to_Discord_pm(member_name_to_ignore + " has been ignored.")
    await printignored(context)


@bot.command(hidden=True)
async def unignore(context: discord.ext.commands.Context, member_name_to_unignore: str) -> None:
    """
    Removes a Member from the ignore list
    :param context: The context
    :param member_name_to_unignore: The member's name
    :return: None
    """
    # TODO: Make OOP
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    # If they are not being ignored, disregard the command
    global member_names_to_ignore
    if member_name_to_unignore not in member_names_to_ignore:
        await log_msg_to_Discord_pm(member_name_to_unignore + " is not currently being ignored.")
        return

    # Remove the Member from the ignore list
    member_names_to_ignore.remove(member_name_to_unignore)
    with open("users_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        for user in member_names_to_ignore:
            f.write(user + '\n')
    await log_msg_to_Discord_pm(member_name_to_unignore + " is no longer being ignored.")
    await printignored(context)


@bot.command(hidden=True)
async def unignoreall(context: discord.ext.commands.Context):
    """

    :param context:
    :return:
    """
    # TODO: Update documentation
    # TODO: Make OOP
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    global member_names_to_ignore
    member_names_to_ignore.clear()
    users_to_ignore_file = "users_to_ignore.txt"

    # Write a new file
    file = open(users_to_ignore_file, "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
    file.close()
    await log_msg_to_Discord_pm("Ignore list has been cleared.")


@bot.command()
async def invite(context: discord.ext.commands.Context, member_to_invite: discord.Member):
    """
    !invite username - invites a user to your current voice room.
    :param context: The current context
    :param member_to_invite: The user to invite to your current voice room.
    :return:
    """
    author: discord.Member = context.message.author

    # Check the VoiceState to see if the command's author is in a voice room
    if author.voice is None:
        await log_msg_to_Discord_pm(
            author.display_name + " attempted to use an !invite command but they are not in a voice room.")
        return

    voice_channel: discord.VoiceChannel = author.voice.channel

    inv: discord.Invite = await voice_channel.create_invite(
        reason="!invite command was invoked by " + author.display_name,
        max_age=3600)

    await member_to_invite.send(author.name + " is inviting you to a voice chat. https://discord.gg/" + inv.code,
                                tts=True)
    await author.send(
        "You have invited " + member_to_invite.name + " to the voice room " + voice_channel.name + " in " + author.guild.name,
        tts=False)

    await log_msg_to_Discord_pm(
        author.display_name + " has invited " + member_to_invite.display_name + " to the voice room " + voice_channel.name)


@bot.command(hidden=True)
async def printignored(context) -> None:
    """
    Prints a list of the users currently being ignored
    :param context: The context
    :return: None
    """
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    global member_names_to_ignore

    if not member_names_to_ignore:
        await log_msg_to_Discord_pm("There are currently no members being ignored.", False)
    else:
        msg = await pad_message("Ignored Users", add_time_and_date=False) + "\n"
        for member in member_names_to_ignore:
            msg = msg + member + '\n'
        msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
        await log_msg_to_Discord_pm(msg, False)


@bot.command(hidden=True)
async def printnotignored(context: discord.ext.commands.Context) -> None:
    """
    Prints a list of users not ignored by the bot.
    :param context:
    :return:
    """
    # Only allow this command to be done by the admin
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    global member_names_to_ignore

    msg: str = await pad_message("Users Not Ignored", add_time_and_date=False) + "\n"
    members_not_ignored: List[discord.Member] = list()

    for guild in bot.guilds:
        for member in guild.members:
            if member.name not in member_names_to_ignore and member not in members_not_ignored:
                members_not_ignored.append(member)

    for m in members_not_ignored:
        msg = msg + m.display_name + '\n'

    msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
    await log_msg_to_Discord_pm(msg, False)


@bot.command(hidden=True)
async def printseeking(context: discord.ext.commands.Context) -> None:
    """
    Prints a list of players who have recently started an activity (game) and are seeking friends.
    :param context: The context.
    :return: None
    """
    global admin_discord_id
    if context.message.author.id != admin_discord_id:
        return

    global players_seeking_playmates
    if not players_seeking_playmates:
        await log_msg_to_Discord_pm("No members are currently seeking friends to play with.")
    else:
        msg = await pad_message("Players Seeking Playmates", add_time_and_date=False) + "\n"
        for player in players_seeking_playmates:
            msg = msg + player.name + "\n"
        msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
        await log_msg_to_Discord_pm(msg, False)


@bot.command()
async def time(context):
    """
    The bot replies with the current time and date.
    :param context:
    :return:
    """
    await context.send("Current time is: " + datetime.now().strftime(
        "%I:%M:%S %p") + " on " + datetime.now().strftime("%A, %B %d, %Y"))


async def pad_message(msg, add_time_and_date=True, dash_count=75):
    """
    Pads a message with stars
    :param msg: The message
    :param add_time_and_date: Adds time and date
    :param dash_count: The number of stars to use in the padding
    :return:
    """
    if add_time_and_date:
        msg = "\n" + (await add_time_and_date_to_string(msg)) + "\n"
    else:
        msg = "\n" + msg + "\n"
    # dash_count = len(log_msg) - 2
    for x in range(dash_count):
        msg = "-".join(["", msg, ""])
    return msg


async def add_time_and_date_to_string(msg):
    return datetime.now().strftime("%m-%d-%y") + "\t" + datetime.now().strftime("%I:%M:%S%p") + "\t" + msg


@bot.command(hidden=True)
async def log_msg_to_Discord_pm(msg: str, add_time_and_date: bool = True, tts_param=False):
    """
    Sends a DM to the bot's owner.
    :param msg: The message to send
    :param add_time_and_date: Prepend information about the date and time of the logging item
    :param tts_param: Text-to-speech option
    :return:
    """
    # TODO: Remove globals, make OOP
    msg = await add_time_and_date_to_string(msg) if (add_time_and_date is True) else msg
    global alertsOn
    if alertsOn:
        global admin_discord_id
        await (await bot.fetch_user(admin_discord_id)).send(msg, tts=tts_param)
    else:
        global messages_waiting_to_send
        messages_waiting_to_send.append(msg)


async def log_user_activity_to_file(member_name: str, log_msg: str) -> None:
    """
    Creates/appends to a log file specific for a user.
    :param member_name: The name of the uer being logged
    :param log_msg: The information to be logged
    :return:
    """
    log_msg = await add_time_and_date_to_string(log_msg)
    filepath = "logs/" + member_name + ".txt"
    with open(filepath, "a+", encoding="utf-8") as file:  # "a+" means append mode, create the file if it doesn't exist.
        file.write(log_msg + "\n")


async def invite_member_to_voice_channel(members_in_same_game: List[discord.Member],
                                         voice_channel: discord.VoiceChannel):
    invite = await (bot.create_invite(voice_channel, max_age=3600))
    for member in members_in_same_game:
        if member.voice.voice_channel == voice_channel:
            continue
        elif member.voice.voice_channel is None:  # is NOT in voice voice_channel
            await member.send("You are not the only person playing "
                              + str(members_in_same_game[0].activity)
                              + ". Here's a voice room you can join your friends in: https://discord.gg/"
                              + invite.code, tts=True)
            msg = str(member.display_name) + " was INVITED to " + str(voice_channel.name)
            await log_msg_to_Discord_pm(msg)
            await log_user_activity_to_file(str(member.display_name), msg)
        else:
            await bot.move_member(member, voice_channel)
            await member.send("Greetings " + str(member.display_name)
                              + "! Due to the fact that you are currently playing " + str(member.activity.name)
                              + ", I have moved you to a more appropriate"
                              + " voice room so you can join your friends.",
                              tts=True)
            msg = str(member.display_name) + " was MOVED to " + str(voice_channel.name)
            await log_msg_to_Discord_pm(msg)
            await log_user_activity_to_file(str(member.display_name), msg)


def initialize_bot_token():
    token_file = "token.txt"
    if not os.path.exists(token_file):
        with open(token_file, 'a') as f:  # 'a' opens for appending without truncating
            token = input("The token file does not exist. Please enter the bot's token: ")
            f.write(token)
            # f.close()# Do not need this line because file was opened using "with"
    else:
        with open(token_file, 'r+') as f:  # 'r+' is reading/writing mode, stream positioned at start of file
            token = f.readline().rstrip('\n')  # readline() usually has a \n at the end of it
            if not token:
                token = input("The token file is empty. Please enter the bot's token: ")
                f.write(token)
            # f.close() # Do not need this line because file was opened using "with"
    return token


async def get_default_text_channel(guild: discord.Guild) -> discord.TextChannel:
    default_text_channel = None
    idx = 0

    # Find the channel if it exists
    for channel in list(guild.text_channels):
        if channel.name == "general":
            return channel

    # If no general channel exists, create one.
    return await guild.create_text_channel("general", reason="Default text channel")


def pop_member_from_voice_room_seek(member):
    # TODO: Is this the best way of doing this???
    global players_seeking_playmates
    players_seeking_playmates.remove(member)


if __name__ == "__main__":
    bot.run(initialize_bot_token())
