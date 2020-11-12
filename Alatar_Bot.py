# for Discord
from threading import Timer

import discord
from discord.ext import commands
import asyncio

# or Insults API
import requests
import json

# for general
import logging
from datetime import datetime
import os.path
from bisect import bisect  # Allows list insertion while maintaining order
from typing import List, DefaultDict
from collections import deque, defaultdict

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Globals
alertsOn = True
"""bool to toggle alerts"""
messages_waiting_to_send = deque()
"""Queues all messages waiting to send"""
member_names_to_ignore: List[str] = list()
members_seeking_playmates: DefaultDict[str, List[discord.Member]] = defaultdict(list)
"""{activity.name : List[discord.Member]}"""

MEMBERS_TO_IGNORE_FILE = "members_to_ignore.txt"
"""A file that keeps control of the members being ignored by the bot for status updates."""
ADMIN_DISCORD_ID = None
"""This is the main person the bot communicates with"""

# Init bot
description = '''This is Vincent's Bot for server management. Use the !command syntax to send a command to the bot.'''
bot = commands.Bot(command_prefix='!', description=description)


@bot.event
async def on_ready():
    msg = await pad_message("Alatar Bot is now online!") + "\n"
    await log_msg_to_server_owner(msg, False)

    # Initialize member_names_to_ignore
    global member_names_to_ignore
    if os.path.exists(MEMBERS_TO_IGNORE_FILE):
        with open(MEMBERS_TO_IGNORE_FILE, 'r') as f:  # 'r' is reading mode, stream positioned at start of file
            for line in f:
                member_names_to_ignore.append(line.strip('\n'))
    else:
        # Create file for later use
        file = open(MEMBERS_TO_IGNORE_FILE,
                    "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
        file.close()

    # Double check everyone's roles.
    for guild in bot.guilds:
        for member in guild.members:
            if len(member.roles) == 1 and member.roles[0].name == "@everyone":
                await add_pleb_role(member)


@bot.event
async def on_socket_raw_receive(msg) -> None:
    """
    Logs whenever a socket receives raw content.
    :param msg: The information received by the socket
    :return: None
    """
    # logging.debug(msg)  # Comment this line out during normal operations
    pass


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    This runs when the bot detects a new message.
    :param message: The Message that the bot has detected.
    :return: None
    """
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    # need this line, it prevents the bot from hanging
    await bot.process_commands(message)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    """
    Handle Member status updates
    :param before: The Member before the status change.
    :param after: The Member after the status change
    :return: None
    """

    # Process status changes
    if before.status != after.status:
        # Desktop change
        if before.mobile_status is discord.enums.Status.offline and after.mobile_status is discord.enums.Status.offline:
            msg = ((str(before.display_name) + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44,
                                                                                                             ' ') + ", \twas " + str(
                before.status).upper()
        elif before.mobile_status is not after.mobile_status:
            msg = ((str(before.display_name) + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44,
                                                                                                             ' ') + " (MOBILE), \t was " + str(
                before.status).upper() + " (MOBILE)."
        elif before.web_status is not after.web_status:
            msg = (str(before.display_name + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44,
                                                                                                           ' ') + " (WEB), \t was " + str(
                before.status).upper() + " (WEB)."
        else:
            msg = "Something weird happened when " + before.display_name + " updated their status."


    # Process activity changes
    elif before.activity != after.activity or before.activities != after.activities:
        if after.activity is None:
            msg = before.display_name + " STOPPED playing: \t" + before.activity.name
        else:
            msg = before.display_name + " STARTED playing: \t" + after.activity.name

            # Figure out if the activity change should trigger the bot to take action regarding Voice Rooms
            global members_seeking_playmates
            if after not in members_seeking_playmates[after.activity.name]:
                # initialize a list with one member in it
                members_in_same_game = [after]

                # Make a list of other members in this same game
                members_seeking_playmates[after.activity.name].append(after)
                for member in list(members_seeking_playmates[after.activity.name]):
                    if member != after and member.activity.name == after.activity.name and member.guild == after.guild:
                        members_in_same_game.append(member)

                # If there are more than 1 players in a game, try to get them all in the same room
                if len(members_in_same_game) > 1:
                    if after.activity.name == "PLAYERUNKNOWN'S BATTLEGROUNDS" or after.activity.name == "PUBG":
                        await invite_members_to_voice_channel(members_in_same_game, "PUBG Rage-Fest")
                    elif after.activity.name == "League of Legends":
                        await invite_members_to_voice_channel(members_in_same_game, "Teemo's Treehouse")
                    else:
                        await invite_members_to_voice_channel(members_in_same_game, "General")

                # Sleep for an interval then remove this Member from members_seeking_playmates
                await asyncio.sleep(15)
                if member in members_seeking_playmates[after.activity.name]:
                    members_seeking_playmates[after.activity.name].remove(member)
                    if not members_seeking_playmates[after.activity.name]:
                        members_seeking_playmates.pop(after.activity.name)
            for activity_name in list(members_seeking_playmates.keys()):
                if after in list(members_seeking_playmates[activity_name]) and activity_name != after.activity.name:
                    members_seeking_playmates[activity_name].remove(after)
                    if not members_seeking_playmates[activity_name]:
                        members_seeking_playmates.pop(activity_name)

    # Process nickname changes
    elif before.nick != after.nick:
        if after.nick is None:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + after.name
        elif before.nick is None:
            msg = (before.name + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)
        else:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)

    # Process display_name changes
    elif before.display_name != after.display_name:
        msg = (before.name + "\'s new member_name is: ").ljust(35, ' ') + after.name

    # Process role changes
    elif before.roles != after.roles:
        new_roles = ""
        for role in after.roles:
            if str(role.name) == "@everyone":
                continue
            if new_roles == "":
                new_roles += str(role.name)
            else:
                new_roles += ", " + str(role.name)

        msg = (before.name + "\'s roles are now: ") + (new_roles if new_roles != "" else "None")

    # Process errors
    else:
        msg = "ERROR!!! " + after.name + " has caused an error in on_member_update()."

    # Log the changes
    await log_user_activity_to_file(str(before.name), msg)
    if after.name not in member_names_to_ignore:
        await log_msg_to_server_owner(msg)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    """
    Welcomes new members, assigns them the Pleb role.
    :param member: The new Member
    :return: None
    """
    await (await get_text_channel(member.guild, "welcome")).send(
        "Welcome " + member.display_name + " to " + member.guild.name + "!", tts=True)

    msg: str = member.display_name + " has joined " + member.guild.name + "!"
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)

    add_pleb_role(member)


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    """
    Event for when a Member is removed from the Guild.
    :param member: The Member who has been removed
    :return: None
    """
    msg = member.display_name + " has left " + str(member.guild) + "."

    await (await get_text_channel(member.guild, "welcome")).send(msg)
    await log_msg_to_server_owner(msg)
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
    await (await get_text_channel(member.guild, "welcome")).send(msg, tts=True)
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    if after.channel != None:
        msg = member.display_name + " joined voice channel: ".ljust(25, ' ') + after.channel.name
    else:
        msg = member.display_name + " left voice channel: ".ljust(25, ' ') + before.channel.name
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    """
    Handles the event when a new guild channel is created.
    :param channel: The channel that was created
    :return: None
    """
    msg: str = "A new channel named \"" + channel.name + "\" has been created."
    await (await get_text_channel(channel.guild, "admin")).send(msg)
    await log_msg_to_server_owner(msg)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    """
    Handles the event when a guild channel is deleted.
    :param channel: The channel that was deleted
    :return: None
    """
    msg: str = "The channel \"" + channel.name + "\" has been deleted."
    await (await get_text_channel(channel.guild, "admin")).send(msg)
    await log_msg_to_server_owner(msg)


@bot.command(hidden=True)
async def on(ctx: discord.ext.commands.Context) -> None:
    """
    Turns logging on
    :param ctx: The Context of the command
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_server_owner("Notifications are ON")

    # Catch up on notifications waiting to be sent.
    global messages_waiting_to_send
    if messages_waiting_to_send:
        await log_msg_to_server_owner(await pad_message("Suppressed Notifications", False), False)
        while messages_waiting_to_send:
            msg = messages_waiting_to_send.popleft()  # pop from FRONT of list
            await log_msg_to_server_owner(msg, False)
        await log_msg_to_server_owner(await pad_message("End", False), False)


@bot.command(hidden=True)
async def off(ctx: discord.ext.commands.Context, seconds_delay: int = -1) -> None:
    """
    Turns logging OFF
    :param ctx: The ctx of the command
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_server_owner("Notifications are OFF")
    alertsOn = False

    if seconds_delay < 0:
        pass
    else:
        await asyncio.sleep(seconds_delay)
        await on(ctx)


@bot.command(hidden=True)
async def ignore(ctx: discord.ext.commands.Context, member_name_to_ignore: str) -> None:
    """
    Ignores a user from activity logging.
    :param ctx: The ctx of the command.
    :param member_name_to_ignore: The name of the Member to ignore.
    :return: None
    """

    # Only allow the admin to use this command
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    # Search to see if the member is already being ignored
    global member_names_to_ignore
    if member_name_to_ignore in member_names_to_ignore:
        await log_msg_to_server_owner(member_name_to_ignore + " is already being ignored.")
        return

    # If user is not in any of the bot's guilds, ignore the ignore command
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
        await log_msg_to_server_owner(member_name_to_ignore + " could not be found.")
        return

    # Add the Member's name to our running list
    member_names_to_ignore.insert(
        bisect([i.lower() for i in member_names_to_ignore], member_name_to_ignore.lower()),
        member_name_to_ignore)

    # Add the Member's name to our persistent file
    with open("members_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        for user in member_names_to_ignore:
            f.write(user + '\n')

    # Log the results
    await log_msg_to_server_owner(member_name_to_ignore + " has been ignored.")
    await printignored(ctx)


@bot.command(hidden=True)
async def unignore(ctx: discord.ext.commands.Context, member_name_to_unignore: str) -> None:
    """
    Removes a Member from the ignore list
    :param ctx: The ctx
    :param member_name_to_unignore: The Member's name
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    # If they are not being ignored, disregard the command
    global member_names_to_ignore
    if member_name_to_unignore not in member_names_to_ignore:
        await log_msg_to_server_owner(member_name_to_unignore + " is not currently being ignored.")
        return

    # Remove the Member from the ignore list
    member_names_to_ignore.remove(member_name_to_unignore)
    with open("members_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        for user in member_names_to_ignore:
            f.write(user + '\n')
    await log_msg_to_server_owner(member_name_to_unignore + " is no longer being ignored.")
    await printignored(ctx)


@bot.command(hidden=True)
async def unignoreall(ctx: discord.ext.commands.Context) -> None:
    """
    Removes all users from the ignore list.
    :param ctx: The Context of the command.
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    global member_names_to_ignore
    member_names_to_ignore.clear()
    users_to_ignore_file = "members_to_ignore.txt"

    # Write a new file
    file = open(users_to_ignore_file, "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
    file.close()
    await log_msg_to_server_owner("Ignore list has been cleared.")


@bot.command()
async def invite(ctx: discord.ext.commands.Context, member_to_invite: discord.Member) -> None:
    """
    !invite username - invites a user to your current voice room.
    :param ctx: The current ctx
    :param member_to_invite: The user to invite to your current voice room.
    :return: None
    """
    author: discord.Member = ctx.message.author

    # Check the VoiceState to see if the command's author is in a voice room
    if author.voice is None:
        await log_msg_to_server_owner(
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

    await log_msg_to_server_owner(
        author.display_name + " has invited " + member_to_invite.display_name + " to the voice room " + voice_channel.name)


@bot.command(hidden=True)
async def printignored(ctx: discord.ext.commands.Context) -> None:
    """
    Prints a list of the users currently being ignored
    :param ctx: The ctx of the command
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    if not member_names_to_ignore:
        await log_msg_to_server_owner("There are currently no members being ignored.", False)
    else:
        msg = await pad_message("Ignored Users", add_time_and_date=False) + "\n"
        for member in member_names_to_ignore:
            msg = msg + member + '\n'
        msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
        await log_msg_to_server_owner(msg, False)


@bot.command(hidden=True)
async def printnotignored(ctx: discord.ext.commands.Context) -> None:
    """
    Prints a list of users not ignored by the bot.
    :param ctx: The ctx of the command
    :return: None
    """
    # Only allow this command to be done by the admin
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return

    msg: str = await pad_message("Users Not Ignored", add_time_and_date=False) + "\n"
    members_not_ignored: List[discord.Member] = list()

    for guild in bot.guilds:
        for member in guild.members:
            if member.name not in member_names_to_ignore and member not in members_not_ignored:
                members_not_ignored.append(member)

    for m in members_not_ignored:
        msg = msg + m.display_name + '\n'

    msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
    await log_msg_to_server_owner(msg, False)


@bot.command(hidden=True)
async def printseeking(ctx: discord.ext.commands.Context) -> None:
    """
    Prints a list of players who have recently started an activity (game) and are seeking friends.
    :param ctx: The ctx.
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        await log_msg_to_server_owner("An unauthorized user attempted to use this command!")
        return

    if not members_seeking_playmates:
        await log_msg_to_server_owner("No members are currently seeking friends to play with.")
    else:
        msg = await pad_message("Players Seeking Playmates", add_time_and_date=False) + "\n"
        for activity in list(members_seeking_playmates.keys()):
            msg += "\nACTIVITY: " + activity + "\n"
            for member in list(members_seeking_playmates[activity]):
                msg = msg + member.name + "\n"
        msg = msg + "\n" + await pad_message("End", add_time_and_date=False) + "\n"
        await log_msg_to_server_owner(msg, False)


@bot.command()
async def time(ctx: discord.ext.commands.Context) -> None:
    """
    The bot replies with the current time and date.
    :param ctx: The Context of the command.
    :return: None
    """
    await ctx.send("Current time is: " + datetime.now().strftime(
        "%I:%M:%S %p") + " on " + datetime.now().strftime("%A, %B %d, %Y"))


async def pad_message(msg, add_time_and_date=True, dash_count=75) -> str:
    """
    Pads a message with stars
    :param msg: The message
    :param add_time_and_date: Adds time and date
    :param dash_count: The number of stars to use in the padding
    :return: A new string with the original message padded with stars.
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


async def log_msg_to_server_owner(msg: str, add_time_and_date: bool = True, tts_param=False):
    """
    Sends a DM to the bot's owner.
    :param msg: The message to send
    :param add_time_and_date: Prepend information about the date and time of the logging item
    :param tts_param: Text-to-speech option
    :return:
    """
    msg = await add_time_and_date_to_string(msg) if (add_time_and_date is True) else msg
    global alertsOn
    if alertsOn:
        await (await bot.fetch_user(ADMIN_DISCORD_ID)).send(msg, tts=tts_param)
    else:
        global messages_waiting_to_send
        messages_waiting_to_send.append(msg)


async def log_user_activity_to_file(member_name: str, log_msg: str) -> None:
    """
    Creates/appends to a log file specific for a user.
    :param member_name: The name of the uer being logged
    :param log_msg: The information to be logged
    :return: None
    """
    log_msg = await add_time_and_date_to_string(log_msg)
    filepath = "logs/" + member_name + ".txt"
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    with open(filepath, "a+", encoding="utf-8") as file:  # "a+" means append mode, create the file if it doesn't exist.
        file.write(log_msg + "\n")


async def invite_members_to_voice_channel(members_in_same_game: List[discord.Member],
                                          voice_channel_name: str) -> None:
    """
    Invites a list of Members to a voice channel.
    :param members_in_same_game: The list of Members to invite
    :param voice_channel_name:  The Voice Channel to invite the Members to.
    :return: None
    """
    voice_channel = discord.utils.get(members_in_same_game[0].guild.voice_channels, name=voice_channel_name)
    if voice_channel is None:
        cat = discord.utils.get(members_in_same_game[0].guild.categories, name="Voice Channels")
        if cat is None:
            cat = await members_in_same_game[0].guild.create_category("Voice Channels", overwrites=None,
                                                                      reason="Category did not exist")
            await log_msg_to_server_owner("Category did not exist and has been created")
        else:
            await log_msg_to_server_owner("Category already existed.")
        voice_channel = await members_in_same_game[0].guild.create_voice_channel(voice_channel_name,
                                                                                 bitrate=64000,
                                                                                 user_limit=10,
                                                                                 overwrites=None,
                                                                                 category=cat,
                                                                                 reason="Voice Channel did not exist but was requested by 2+ players playing the same game."
                                                                                 )

    invite = await (voice_channel.create_invite(
        reason="multiple members are in the same game so the bot is inviting them to the same voice room",
        max_age=3600))

    for member in members_in_same_game:
        if member.voice and member.voice.channel == voice_channel:
            continue
        elif member.voice is None:  # is NOT in voice voice_channel_name
            await member.send("You are not the only person playing "
                              + members_in_same_game[0].activity.name
                              + ". Here's a voice room you can join your friends in: https://discord.gg/"
                              + invite.code, tts=True)
            msg = member.display_name + " was INVITED to " + voice_channel.name
            await log_msg_to_server_owner(msg)
            await log_user_activity_to_file(member.display_name, msg)
        else:
            await member.move_to(voice_channel)
            await member.send("Greetings " + member.display_name
                              + "! Due to the fact that you are currently playing " + str(member.activity.name)
                              + ", I have moved you to a more appropriate"
                              + " voice room so you can join your friends.",
                              tts=True)
            msg = member.display_name + " was MOVED to " + voice_channel.name
            await log_msg_to_server_owner(msg)
            await log_user_activity_to_file(member.display_name, msg)


@bot.command()
async def insult(ctx: discord.ext.commands.Context, member_name: str) -> None:
    """
    !insult user - Hurls an insult at a targetted user.
    :param ctx: The Context of the Command.
    :param name: The name of the user to insult
    :return: None
    """
    response = requests.get("https://evilinsult.com/generate_insult.php?lang=en&type=json")
    insult = json.loads(response.text)['insult']

    if ctx.message.mentions:
        member = ctx.message.mentions[0]
    else:
        member = discord.utils.get(ctx.guild.members, name=member_name)

    if member:
        await ctx.send(member.mention + " " + insult)
    else:
        await ctx.send("That is not a member of this guild. Choose a better target to insult!")


async def get_text_channel(guild: discord.Guild, channel_name: str) -> discord.TextChannel:
    """
    Gets the text channel requested, creates if the channel does not exist.
    :param guild: The Guild for this request
    :param channel_name: The channel to be fetched or created
    :return: The Text Channel object
    """
    # Find the channel if it exists
    for channel in list(guild.text_channels):
        if channel.name == channel_name:
            return channel

    # If no Text Channel with this name exists, create one.
    return await guild.create_text_channel(channel_name, reason="Text Channel was requested but did not exist.")


async def add_pleb_role(member: discord.Member) -> None:
    """
    Adds the pleb Role to a Member.
    :param member: The Member to add the role to
    :return: None
    """
    pleb_role: discord.Role = discord.utils.get(member.guild.roles, name="Plebs")
    if pleb_role is None:
        pleb_role = await member.guild.create_role(name="Plebs", hoist=True, mentionable=True,
                                                   reason="Pleb role for the plebs")
        await log_msg_to_server_owner("The Pleb role did not exist, so the bot has created it.")
    await member.add_roles(pleb_role)


def init_bot_token(token_file: str) -> str:
    """
    Gets the bot's token from a file
    :param token_file: The token file from which to get the bot's token number.
    :return: The bot's token as a string.
    """
    if not os.path.exists(token_file):
        with open(token_file, 'a') as f:  # 'a' opens for appending without truncating
            token = input("The token file does not exist. Please enter the bot's token: ")
            f.write(token)
    else:
        with open(token_file, 'r+') as f:  # 'r+' is reading/writing mode, stream positioned at start of file
            token = f.readline().rstrip('\n')  # readline() usually has a \n at the end of it
            if not token:
                token = input("The token file is empty. Please enter the bot's token: ")
                f.write(token)
    return token


def init_admin_discord_id(id_fname: str) -> int:
    """
    Initializes the owner ID so the bot knows who is in charge.
    :param id_fname: The name of the file that contains the admin's id number
    :return: The ID of the admin user as a string.
    """
    if os.path.isfile("admin_dicord_id.txt"):
        with open("admin_dicord_id.txt", 'r') as f:
            try:
                line = f.readline().strip()
                if line and len(line) == 18:  # Discord IDs are 18 characters.
                    try:
                        return int(line)
                    except ValueError as e:
                        print(e)
                        print("There was an issue with the discord ID found in " + id_fname
                              + ". This file should only contain an 18-digit number and nothing else")
            except EOFError as e:
                print(e)
                print(id_fname + " is empty. This file must contain the user ID of the bot's admin")
    with open("admin_dicord_id.txt", "w") as f:
        id = input("Please enter the Discord ID number for the admin you want this bot to report to: ")
        f.write(id)
        return id


if __name__ == "__main__":

    try:
        ADMIN_DISCORD_ID = int(init_admin_discord_id("admin_discord_id.txt"))
    except TypeError as e:
        print(e)
        print("This error means that there is something wrong with your admin_discord_id.txt file.")
    bot.run(init_bot_token("discord_token.txt"))
