# TODO: Eliminate all send_message

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
messages_waiting_to_send = []
users_to_ignore = []
players_seeking_friends = []
my_discord_id = 251934924196675595
USERS_TO_IGNORE_FILE = "users_to_ignore.txt"


@bot.event
async def on_ready():
    msg = await pad_message("AlatarBot is now online!") + "\n"
    await log_msg_to_Discord_pm(msg, False)

    global users_to_ignore
    if os.path.exists(USERS_TO_IGNORE_FILE):
        with open(USERS_TO_IGNORE_FILE, 'r') as f:  # 'r' is reading mode, stream positioned at start of file
            for line in f:
                users_to_ignore.append(line.strip('\n'))
    else:
        file = open(USERS_TO_IGNORE_FILE, "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
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
async def on_member_update(before, after):
    if str(before.status) == "offline" and str(after.status) == "offline":
        msg = str(before.name) + " is in OFFLINE MODE."
    elif before.status != after.status:
        msg = (((str(before.name) + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44, ' ')
               + "(was " + str(before.status).upper() + ")")
    elif before.game != after.game:
        if after.game is None:
            msg = str(before.name + " STOPPED playing: ").ljust(35, ' ') + before.game.name
        else:
            msg = str(before.name + " STARTED playing: ").ljust(35, ' ') + after.game.name

            global players_seeking_friends
            if after not in players_seeking_friends:
                # Voice Room controls
                members_in_same_game = [after]  # initialize list with one member in it

                players_seeking_friends.append(after)  # <----------------- can I remove this and do it in the loop?
                for member in players_seeking_friends:
                    if member != after and member.game == after.game and member.server == after.server:
                        members_in_same_game.append(member)

                # If there are more than 1 players in a game, activate voice room controls
                if len(members_in_same_game) > 1:
                    if str(after.game.name) == "PLAYERUNKNOWN'S BATTLEGROUNDS" or str(after.game.name) == "PUBG":
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel(335193104703291393))  # PUBG Rage-Fest
                    elif str(after.game.name) == "League of Legends":
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel(349099177189310475))  # Teemo's Treehouse
                    else:
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel(335188428780208130))  # Ian's Sex Dungeon

                event_loop = asyncio.get_event_loop()
                event_loop.call_later(300.0, pop_member_from_voice_room_seek, after)

    elif before.nick != after.nick:
        if after.nick is None:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + str(after.name)
        elif before.nick is None:
            msg = (str(before.name) + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)
        else:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)
    elif str(before.name) != str(after.name):
        msg = str(before.name + "\'s new name is: ").ljust(35, ' ') + str(after.name)
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
    elif before.avatar != after.avatar:
        msg = str(before.name) + " now has a new avatar!"
    else:
        msg = "ERROR!!! " + str(after.name) + " has caused an error in on_member_update()."

    await log_user_activity_to_file(str(before.name), msg)

    global users_to_ignore
    if str(after.name) not in users_to_ignore:
        await log_msg_to_Discord_pm(msg)


@bot.event
async def on_member_ban(member: discord.Member):
    msg = ("Holy cats, " + str(member.name)
           + " just received the full wrath of the ban hammer! Bye bye nerd! Don't come back to "
           + str(member.guild) + "!")
    await bot.send_message(await get_default_text_channel(member.guild), msg, tts=True)


@bot.event
async def on_member_join(member: discord.Member):
    await bot.send_message(await get_default_text_channel(member.server),
                           "Welcome " + member.name + " to " + member.guild.name + "!",
                           tts=True)

    msg = member.name + " has joined " + str(member.server.name) + "!"
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(str(member.name), msg)

    pleb_role = discord.utils.get(member.server.roles, name="Plebs")
    if pleb_role is None:
        pleb_role = await bot.create_role(member.guild, name="Plebs", id="Plebs", hoist=True)
    await bot.add_roles(member, pleb_role)


@bot.event
async def on_member_remove(member: discord.Member):
    msg = str(member.name) + " has left " + str(member.guild) + "."

    await bot.send_message(await get_default_text_channel(member.guild), msg)
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(str(member.name), msg)


