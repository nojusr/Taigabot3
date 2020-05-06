# intro plugin
# author: afloat
#
# usage:
# .introinit                    -- database initialization command (admin only)
# .intro [intro message]        -- set your intro message
# .intro @[IRC NICK]            -- check out a user's intro message
# .intro -del OR .intro delete  -- deletes intro message (configurable in intro_clear)

# import core db functions
from core import db, hook

intro_name = 'intro'
intro_clear = ['delete', '-del']


def _update_user_intro(conn, intro_name, intro_value, username):
    """Deleting intro"""
    for intro_clearer in intro_clear:
        if intro_value.startswith(intro_clearer):
            db.set_cell(conn, 'users', intro_name, None, 'nick', username)
            db.ccache()
            return
    db.set_cell(conn, 'users', intro_name, intro_value, 'nick', username)
    db.ccache()
    return


def _get_user_intro(conn, intro_name, username, join):
    intro = db.get_cell(conn, 'users', intro_name, 'nick', username)
    try:
        intro_msg = intro[0][0]
    except:
        return None
    
    if join:
        """Checking intro through JOIN"""
        if intro_msg is not None and len(intro_msg) > 0:
            return intro_msg
        return None
    elif not join:
        """Checking intro through PRIVMSG"""
        if intro_msg is None or len(intro_msg) < 0:
            return f'No {intro_name} saved for {username}.'
        return username + ": " + intro_msg


@hook.hook('init', ['introinit'])
async def introinit(client):
    """Is used for initializing the database for this plugin"""
    conn = client.bot.dbs[client.server_tag]
    print(('Initializing intro column in \'users\''
          f' in /persist/db/{client.server_tag}.db...'))
    db.add_column(conn, 'users', intro_name)
    db.ccache()
    print('User intro initialization complete.')


@hook.hook('command', ['intro'])
async def intro(client, data):
    """Set or delete intro, check other users' intros"""

    conn = client.bot.dbs[data.server]
    message = data.split_message
    command = data.command

    """User is checking own intro"""
    if len(message) < 1:
        intro_attr = _get_user_intro(conn, data.command, data.nickname, False)
        asyncio.create_task(client.message(data.target, intro_attr))
        return

    """User is checking another user's intro"""
    if message[0][0] == '@':
        user_to_look_for = message[0][1:]
        intro_attr = _get_user_intro(conn, data.command, user_to_look_for, False)
        asyncio.create_task(client.message(data.target, intro_attr))
        return

    """User is setting an intro for self"""
    _update_user_intro(conn, data.command, data.message, data.nickname)
    for intro_clearer in intro_clear:
        if data.message.startswith(intro_clearer):
            asyncio.create_task(client.notice(data.target, f'Deleted your intro'))
            return
    asyncio.create_task(client.notice(data.nickname, f'Updated {data.command} for {data.nickname}'))
    return


@hook.hook('event', ['JOIN'])
async def on_connect_show_intro(client, data):
    conn = client.bot.dbs[data.server]
    intro_attr = _get_user_intro(conn, intro_name, data.nickname, True)
    if intro_attr is not None:
        asyncio.create_task(client.message(data.target, '\x02\x02' + intro_attr))
    return
