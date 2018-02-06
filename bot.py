#v1.06

import discord
from discord.ext import commands
from datetime import datetime
import os.path
import logging
from threading import Timer
from bisect import bisect

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
users_to_ignore = []
players_seeking_friends = []

@bot.event
async def on_ready():
    msg = await pad_message("AlatarBot is now online!") + "\n"
    await log_msg_to_Discord_pm(msg, False)

    users_to_ignore_file = "users_to_ignore.txt"
    global users_to_ignore
    if os.path.exists(users_to_ignore_file):
        with open(users_to_ignore_file, 'r') as f:  # 'r' is reading mode, stream positioned at start of file
            for line in f:
                line = line.strip('\n')
                users_to_ignore.append(line)
        f.close()
    else:
        with open(users_to_ignore_file, 'a') as f:  # 'a' opens for writing without truncating, creates file if needed
            f.close()


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
async def on_member_update(before: discord.Member, after: discord.Member):
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

                players_seeking_friends.append(after)   # <----------------- can I remove this and do it in the loop?
                for member in players_seeking_friends:
                    if member != after and str(member.game) == str(after.game) and member.server == after.server:
                        members_in_same_game.append(member)

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

                t = Timer(300.0, pop_member_from_voice_room_seek, args=(after,))
                t.start()

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
    # await log_msg_to_Discord_pm(msg) # FOR TESTING ONLY, send alert regardless of author


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

    msg = str(member.name) + " has joined " + str(member.server.name) + "!"
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(str(member.name), msg)

    pleb_role = discord.utils.get(member.server.roles, name="Plebs")
    if pleb_role is None:
        pleb_role = await bot.create_role(member.server, name="Plebs", id="Plebs", hoist=True)
    await bot.add_roles(member, pleb_role)


@bot.event
async def on_member_remove(member: discord.Member):

    msg = str(member.name) + " has left " + str(member.server) + "."

    await bot.send_message(await get_default_text_channel(member.server), msg)
    await log_msg_to_Discord_pm(msg)
    await log_user_activity_to_file(str(member.name), msg)


@bot.event
async def on_voice_state_update(before: discord.Member, after: discord.Member):
    if str(after.voice.voice_channel) != "None":
        msg = before.name + " joined voice channel: ".ljust(25, ' ') + str(after.voice.voice_channel)
    else:
        msg = before.name + " left voice channel: ".ljust(25, ' ') + str(before.voice.voice_channel)
    await log_msg_to_Discord_pm(msg)


@bot.event
async def on_channel_create(channel: discord.Channel):
    if not channel.is_private:
        msg = "A new " + str(channel.type) + " channel named \"" + str(channel.name) + "\" has been created."
        await bot.send_message(await get_default_text_channel(channel.server), msg, tts=True)
        await log_msg_to_Discord_pm(msg)


@bot.event
async def on_channel_delete(channel: discord.Channel):
    await bot.send_message(await get_default_text_channel(channel.server),
                           "The " + str(channel.type) + " channel \"" + str(channel.name) + "\" has been deleted.",
                           tts=True)


@bot.command(pass_context=True, hidden=True)
async def on(context):
    """Admin command"""
    if context.message.author.id != "251934924196675595":
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_Discord_pm("Notifications are ON")

    # Catch up on notifications waiting to be sent.
    global messages_waiting_to_send
    if messages_waiting_to_send:
        await log_msg_to_Discord_pm(await pad_message("Suppressed Notifications", False), False)
        while messages_waiting_to_send:
            msg = messages_waiting_to_send.pop(0)   # pop from FRONT of list
            await log_msg_to_Discord_pm(msg, False)
        await  log_msg_to_Discord_pm(await pad_message("End", False), False)


@bot.command(pass_context=True, hidden=True)
async def off(context):
    """Admin command"""
    if context.message.author.id != "251934924196675595":
        return

    global alertsOn
    alertsOn = True
    await log_msg_to_Discord_pm("Notifications are OFF")
    alertsOn = False

