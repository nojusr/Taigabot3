# Events, sieves, and commands for channel admins.

# Standard Libs
import asyncio

# First Party
from core import db, hook
from util import botu, timeu, user

last_invite: str = ''


@hook.hook('event', ['INVITE'])
async def invite(client, data):
    """Is for listening for invite events, storing it then triggering whois."""
    print(f'INVITE_RECIEVED: from: {data.nickname}, to join: {data.message}')
    global last_invite
    last_invite = f'{data.nickname} {data.message}'
    asyncio.create_task(client.whois(data.nickname))


@hook.hook('event', ['319'])
async def whois(client, data):
    """
    Is for listening to whois to deal with invites.

    If the whois was the result of the invite event, check the user is op,
    owner, or hop in the channel then join.
    """
    message = data.split_message
    global last_invite
    if last_invite:
        invite = last_invite.split()
        nick = invite[0]
        data.nickname = nick
        channel = invite[1]
        channel = channel.lower()
        if message[1] == invite[0]:
            privilages = [
                f'~{channel}', f'&{channel}', f'@{channel}', f'%{channel}']
            if len([priv for priv in privilages if priv in message]) > 0:
                channels = client.bot.config['servers'][data
                                                        .server]['channels']
                if channel not in channels:
                    channels.append(channel)
                
                asyncio.create_task(
                    botu.add_to_conf(client, data, channel, channels,
                                     f'Joining {channel}.',
                                     f'{channel} is already in the config, joining regardless.'))
                asyncio.create_task(client.rawmsg('JOIN', channel))


@hook.hook('init', ['init_channel_dbs'])
async def init_channel_dbs(client):
    conn = client.bot.dbs[client.server_tag]
    db.add_column(conn, 'channels', 'disabled')
    db.add_column(conn, 'channels', 'ban')
    db.add_column(conn, 'channels', 'op')
    db.add_column(conn, 'channels', 'hop')
    db.add_column(conn, 'channels', 'vop')


@hook.hook('event', ['JOIN'])
async def chan_join(client, data):
    """Is called on channel join."""
    conn = client.bot.dbs[data.server]
    if data.nickname in client.users:
        ops = await botu.make_list(
            db.get_cell(conn, 'channels', 'op', 'channel', data.target)[0][0])
        hops = await botu.make_list(
            db.get_cell(conn, 'channels', 'hop', 'channel', data.target)[0][0])
        vops = await botu.make_list(
            db.get_cell(conn, 'channels', 'vop', 'channel', data.target)[0][0])
        bans = await botu.make_list(
            db.get_cell(conn, 'channels', 'ban', 'channel', data.target)[0][0])

        if data.mask in ops:
            asyncio.create_task(
                client.rawmsg('MODE', data.target, '+o', f'{data.nickname}'))
        elif data.mask in hops:
            asyncio.create_task(
                client.rawmsg('MODE', data.target, '+h', f'{data.nickname}'))
        elif data.mask in vops:
            asyncio.create_task(
                client.rawmsg('MODE', data.target, '+v', f'{data.nickname}'))
        if data.mask in bans:
            asyncio.create_task(client.ban(data.target, data.nickname))


@hook.hook('command', ['admins'], admin=True, autohelp=True)
async def c_admins(client, data):
    """
    .admins [list/add/del] [user/mask] -- Lists, adds or deletes users or
    masks from admins.
    """
    message = data.split_message
    conn = client.bot.dbs[data.server]
    admins = await botu.make_list(
        db.get_cell(conn, 'channels', 'admins', 'channel', data.target)[0][0])
    if len(message) > 1:
        masks = await user.parse_masks(client, conn, ' '.join(message[1:]))

    if message[0] == 'del':
        for mask in masks:
            asyncio.create_task(
                botu.del_from_channels(client, data, conn, 'admins', mask,
                                       admins, f'Removing {mask} from admins.',
                                       f'{mask} is not an admin.'))
    elif message[0] == 'add':
        for mask in masks:
            asyncio.create_task(
                botu.add_to_channels(client, data, conn, 'admins', mask,
                                     admins, f'Adding {mask} to admins.',
                                     f'{mask} is already an admin.'))
    elif message[0] == 'list':
        if admins:
            asyncio.create_task(
                client.notice(data.nickname,
                              f'Admins are: {", ".join(admins)}'))
        else:
            asyncio.create_task(
                client.notice(data.nickname, 'There are no admins.'))
        return