@bot.event
async def on_voice_state_update(before: discord.Member, after: discord.Member):
    if after.voice.voice_channel != None:
        msg = before.name + " joined voice channel: ".ljust(25, ' ') + str(after.voice.voice_channel)
    else:
        msg = before.name + " left voice channel: ".ljust(25, ' ') + str(before.voice.voice_channel)
    await log_msg_to_Discord_pm(msg)


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    if not channel.is_private:
        msg = "A new " + str(channel.type) + " channel named \"" + str(channel.name) + "\" has been created."
        await bot.send_message(await get_default_text_channel(channel.server), msg, tts=True)
        await log_msg_to_Discord_pm(msg)


@bot.event
async def on_channel_delete(channel):
    await bot.send_message(await get_default_text_channel(channel.server),
                           "The " + str(channel.type) + " channel \"" + str(channel.name) + "\" has been deleted.",
                           tts=True)


@bot.command(pass_context=True, hidden=True)
async def on(context):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
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
        await  log_msg_to_Discord_pm(await pad_message("End", False), False)


@bot.command(pass_context=True, hidden=True)
async def off(context):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_Discord_pm("Notifications are OFF")
    alertsOn = False


@bot.command(pass_context=True, hidden=True)
async def ignore(context, user_to_ignore):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    global users_to_ignore
    if user_to_ignore in users_to_ignore:
        await log_msg_to_Discord_pm(user_to_ignore + " is already being ignored.")

    # If user is not in any of the bot's servers, ignore the ignore command
    user_found = False
    for server in bot.servers:
        for member in server.members:
            if member.name == user_to_ignore:
                user_found = True
                break
        if user_found:
            break

    if not user_found:
        await log_msg_to_Discord_pm(user_to_ignore + " could not be found.")
        return

    users_to_ignore.insert(bisect([i.lower() for i in users_to_ignore], user_to_ignore.lower()), user_to_ignore)

    with open("users_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        for user in users_to_ignore:
            f.write(user + '\n')
    # f.close() # Do not need this line because file was opened using "with"
    await log_msg_to_Discord_pm(user_to_ignore + " has been ignored.")
    await print_ignored(context)


@bot.command(pass_context=True, hidden=True)
async def unignore(context, user_to_unignore):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    # If they are not being ignored, disregard the command
    global users_to_ignore
    if user_to_unignore not in users_to_ignore:
        await log_msg_to_Discord_pm(user_to_unignore + " is not currently being ignored.")
        return

    users_to_ignore.remove(user_to_unignore)
    with open("users_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        for user in users_to_ignore:
            f.write(user + '\n')
    # f.close()  # Do not need this line because file was opened using "with"
    await print_ignored(context)


@bot.command(pass_context=True, hidden=True)
async def unignoreall(context):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    global users_to_ignore
    users_to_ignore.clear()
    users_to_ignore_file = "users_to_ignore.txt"

    # Write a new file
    file = open(users_to_ignore_file, "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
    file.close()
    await log_msg_to_Discord_pm("Ignore list has been cleared.")


@bot.command(pass_context=True)
async def invite(context, member_to_invite: discord.Member):
    """Invites another user to join your current voice room."""
    if context.message.author.voice.voice_channel is None:
        return
    author = context.message.author
    voice_room = author.voice.voice_channel

    inv = await (bot.create_invite(voice_room, max_age=3600))

    msg = author.name + " is inviting you to a voice chat. https://discord.gg/"
    await bot.send_message(member_to_invite, msg + inv.code, tts=True)

    msg = "You have invited " + str(member_to_invite.name) + " to the voice room " + str(voice_room.name)
    await bot.send_message(author, msg, tts=False)

    msg = str(author.name) + " has invited " + str(member_to_invite.name) + " to the voice room " + str(voice_room.name)
    await log_msg_to_Discord_pm(msg)


@bot.command(pass_context=True, hidden=True)
async def printignored(context):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    await print_ignored(context)


async def print_ignored(context):
    """Admin method"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    global users_to_ignore

    if not users_to_ignore:
        await log_msg_to_Discord_pm("There are currently no members being ignored.", False)
    else:
        msg = await pad_message("Ignored Users", add_time_and_date=False) + "\n"
        for user in users_to_ignore:
            msg = msg + user + '\n'
        msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
        await log_msg_to_Discord_pm(msg, False)


@bot.command(pass_context=True, hidden=True)
async def printnotignored(context):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    await print_not_ignored(context)


async def print_not_ignored(context):
    """Admin method"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    global users_to_ignore

    msg = await pad_message("Users Not Ignored", add_time_and_date=False) + "\n"
    users_not_ignored = list()
    for server in bot.servers:
        for member in server.members:
            if member.name not in users_to_ignore and member.name not in users_not_ignored:
                users_not_ignored.append(member.name)
    for user in users_not_ignored:
        msg = msg + user + '\n'
    msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
    await log_msg_to_Discord_pm(msg, False)


@bot.command(pass_context=True, hidden=True)
async def printseeking(context):
    """Admin command"""
    global my_discord_id
    if context.message.author.id != my_discord_id:
        return

    global players_seeking_friends
    if not players_seeking_friends:
        await log_msg_to_Discord_pm("No members are currently seeking friends.")
    else:
        msg = await pad_message("Players Seeking Friends", add_time_and_date=False) + "\n"
        for player in players_seeking_friends:
            msg = msg + player.name + "\n"
        msg = msg + await pad_message("End", add_time_and_date=False) + "\n"
        await log_msg_to_Discord_pm(msg, False)


@bot.command(pass_context=True)
async def time(context):
    """
    The bot sends you a PM with the current time and date.
    :param context:
    :return:
    """
    await context.send("Current time is: " + datetime.now().strftime(
        "%I:%M:%S %p") + " on " + datetime.now().strftime("%A, %B %d, %Y"))


async def pad_message(msg, add_time_and_date=True, dash_count=80):
    if add_time_and_date:
        msg = "\n" + (await add_time_and_date_to_string(msg)) + "\n"
    else:
        msg = "\n" + msg + "\n"
    # dash_count = len(msg) - 2
    for x in range(dash_count):
        msg = "-".join(["", msg, ""])
    return msg


async def add_time_and_date_to_string(msg):
    return datetime.now().strftime("%m-%d-%y") + "\t" + datetime.now().strftime("%I:%M:%S%p") + "\t" + msg


@bot.command()
async def log_msg_to_Discord_pm(msg, add_time_and_date=True):
    """
    Sends a DM to the bot's owner.
    :param msg:
    :param add_time_and_date:
    :return:
    """
    msg = await add_time_and_date_to_string(msg) if (add_time_and_date is True) else msg
    global alertsOn
    if alertsOn:
        global my_discord_id
        usr = await bot.fetch_user(my_discord_id)
        await usr.send(msg)
    else:
        global messages_waiting_to_send
        messages_waiting_to_send.append(msg)


async def log_user_activity_to_file(name, msg):
    msg = await add_time_and_date_to_string(msg)
    filepath = "logs/" + name + ".txt"
    with open(filepath, "a+", encoding="utf-8") as file:  # "a+" means append mode, create the file if it doesn't exist.
        file.write(msg + "\n")


async def invite_member_to_voice_channel(members_in_same_game: List[discord.User], voice_channel: discord.VoiceChannel):
    invite = await (bot.create_invite(voice_channel, max_age=3600))
    for member in members_in_same_game:
        if member.voice.voice_channel == voice_channel:
            continue
        elif member.voice.voice_channel is None:  # is NOT in voice voice_channel
            await member.send("You are not the only person playing "
                              + str(members_in_same_game[0].game)
                              + ". Here's a voice room you can join your friends in: https://discord.gg/"
                              + invite.code, tts=True)
            msg = str(member.name) + " was INVITED to " + str(voice_channel.name)
            await log_msg_to_Discord_pm(msg)
            await log_user_activity_to_file(str(member.name), msg)
        else:
            await bot.move_member(member, voice_channel)
            await member.send("Greetings " + str(member.name)
                              + "! Due to the fact that you are currently playing " + str(member.game.name)
                              + ", I have moved you to a more appropriate"
                              + " voice room so you can join your friends.",
                              tts=True)
            msg = str(member.name) + " was MOVED to " + str(voice_channel.name)
            await log_msg_to_Discord_pm(msg)
            await log_user_activity_to_file(str(member.name), msg)


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


async def get_default_text_channel(server):
    default_text_channel = None
    idx = 0
    default_text_channel = None
    for channel in list(server.channels):
        if channel.type == discord.ChannelType.text and channel.name == "general":  # 0 type is text, 1 type is voice
            default_text_channel = channel
            break
    if default_text_channel == None:
        default_text_channel = await bot.create_channel(server, "general", type=discord.ChannelType.text)

    return default_text_channel


def pop_member_from_voice_room_seek(member):
    global players_seeking_friends
    players_seeking_friends.remove(member)


if __name__ == "__main__":
    bot.run(initialize_bot_token())