@bot.command(pass_context=True, hidden=True)
async def ignore(context, user_to_ignore):
    """Admin command"""
    if context.message.author.id != "251934924196675595":
        return

    user_to_ignore = user_to_ignore.strip('\n')

    global users_to_ignore
    if user_to_ignore in users_to_ignore:
        await log_msg_to_Discord_pm(user_to_ignore + " is already being ignored.")
    else:
        users_to_ignore.insert(bisect([i.lower() for i in users_to_ignore], user_to_ignore.lower()), user_to_ignore)

        with open("users_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
            for user in users_to_ignore:
                f.write(user + '\n')
        f.close()
        await log_msg_to_Discord_pm(user_to_ignore + " has been ignored.")
        await print_ignored(context)


@bot.command(pass_context=True, hidden=True)
async def unignore(context, user_to_unignore):
    """Admin command"""
    if context.message.author.id != "251934924196675595":
        return

    global users_to_ignore
    if user_to_unignore not in users_to_ignore:
        await log_msg_to_Discord_pm(user_to_unignore + " is not currently being ignored.")
        return
    else:
        users_to_ignore.remove(user_to_unignore)
        with open("users_to_ignore.txt", 'w') as f:  # 'w' opens for writing, creates if doesn't exist
            for user in users_to_ignore:
                f.write(user + '\n')
        f.close()
    await print_ignored(context)


@bot.command(pass_context=True, hidden=True)
async def unignoreall(context):
    """Admin command"""
    if context.message.author.id != "251934924196675595":
        return

    global users_to_ignore
    users_to_ignore.clear()
    users_to_ignore_file = "users_to_ignore.txt"
    with open(users_to_ignore_file, 'w') as f:  # 'w' opens for writing, creates if doesn't exist
        f.close()
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
    if context.message.author.id != "251934924196675595":
        return
    await print_ignored(context)

async def print_ignored(context):
    """Admin method"""
    if context.message.author.id != "251934924196675595":
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
async def printseeking(context):
    """Admin command"""
    if context.message.author.id != "251934924196675595":
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
    return (msg.ljust(59, ' ') + datetime.now().strftime("%I:%M:%S %p").ljust(13, ' ')
            + datetime.now().strftime("%m-%d-%y"))


async def log_msg_to_Discord_pm(msg, add_time_and_date=True):
    msg = await add_time_and_date_to_string(msg) if (add_time_and_date is True) else msg
    global alertsOn
    if alertsOn:
        await bot.send_message(await bot.get_user_info('251934924196675595'), msg, tts=True)
    else:
        global messages_waiting_to_send
        messages_waiting_to_send.append(msg)

async def log_user_activity_to_file(name, msg):
    msg = await add_time_and_date_to_string(msg)
    filepath = "logs/" + name + ".txt"
    file = open(filepath, "a+")   # "a+" parameter means append mode, the + means create the file if it doesn't exist.
    file.write(msg + "\n")
    file.close()


async def invite_member_to_voice_channel(members_in_same_game, channel):
    inv = await (bot.create_invite(channel, max_age=3600))  # general channel
    for member in members_in_same_game:
        if member.voice.voice_channel == channel:
            continue
        elif member.voice.voice_channel is None:  # is NOT in voice channel
            print("User is currently in " + str(channel.name))
            await bot.send_message(member, "You are not the only person playing "
                                   + str(members_in_same_game[0].game)
                                   + ". Here's a voice room you can join your friends in: https://discord.gg/"
                                   + inv.code, tts=True)
            await log_msg_to_Discord_pm(str(member.name) + " was INVITED to " + str(channel.name))
        else:
            await bot.move_member(member, channel)
            await bot.send_message(member, "Greetings " + str(member.name)
                                   + "! Due to the fact that you are currently playing " + str(member.game.name)
                                   + ", I have moved you to a more appropriate"
                                   + " voice room so you can join your friends.",
                                   tts=True)
            await log_msg_to_Discord_pm(str(member.name) + " was MOVED to " + str(channel.name))


def initialize_bot_token():
    token_file = "token.txt"
    if not os.path.exists(token_file):
        with open(token_file, 'a') as f:    # 'a' opens for appending without truncating
            token = input("The token file does not exist. Please enter the bot's token: ")
            f.write(token)
            f.close()
    else:
        with open(token_file, 'r+') as f:  # 'r+' is reading/writing mode, stream positioned at start of file
            token = f.readline().rstrip('\n')  # readline() usually has a \n at the end of it
            if not token:
                token = input("The token file is empty. Please enter the bot's token: ")
                f.write(token)
            f.close()
    return token


async def get_default_text_channel(server):
    default_text_channel = None
    idx = 0
    default_text_channel = None
    for channel in list(server.channels):
        if channel.type == discord.ChannelType.text:  # 0 type is text, 1 type is voice
            default_text_channel = channel
            break
    if default_text_channel == None:
        default_text_channel = await bot.create_channel(server, "general", type=discord.ChannelType.text)

    return default_text_channel

def pop_member_from_voice_room_seek(member):
    global players_seeking_friends
    players_seeking_friends.remove(member)


bot.run(initialize_bot_token())