@hook.hook('command', ['disable', 'enable'], admin=True, autohelp=True)
async def c_enable_disable(client, data):
    """
    .enable/.disable <list/commands/events/sieves> -- Lists, enables or
    disables commands, events and sieves.
    """
    event_vals = list(client.bot.plugs['event'].values())
    events = [func[0].__name__ for func in (event for event in event_vals)]
    commands = list(client.bot.plugs['command'])
    sieves = list(client.bot.plugs['sieve'])

    nodisable = client.bot.config['servers'][data.server]['no_disable']
    conn = client.bot.dbs[data.server]
    disabled = await botu.make_list(
        db.get_cell(conn, 'channels', 'disabled', 'channel',
                    data.target)[0][0])
    message = data.split_message

    if message[0] == 'list':
        asyncio.create_task(
            botu.cmd_event_sieve_lists(client, data, disabled, nodisable,
                                       sieves, events, commands))
        return

    for plugin in message:
        plugin = plugin.lower().strip()
        if await botu.is_cmd_event_sieve(plugin, data, sieves, events,
                                         commands):
            asyncio.create_task(
                client.notice(data.nickname,
                              f'{plugin} is not a sieve, command or event.'))
        elif data.command == 'enable':
            asyncio.create_task(
                botu.del_from_channels(client, data, conn, 'disabled', plugin,
                                       disabled, f'Enabling {plugin}',
                                       f'{plugin} is not disabled'))
        elif data.command == 'disable':
            if plugin in nodisable:
                asyncio.create_task(
                    client.notice(data.nickname,
                                  f'You cannot disable {plugin}.'))
            else:
                asyncio.create_task(
                    botu.add_to_channels(client, data, conn, 'disabled',
                                         plugin, disabled,
                                         f'Disabling {plugin}',
                                         f'{plugin} is already disabled.'))


@hook.hook(
    'command', ['op', 'hop', 'vop', 'deop', 'dehop', 'devop'],
    admin=True,
    autohelp=True)
async def c_op(client, data):
    """.deop <users>/.op [add/del/list] [users] -- Ops/deops users and can add/del
    to autoop list. Same for hop and vop."""
    message = data.split_message
    conn = client.bot.dbs[data.server]
    if data.command[0:2] == 'de':
        asyncio.create_task(
            botu.usermodes(client, data.target, data.command, message))
        return

    dbmasks = await botu.make_list(
        db.get_cell(conn, 'channels', data.command, 'channel',
                    data.target)[0][0])

    if message[0] == 'list':
        if dbmasks:
            asyncio.create_task(
                client.notice(data.nickname,
                              f'{data.command}s are: {" ".join(dbmasks)}.'))
        else:
            asyncio.create_task(
                client.notice(data.nickname, f'There are no {data.command}s.'))
        return

    message = message[1:]
    masks = await user.parse_masks(client, conn, ' '.join(message))
    for mask in masks:
        if message[0] == 'add':
            asyncio.create_task(
                botu.add_to_channels(
                    client, data, conn, data.command, mask, dbmasks,
                    f'Adding {mask} to {data.command} list.',
                    f'{mask} is already auto-{data.command}ed.'))
        elif message[0] == 'del':
            asyncio.create_task(
                botu.del_from_channels(
                    client, data, conn, data.command, mask, dbmasks,
                    f'Removing {mask} from {data.command} list.',
                    f'{mask} is not auto-{data.command}ed.'))
    asyncio.create_task(
        botu.usermodes(client, data.target, data.command, message))


