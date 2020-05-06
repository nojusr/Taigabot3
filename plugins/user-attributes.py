# user attribute plugin
# author: nojusr
#
# usage:
#  .homescreen @[IRC NICK]          -- check out what homescreen an
#                                      user has
#
#  .homescreen                      -- show your current homescreen
#
#  .homescreen [TEXT]               -- set your current homescreen
#  .homescreen del                  -- delete your current homescreen
#
#  note: the same usage and syntax applies for:
#        .waifu, .desktop, .battlestation, .selfie, .husbando
#  note: you can change the modifable user stats/attributes by adding
#        or removing values from usr_attributes

from typing import List

# import core db functions
from core import db, hook

usr_attributes: List[str] = ['homescreen', 'desktop', 'battlestation',
                             'waifu', 'husbando', 'selfie']


def _update_user_attribute(conn, attr_name, attr_value, username):
    db.set_cell(conn, 'users', attr_name, attr_value, 'nick', username)
    db.ccache()
    return


def _get_user_attribute(conn, attr_name, username):
    attr = db.get_cell(conn, 'users', attr_name, 'nick', username)

    if attr[0][0] is None:
        print('returning error str')
        return f'No {attr_name} found for {username}.'
    else:
        return attr[0][0]


@hook.hook('init', ['statinit'])
async def statinit(client):
    """Is used for initializing the database for this plugin"""
    conn = client.bot.dbs[client.server_tag]
    print(('Initializing stat columns in \'users\''
           f' in /persist/db/{client.server_tag}.db...'))
    for attr in usr_attributes:
        db.add_column(conn, 'users', attr)
    db.ccache()
    print('User stat initialization complete.')


@hook.hook('command', usr_attributes)
async def stat(client, data):
    """Is used for setting and viewing user attributes"""
    conn = client.bot.dbs[data.server]

    message = data.split_message
    command = data.command
    
    """ if command has no other arguments, show the user's attribute """
    if len(message) < 1:
        user_attr = _get_user_attribute(conn, data.command,
                                        data.nickname)
        print(user_attr)
        asyncio.create_task(client.message(data.target, user_attr))
        return

    """ check if user is trying to find another user's attribute """
    if message[0][0] == '@':
        user_to_look_for = message[0][1:]
        user_attr = _get_user_attribute(conn, data.command,
                                        user_to_look_for)

        asyncio.create_task(client.message(data.target, user_attr))
        return

    _update_user_attribute(conn, data.command,
                           data.message, data.nickname)

    asyncio.create_task(client.notice(
                        data.nickname,
                        f'Updated {data.command} for {data.nickname}'))

