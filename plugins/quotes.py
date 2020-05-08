#quote plugin
#author: nojusr
#
#usage:
# .qinit                                       --- database initialization command (admin only)
# .q [nick/channel] [optional quote number]    --- for fetching quotes by their number (or a random quote)
# .q [nick/channel] [search term]              --- for fetching quotes by a search term
# .q add [nick] [quote]                        --- for adding quotes
# .q delete [quote number]                     --- for deleting quotes (you can only delete your own quotes)
#


<<<<<<< HEAD
from typing import Optional, Dict, Any, List, Set, Union, Callable, Tuple
from dataclasses import dataclass, field
import time
=======
# Standard Libs
>>>>>>> ea6f341077c6add8bfdcaed5119610c323799ad8
import asyncio
import random
import time
from typing import List

<<<<<<< HEAD
#import core db functions
from core import db

=======
# First Party
# import core db functions
from core import db, hook

# Third Party
import requests

# db table definition
quote_columns: List[str] = [
    'chan', 'nick', 'add_nick', 'msg', 'time', 'deleted'
]
>>>>>>> ea6f341077c6add8bfdcaed5119610c323799ad8

#db table definition
quote_columns: List[str] = ['chan', 'nick', 'add_nick', 'msg', 'time', 'deleted']

def remove_quotes(quotelist):
    """removes quotes from a quotelist where deleted == '1' """
    buf = []
    for quote in quotelist:
        if quote[5] != '1':
            buf.append(quote)

    return buf

def display_quote(client, data, quotelist, target, arg):
    """
    output a quote, given a tuple list of all avalable quotes, and possibly
    a number (for selection of a specific quote)
    """
    usertarg = target
    
    outquotes = []
    quotenums = []
    wordarg = None
    numarg = None

    if not arg:
        # pick a random number from the quotelist
        # if no argument is provided

        if len(quotelist)-2 > 0:
            numarg = random.randint(0, len(quotelist)-2)
        else:
            numarg = random.randint(0, len(quotelist)-1)

    else:
        try:
            numarg = int(arg)
            if numarg > 0:
                numarg -= 1
        except:
            wordarg = arg


    quotelist = remove_quotes(quotelist)

    if len(quotelist) < 1:
        asyncio.create_task(client.message(data.target, f'I have no quotes for {target}'))
        return

<<<<<<< HEAD
=======
    if isinstance(search, int):
        try:
            quotes.append(quotelist[search])
            if search < 0:
                quotenums.append(len(quotelist) + search + 1)
            else:
                quotenums.append(search + 1)
        except IndexError:
            asyncio.create_task(
                client.message(data.target, (
                    f'I only have {str(len(quotelist))} quote(s) for'
                    f'{target}')))
    else:
        for i, value in enumerate(quotelist):
            if search in value[3]:
                quotes.append(value)
                quotenums.append(i + 1)
    _message_or_paste(client, data, quotenums, quotelist)
>>>>>>> ea6f341077c6add8bfdcaed5119610c323799ad8


    if numarg != None:
        try:

            outquotes.append(quotelist[numarg])
            if numarg < 0:
                quotenums.append(len(quotelist)+numarg+1)
            else:
                quotenums.append(numarg+1)
        except IndexError:
            if len(quotelist) == 1:
                asyncio.create_task(client.message(data.target, f'I only have 1 quote for {target}'))
            else:
                asyncio.create_task(client.message(data.target, f'I only have {str(len(quotelist))} quotes for {target}'))
    elif wordarg != None:
        for i in range(len(quotelist)):
            quote = quotelist[i]
            if wordarg in quote[3]:
                outquotes.append(quote)
                quotenums.append(i+1)

    #if we have more than five quotes....
    if len(outquotes) > 5:
        #append each quote with '\n', smack it right into hastebin
        out = ''
        for i in range(len(outquotes)):
            quote = outquotes[i]
            out += f'[{str(quotenums[i])}/{str(len(quotelist))}]'
            out += f' <{quote[1]}> {quote[3]}\n'

        response = requests.post('https://pastie.io/documents', data=out)
        if response.status_code == 200:
            d = response.json()['key']
            link = f'https://pastie.io/{str(d)}.txt'
            asyncio.create_task(client.message(data.target, link))
        else:
            asyncio.create_task(client.message(data.target, 'Failed to upload quotes onto pastebin.'))

    elif len(outquotes) > 0:
        #if not, send each quote as a seperate message
        for i in range(len(outquotes)):
            quote = outquotes[i]
            out = f'[{str(quotenums[i])}/{str(len(quotelist))}]'
            out += f' <{target}> {quote[3]}'
            asyncio.create_task(client.message(data.target, out))
    else:
        asyncio.create_task(client.message(data.target, 'No results.'))


