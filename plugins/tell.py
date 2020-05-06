# tells
# author: nojusr
#
# usage:
#  .tell [user] [message]     -- send a message to an offline user.
#                                message will be shown to them once
#                                said user connects to the server.
#
#  .showtells                 -- shows all seen messages sent to you
#                                within the last 24 hours and all unseen
#                                messages sent to you within the last week
#
# note: read messages are deleted within 24 hours,
#       unread messages are deleted within a week
#
# note: once a message is read, it is still displayed for 24 hours

from typing import List
import time
import dateutil.relativedelta
from datetime import datetime
import asyncio


# import core functions
from core import db
from core import hook

# db table definition
tell_columns: List[str] = ['nick', 'add_nick', 'msg',
                           'time', 'seen', 'seen_time']

# config values
unseen_tell_timeout = 31556926  # equals to a year
seen_tell_timeout = 86400  # equals to a day
tell_limit = 10 # amount of tells shown


def _set_tell_seen(conn, tell):
    """ Is used to set a tell's status to seen """
    if tell[4] == '1':
        return

    cur = conn.cursor()
    cur.execute("UPDATE tells SET seen='1', seen_time=? WHERE msg=? AND time=?", (str(int(time.time())), tell[2], tell[3]))
    del cur
    conn.commit()
    db.ccache()


def _delete_tell(conn, tell):
    """ Is used to delete tells """
    cur = conn.cursor()
    cur.execute('DELETE FROM tells WHERE msg=? AND time=? AND seen_time=?', (tell[2], tell[3], tell[5]))
    conn.commit()
    db.ccache()


def _get_time_since_tell_send(tell):
    """
       Is used to get a human readable representation of the time since
       the message was sent.
    """
    tell_time_sent = int(tell[3])

    current_time = int(time.time())

    dt1 = datetime.fromtimestamp(tell_time_sent)
    dt2 = datetime.fromtimestamp(current_time)
    rd = dateutil.relativedelta.relativedelta(dt2, dt1)

    out = ''

    if rd.days == 1:
        out += f'{rd.days} day, '
    elif rd.days != 0:
        out += f'{rd.days} days, '

    if rd.hours == 1:
        out += f'{rd.hours} hour, '
    elif rd.hours != 0:
        out += f'{rd.hours} hours, '

    if rd.minutes == 1:
        out += f'{rd.minutes} minute and '
    elif rd.minutes != 0:
        out += f'{rd.minutes} minutes and '

    if rd.seconds == 1:
        out += f'{rd.seconds} second ago'
    elif rd.seconds != 0:
        out += f'{rd.seconds} seconds ago'
    elif current_time - tell_time_sent == 0:
        out = 'just now'

    return out


def _send_tell_notice(client, recipient, tell):
    relative_time = _get_time_since_tell_send(tell)
    asyncio.create_task(client.notice(recipient,
                        f'{tell[1]} sent you a message {relative_time}: {tell[2]}'))


def _get_tell_time(elem):
    """ Tiny helper function used to sort tells """
    return int(elem[3])

def _show_user_recent_tells(client, conn, recipient, show_only_unseen):
    tells = db.get_row(conn, 'tells', 'nick', recipient)
    # small sanity check

    if len(tells) <= 0:
        if show_only_unseen is False:
            asyncio.create_task(client.notice(recipient, 'You have no pending tells.'))
        return

    # sort tells
    tells.sort(key=_get_tell_time, reverse=True)

    # limit tells
    if len(tells) > tell_limit:
        tells = tells[0:tell_limit]

    if show_only_unseen is True:

        unseen_tell_found = 0

        for tell in tells:
            if str(tell[4]) == '0':
                if unseen_tell_found == 0:
                    asyncio.create_task(client.notice(recipient, 'You have new tells!'))
                    unseen_tell_found = 1

                _set_tell_seen(conn, tell)
                _send_tell_notice(client, recipient, tell)

    else:
        asyncio.create_task(client.notice(recipient, 'Here are your recent tells:'))
        for tell in tells:
            _set_tell_seen(conn, tell)
            _send_tell_notice(client, recipient, tell)


@hook.hook('init', ['tellinit'])
async def inittell(client):
    """Is used to initialize the tell database"""
    conn = client.bot.dbs[client.server_tag]
    print (f'Initializing tell table in /persist/db/{client.server_tag}.db...')
    db.init_table(conn, 'tells', tell_columns)
    db.ccache()
    print ('Tell initialization complete.')


@hook.hook('init', ['tell_garbage_collector'])
async def tellgc(client):
    """ Looks for and deletes old tells every 10 miuntes """
    conn = client.bot.dbs[client.server_tag]
    print ('Starting tell garbage collector...')
    while client.connected is True:
        print('Deleting old tells...')
        current_time = int(time.time())

        all_tells = db.get_table(conn, 'tells')
        for tell in all_tells:
            print (f'    TELL_DEBUG: seen: {tell[4]}, diff of send time {current_time - int(tell[3])}, diff of seen time {current_time - int(tell[5])}')
            if str(tell[4]) == '1' and (current_time - int(tell[5])) > seen_tell_timeout:
                print('    TELL_DEBUG: deleting tell due to seen timeout')
                _delete_tell(conn, tell)
            if str(tell[4]) == '0' and (current_time - int(tell[3])) > unseen_tell_timeout:
                print('    TELL_DEBUG: deleting tell due to unseen timeout')
                _delete_tell(conn, tell)
        print('Done.')
        await asyncio.sleep(600)


@hook.hook('command', ['tell', 'ask'])
async def tell(client, data):
    """.tell - send a message to an user which is currently inactive"""
    conn = client.bot.dbs[data.server]
    split = data.split_message

    tables = db.get_table_names(conn)
    if 'tells' not in tables:
        asyncio.create_task(client.message(data.target, 'Tell table uninitialized, ask your nearest bot admin to restart the bot.'))

    if len(split) > 1:
        recipient = split[0]
        recipient = recipient.lower()
        message = ' '.join(split[1:])
    else:
        return
        
    telldata = (recipient, data.nickname, message, int(time.time()), '0', '0')
    db.set_row(conn, 'tells', telldata)
    db.ccache()

    asyncio.create_task(client.notice(data.nickname, 'Your message will be sent.'))


@hook.hook('command', ['cleartells', 'ct'])
async def cleartells(client, data):
    conn = client.bot.dbs[data.server]
    tells = db.get_row(conn, 'tells', 'nick', data.nickname.lower())
    
    for tell in tells:
        print(f'TELL_DEBUG: manual tell delete {tell[0]} {tell[2]} {tell[3]} {tell[5]}')
        _delete_tell(conn, tell)
    
    asyncio.create_task(client.notice(data.nickname, 'Your tells have been deleted.'))


@hook.hook('command', ['showtells', 'st'])
async def showtells(client, data):
    conn = client.bot.dbs[data.server]
    nick = data.nickname
    nick = nick.lower()
    _show_user_recent_tells(client, conn, nick, False)


@hook.hook('event', ['JOIN', 'PRIVMSG'])
async def onconnectshowtells(client, data):
    conn = client.bot.dbs[data.server]
    nick = data.nickname
    nick = nick.lower()
    _show_user_recent_tells(client, conn, nick, True)

