# v1.09

import discord
from discord.ext import commands
from datetime import datetime
import os.path
import logging
import asyncio

# logging
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Initialize Bot settings
description = '''This is Vincent's Discord Bot.'''
bot = commands.Bot(command_prefix='!', description=description)

# Globals
alertsOn = True
messages_waiting_to_send = []
players_seeking_friends = []


@bot.event
async def on_ready():
    users_to_ignore_file = "users_to_ignore.txt"
    global users_to_ignore
    if os.path.exists(users_to_ignore_file):
        with open(users_to_ignore_file, 'r') as f:  # 'r' is reading mode, stream positioned at start of file
            for line in f:
                line = line.strip('\n')
                users_to_ignore.append(line)
    else:
        file = open(users_to_ignore_file, "w+")  # "w+" opens for reading/writing (truncates), creates if doesn't exist
        file.close()


@bot.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await bot.send_message(message.channel, msg)

    await bot.process_commands(message)  # need this line, it prevents the bot from hanging


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
                                                             bot.get_channel('335193104703291393'))  # PUBG Rage-Fest
                    elif str(after.game.name) == "League of Legends":
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel('349099177189310475'))  # Teemo's Treehouse
                    else:
                        await invite_member_to_voice_channel(members_in_same_game,
                                                             bot.get_channel('335188428780208130'))  # Ian's Sex Dungeon

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


@bot.event
async def on_member_ban(member: discord.Member):
    msg = ("Holy cats, " + str(member.name)
           + " just received the full wrath of the ban hammer! Bye bye nerd! Don't come back to "
           + str(member.server) + "!")
    await bot.send_message(await get_default_text_channel(member.server), msg, tts=True)


@bot.event
async def on_member_join(member):
    await bot.send_message(await get_default_text_channel(member.server),
                           "Welcome " + member.name + " to " + member.server.name + "!",
                           tts=True)

    msg = member.name + " has joined " + str(member.server.name) + "!"
    await log_user_activity_to_file(str(member.name), msg)

    pleb_role = discord.utils.get(member.server.roles, name="Plebs")
    if pleb_role is None:
        pleb_role = await bot.create_role(member.server, name="Plebs", id="Plebs", hoist=True)
    await bot.add_roles(member, pleb_role)


@bot.event
async def on_member_remove(member: discord.Member):
    msg = str(member.name) + " has left " + str(member.server) + "."

    await bot.send_message(await get_default_text_channel(member.server), msg)
    await log_user_activity_to_file(str(member.name), msg)


@bot.event
async def on_voice_state_update(before: discord.Member, after: discord.Member):
    if after.voice.voice_channel != None:
        msg = before.name + " joined voice channel: ".ljust(25, ' ') + str(after.voice.voice_channel)
    else:
        msg = before.name + " left voice channel: ".ljust(25, ' ') + str(before.voice.voice_channel)
    await log_user_activity_to_file(after.name, msg)


@bot.event
async def on_channel_create(channel: discord.Channel):
    if not channel.is_private:
        msg = "A new " + str(channel.type) + " channel named \"" + str(channel.name) + "\" has been created."
        await bot.send_message(await get_default_text_channel(channel.server), msg, tts=True)


@bot.event
async def on_channel_delete(channel: discord.Channel):
    await bot.send_message(await get_default_text_channel(channel.server),
                           "The " + str(channel.type) + " channel \"" + str(channel.name) + "\" has been deleted.",
                           tts=True)


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


@bot.command(pass_context=True)
async def time(context):
    """
    The bot sends you a PM with the current time and date.
    :param context:
    :return:
    """
    await bot.send_message(context.message.author, "Current time is: " + datetime.now().strftime(
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
    return msg.ljust(59, ' ') + datetime.now().strftime("%I:%M:%S %p").ljust(13, ' ') + datetime.now().strftime(
        "%m-%d-%y")


async def log_user_activity_to_file(name, msg):
    msg = await add_time_and_date_to_string(msg)
    filepath = "logs/" + name + ".txt"
    with open(filepath, "a+", encoding="utf-8") as file:  # "a+" means append mode, create the file if it doesn't exist.
        file.write(msg + "\n")


async def invite_member_to_voice_channel(members_in_same_game, channel):
    inv = await (bot.create_invite(channel, max_age=3600))
    for member in members_in_same_game:
        if member.voice.voice_channel == channel:
            continue
        elif member.voice.voice_channel is None:  # is NOT in voice channel
            await bot.send_message(member, "You are not the only person playing "
                                   + str(members_in_same_game[0].game)
                                   + ". Here's a voice room you can join your friends in: https://discord.gg/"
                                   + inv.code, tts=True)
            msg = str(member.name) + " was INVITED to " + str(channel.name)
            await log_user_activity_to_file(str(member.name), msg)
        else:
            await bot.move_member(member, channel)
            await bot.send_message(member, "Greetings " + str(member.name)
                                   + "! Due to the fact that you are currently playing " + str(member.game.name)
                                   + ", I have moved you to a more appropriate"
                                   + " voice room so you can join your friends.",
                                   tts=True)
            msg = str(member.name) + " was MOVED to " + str(channel.name)
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