@hook.hook('init', ['qinit'])
async def quoteinit(client):
    """quote initialization function, run once upon startup"""
    conn = client.bot.dbs[client.server_tag]
    print (f'Initializing quote table in /persist/db/{client.server_tag}.db...')
    db.init_table(conn, 'quotes', quote_columns)
    db.ccache()
    print ('Quote initialization complete.')

@hook.hook('command', ['q'])
async def quotes(client, data):
    """main quote hook"""
    conn = client.bot.dbs[data.server]
    split = data.message.split()

    tables = db.get_table_names(conn)
    if 'quotes' not in tables:
<<<<<<< HEAD
        asyncio.create_task(client.message(data.target, 'Quote table uninitialized. Please ask your nearest bot admin to run .qinit.'))
=======
        asyncio.create_task(
            client.message(data.target, (
                'Quote table uninitialized. Please ask your nearest bot'
                'admin to run .qinit.')))

    if message[0] == 'add':
        quotedata = (data.target, message[1], data.nickname,
                     ' '.join(message[2:]), int(time.time()), '0')
        db.set_row(conn, 'quotes', quotedata)
        asyncio.create_task(client.message(data.target, 'Quote added.'))
        db.ccache()
        return
    elif message[0] == 'del':
        quotes = db.get_row(conn, 'quotes', 'nick', data.nickname)
>>>>>>> ea6f341077c6add8bfdcaed5119610c323799ad8

    #TODO: fix weird ass edgecase with users when a nick that corresponds to a command

    if len(split) > 1:
        if split[0] == 'add' or split[0] == 'a':
            nick = split[1].lower()

            quote = ' '.join(split[2:])
            quotedata = (data.target, nick, data.nickname, quote, int(time.time()), '0',)
            db.set_row(conn, 'quotes', quotedata)
            asyncio.create_task(client.notice(data.nickname, 'Quote added.'))
            db.ccache()
            return

        elif split[0] == 'delete' or split[0] == 'r' or split[0] == 'remove':
            nickquotes = db.get_row(conn, 'quotes', 'nick', data.nickname.lower())
            numarg = None

            try:
                numarg = int(split[1])
                if numarg > 0:
                    numarg -= 1
            except:
                asyncio.create_task(client.message(data.target, 'You need to use a number when deleting quotes.'))
                return
<<<<<<< HEAD
=======
            cur = conn.cursor()
            cur.execute(
                "UPDATE quotes SET deleted='1' WHERE msg=? AND time=?",
                (quote[3], quote[4]))
            del cur
            conn.commit()
            db.ccache()
            asyncio.create_task(client.message(data.target, 'Quote deleted.'))
>>>>>>> ea6f341077c6add8bfdcaed5119610c323799ad8

            nickquotes = remove_quotes(nickquotes)
            if len(nickquotes) > 0:
                try:
                    #get quote to delete
                    quote = nickquotes[numarg]
                except:
                    if len(nickquotes) == 1:
                        asyncio.create_task(client.message(data.target, 'You only have 1 quote.'))
                    else:
                        asyncio.create_task(client.message(data.target, f'You only have {str(len(nickquotes))} quote(s).'))
                    return

                """gotta do custom query since i couldn't find anything in db.py that suits my needs.
                i'm using both the time and the quote itself because it's the quickest sure way to know that that quote is unique
                afaik it's very unlikely that the bot is fast enough to process two or more inputs within a second
                """

                cur = conn.cursor()
                cur.execute("UPDATE quotes SET deleted='1' WHERE msg=? AND time=?", (quote[3], quote[4]))
                del cur
                conn.commit()
                db.ccache()
                asyncio.create_task(client.notice(data.nickname, 'Quote deleted.'))

                return
            else:
                asyncio.create_task(client.message(data.target, 'You have no quotes.'))
                return

    if len(split) > 0 and len(data.message) > 0:
        argtuple = split[0].lower(),

        #convert split[0] (we now know that it needs to be compared with a db) into a tuple, since we get db results in a tuple

        if data.message[0] == '#':
            channels = db.get_column(conn, 'channels', 'channel')

            if argtuple in channels:
                chanquotes = db.get_row(conn, 'quotes', 'chan', split[0].lower())
                try:
                    display_quote(client, data, chanquotes, split[0], split[1])
                except:
                    display_quote(client, data, chanquotes, split[0], None)

            else:
                asyncio.create_task(client.message(data.target, f'No quotes found for {split[0]}.'))
        else:
            users = db.get_column(conn, 'quotes', 'nick')

            if argtuple in users:
                print(split[0])
                print(split[0].lower())
                nickquotes = db.get_row(conn, 'quotes', 'nick', split[0].lower())
                try:
                    display_quote(client, data, nickquotes, split[0], split[1])
                except:
                    display_quote(client, data, nickquotes, split[0], None)
            else:
                asyncio.create_task(client.message(data.target, f'No quotes found for {split[0]}.'))