@hook.hook('command', ['topic'], admin=True, autohelp=True)
async def c_topic(client, data):
    """.topic [|] <message> -- Changes topic, adds if message starts with |."""
    if data.message[0] != '|':
        asyncio.create_task(client.set_topic(data.target, data.message))
    else:
        asyncio.create_task(
            client.set_topic(
                data.target,
                client.channels[data.target]['topic'] + data.message))


@hook.hook('command', ['mute', 'unmute'], admin=True)
async def c_mute(client, data):
    """.mute/.unmute -- Mutes or unmutes the channel."""
    if data.command == 'mute':
        asyncio.create_task(client.rawmsg("MODE", data.target, "+m"))
    else:
        asyncio.create_task(client.rawmsg("MODE", data.target, "-m"))


@hook.hook('command', ['lock', 'unlock'], admin=True)
async def c_lock(client, data):
    """.lock/.unlock -- Locks or unlocks the channel."""
    if data.command == 'lock':
        asyncio.create_task(client.rawmsg("MODE", data.target, "+i"))
    else:
        asyncio.create_task(client.rawmsg("MODE", data.target, "-i"))


@hook.hook('command', ['remove'], admin=True, autohelp=True)
async def c_remove(client, data):
    """.remove <user> -- Makes a user part from the channel."""
    asyncio.create_task(client.rawmsg("REMOVE", data.target, data.message))


@hook.hook('command', ['kick'], admin=True, autohelp=True)
async def c_kick(client, data):
    """.kick <user> [message] -- Kicks a user from the channel."""
    reason = 'bye bye'
    message = data.split_message
    if len(message) > 1:
        reason = message[1:]
        if len(reason) > 1:
            reason = ' '.join(reason)
        else:
            reason = reason[0]
    asyncio.create_task(client.kick(data.target, message[0], reason))


@hook.hook(
    'command', ['ban', 'unban', 'unban', 'kickban'], admin=True, autohelp=True)
async def c_ban_unban(client, data):
    """.ban [add/del/list] [user] [timer]/.kickban [add/del]
       [user] [reason] [timer]/.unban [user] --
       Ban/kickban/unban the user. User can be banned for [timer].
       .unban automatically removes from ban list."""
    message = data.split_message
    conn = client.bot.dbs[data.server]
    bans = await botu.make_list(
        db.get_cell(conn, 'channels', 'ban', 'channel', data.target)[0][0])
    if data.command == 'unban':
        asyncio.create_task(client.unban(data.target, message[0]))
        asyncio.create_task(
            botu.del_from_channels(client, data, conn, 'ban', message[0], bans,
                                   f'Removing {message[0]} from bans.',
                                   f'{message[0]} is not in the ban list.'))
        return

    try:
        timer = int(message[-1])
        message = message[:-1]
    except ValueError:
        timer = 0

    if message[0] == 'del':
        message = message[1:]
        asyncio.create_task(
            botu.del_from_channels(client, data, conn, 'ban', message[0], bans,
                                   f'Removing {message[0]} from bans.',
                                   f'{message[0]} is not in the ban list.'))
    elif message[0] == 'add':
        message = message[1:]
        asyncio.create_task(
            botu.add_to_channels(client, data, conn, 'ban', message[0], bans,
                                 f'Adding {message[0]} to the bans.',
                                 f'{message[0]} is already in the ban list.'))
    elif message[0] == 'list':
        asyncio.create_task(
            client.notice(data.nickname, 'bans are: ' + ', '.join(bans)))
        return

    if data.command == 'ban':
        asyncio.create_task(client.ban(data.target, message[0]))
    if data.command == 'kickban':
        asyncio.create_task(
            client.kickban(
                data.target,
                message[0],
                reason=' '.join(message).replace(message[0], 'Git Rekt')))

    if timer:
        asyncio.create_task(
            timeu.asyncsched(timer, client.unban, (data.target, message[0])))
