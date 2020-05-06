# plugin to save various reminders
# author: nojusr
#
# usage:
#  .reminit                      -- initialize reminder db table
#  .r [REMINDER_NAME] [MESSAGE]  -- add/append to a new reminder
#  #[REMINDER_NAME]              -- view a reminder
#                                   NOTE: can be changed by changing
#                                   the value of remider_trigger_char

from typing import List
import asyncio
from datetime import datetime

# import core db functions
from core import db, hook

# plugin config

max_reminder_len = 550  # maximum length of reminders
max_rem_name_len = 50
reminder_trigger_char = '#'  # chararcter to look for


# db column def; dont touch
reminder_columns: List[str] = ['name', 'msg', 'time_org', 'last_updated']


def _get_reminder_text(conn, reminder_name):
    """Finds reminder text if reminder has any"""

    out = ''

    rem_row = db.get_row(conn, 'reminders', 'name', reminder_name)

    if len(rem_row) == 0:
        return out
    else:
        print(f'REMINDER_DEBUG: {rem_row}')
        out = rem_row[0][1]
        return out


def _create_new_reminder(conn, rem_name, rem_text):
    """Is for creating new reminders in the db"""

    rem_text_trunc = rem_text[:max_reminder_len]
    rem_data = (
        rem_name, rem_text_trunc,
        str(int(time.time())), str(int(time.time())), )
    db.set_row(conn, 'reminders', rem_data)
    db.ccache()


def _append_reminder(conn, rem_name, rem_text):
    """Is for appending to old reminders in the db"""
    old_rem_text = _get_reminder_text(conn, rem_name)
    new_rem_text = f'{old_rem_text} and {rem_text}'

    rem_text_trunc = new_rem_text[:max_reminder_len]

    db.set_cell(conn, 'reminders', 'msg', rem_text_trunc, 'name', rem_name)
    db.set_cell(conn, 'reminders', 'last_updated',
                str(int(time.time())), 'name', rem_name)
    db.ccache()


@hook.hook('init', ['reminit'])
async def reminit(client):
    """Db init command, run once on startup"""
    conn = client.bot.dbs[client.server_tag]
    print(('Initializing reminder database table'
           f'in /persist/db/{client.server_tag}.db...'))
    db.init_table(conn, 'reminders', reminder_columns)
    db.ccache()
    print('Reminder initialization complete.')


@hook.hook('command', ['r'])
async def addrem(client, data):
    """Is a command for adding new reminders"""
    conn = client.bot.dbs[data.server]
    split = data.split_message

    if len(split) <= 0:
        return

    tables = db.get_table_names(conn)
    if 'reminders' not in tables:
        asyncio.create_task(client.message(data.target,
                            ('Reminder table uninitialized. Please ask your'
                             'nearest bot admin to fix the issue.')))

    print ("REMINDER_DEBUG: running func")

    rem_name = split[0]
    rem_name = rem_name[:max_rem_name_len]
    rem_user_text = ' '.join(split[1:])
    rem_text = _get_reminder_text(conn, rem_name)

    print((f'REMINDER_DEBUG: rem_name: {rem_name},'
           f'rem_user_text: {rem_user_text}, rem_text: {rem_text}'))

    if rem_text == '':
        print(f'REMINDER_DEBUG: creating new reminder')
        _create_new_reminder(conn, rem_name, rem_user_text)
    else:
        print(f'REMINDER_DEBUG: appending to reminder')
        _append_reminder(conn, rem_name, rem_user_text)


@hook.hook('event', ['PRIVMSG'])
async def remind(client, data):
    """Is an event that listens for reminder triggers"""
    conn = client.bot.dbs[data.server]
    split = data.split_message

    if len(split) <= 0:
        return

    if split[0][0] == reminder_trigger_char:
        rem_name = split[0][1:]
        rem_text = _get_reminder_text(conn, rem_name)
        if rem_text == '':
            return
        asyncio.create_task(client.message
                            (data.target, f'{rem_name} {rem_text}'))
