# Events, sieves, and commands for flood control.

# Standard Libs
import asyncio
import sched
import threading
import time
from typing import Dict, List

# First Party
from core import db, hook
from util import user

msg_flooding: Dict[str, Dict[str, List[int]]] = {}
cmd_flooding: Dict[str, Dict[str, List[int]]] = {}


async def _take_action(client, data, flood_rules, flood_type):
    """Is for warning, kicking, or banning flooding users."""
    message = (f'You are flooding, the flood rules are {flood_rules[0]} '
               f'{flood_type} per {flood_rules[1]} seconds.')
    if flood_rules[-1] == 'warn':
        asyncio.create_task(client.notice(data.nickname, message))
    elif flood_rules[-1] == 'kick':
        asyncio.create_task(
            client.kick(data.target, data.nickname, reason=message))
    elif flood_rules[-1] == 'ban':
        asyncio.create_task(
            client.kickban(data.target, data.nickname, reason=message))
        s = sched.scheduler(time.perf_counter, time.sleep)
        s.enter(60, 1, asyncio.create_task,
                (client.unban(data.target, data.nickname)))
        thread = threading.Thread(target=s.run)
        thread.daemon = True
        thread.start()


async def _detect_flood(client, data, flood_rules, flood_type):
    """Is for detecting flooding users then taking action."""
    global msg_flooding
    global cmd_flooding
    if flood_type == 'msg':
        flood_dict = msg_flooding
        flood_type = 'messages'
    elif flood_type == 'cmd':
        flood_dict = cmd_flooding
        flood_type = 'commands'

    if data.target not in flood_dict:
        flood_dict[data.target] = {}
    if data.nickname not in flood_dict[data.target]:
        flood_dict[data.target][data.nickname] = []
    flooder = flood_dict[data.target][data.nickname]
    now = time.perf_counter()
    flooder.append(now)
    flooder = [t for t in list(flooder) if now - t < int(flood_rules[1])]
    if len(flooder) > int(flood_rules[0]):
        await _take_action(client, data, flood_rules, flood_type)


@hook.hook('sieve', ['05-flood-input'])
async def flood_input_sieve(client, data):
    #Is for handling users who are flooding in the channel.
    conn = client.bot.dbs[data.server]
    isadmin = await user.is_admin(client, conn, data.nickname, data.mask)

    if await user.is_gadmin(client, data.server, data.mask):
        return data
    if isadmin or not data.target:
        return data
    if data.target[0] != '#':
        return data

    db.add_column(conn, 'channels', 'msgflood')
    db.add_column(conn, 'channels', 'cmdflood')
    prefix = db.get_cell(conn, 'channels', 'commandprefix', 'channel',
                         data.target)[0][0]
    msgflood = db.get_cell(conn, 'channels', 'msgflood', 'channel',
                           data.target)[0][0]
    cmdflood = db.get_cell(conn, 'channels', 'cmdflood', 'channel',
                           data.target)[0][0]
    if msgflood:
        msgflood = msgflood.split()
        asyncio.create_task(_detect_flood(client, data, msgflood, 'msg'))
    if cmdflood and data.command and prefix:
        if data.command[0] == prefix:
            if cmdflood:
                cmdflood = cmdflood.split()
                asyncio.create_task(
                    _detect_flood(client, data, cmdflood, 'cmd'))
    return data


async def _is_int(inp):
    """Is for testing if input can be parsed to int."""
    try:
        int(inp)
        return True
    except ValueError:
        return False


async def _secs_or_help(client, data, message):
    """Is for displaying help for various conditions, or returning seconds."""
    if len(message) == 1:
        doc = ' '.join(c_flood.__doc__.split())
        asyncio.create_task(client.notice(data.nickname, f'{doc}'))
        return None
    if len(message) >= 2 and message[1] != 'disable':
        commands = ['list', 'cmd', 'msg']
        tooshort = (len(message) < 4 and message[0] != 'list')
        try:
            notvalid = (message[3] not in ['kick', 'ban', 'warn'])
            notint = (not _is_int(message[1]) or not _is_int(message[2]))
            secs = message[2]
        except IndexError:
            secs = notint = False
        if message[0] not in commands or tooshort or notvalid or notint:
            doc = ' '.join(c_flood.__doc__.split())
            asyncio.create_task(client.notice(data.nickname, f'{doc}'))
            return None
        if not notint:
            if int(message[1]) < 1 or int(message[2]) < 1:
                doc = ' '.join(c_flood.__doc__.split())
                asyncio.create_task(client.notice(data.nickname, f'{doc}'))
                return None

    else:
        secs = 1
    return secs


@hook.hook('command', ['flood'], autohelp=True, admin=True)
async def c_flood(client, data):
    """
    .flood [list/cmd/msg] [messages/disable] [second] [kick/ban/warn] --
     List, disable, or change the max messages per second or commands per
     second. The bot can kick, ban(which also kicks), or warn flooding users.
    """
    conn = client.bot.dbs[data.server]
    msgflood = db.get_cell(conn, 'channels', 'msgflood', 'channel',
                           data.target)[0][0]
    cmdflood = db.get_cell(conn, 'channels', 'cmdflood', 'channel',
                           data.target)[0][0]
    if ' ' in data.message:
        message = data.message.split(' ')
    else:
        message = [data.message]

    if message[0] == 'list':
        if msgflood not in (None, ''):
            asyncio.create_task(
                client.notice(data.nickname, f'Message flood: {msgflood}.'))
        else:
            asyncio.create_task(
                client.notice(data.nickname, f'No message flood set.'))
        if cmdflood not in (None, ''):
            asyncio.create_task(
                client.notice(data.nickname, f'Command flood: {cmdflood}.'))
        else:
            asyncio.create_task(
                client.notice(data.nickname, f'No command flood set.'))
        return

    secs = await _secs_or_help(client, data, message)
    if not secs:
        return

    if message[0] == 'msg':
        if message[1] == 'disable':
            asyncio.create_task(
                client.notice(data.nickname, 'Disabling message flood.'))
            db.set_cell(conn, 'channels', 'msgflood', '', 'channel',
                        data.target)
        else:
            asyncio.create_task(
                client.notice(
                    data.nickname,
                    f'Changing message flood to {message[1]} {secs}'
                    f'{message[3]}.'))
            db.set_cell(conn, 'channels', 'msgflood',
                        f'{message[1]} {secs} {message[3]}', 'channel',
                        data.target)
    if message[0] == 'cmd':
        if message[1] == 'disable':
            asyncio.create_task(
                client.notice(data.nickname, 'Disabling command flood.'))
            db.set_cell(conn, 'channels', 'cmdflood', '', 'channel',
                        data.target)
        else:
            asyncio.create_task(
                client.notice(
                    data.nickname,
                    f'Changing command flood to {message[1]} {secs}'
                    f'{message[3]}.'))
            db.set_cell(conn, 'channels', 'cmdflood',
                        f'{message[1]} {secs} {message[3]}', 'channel',
                        data.target)
