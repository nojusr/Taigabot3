# homages to shitbot
# author: nojusr
# Standard Libs
# Standard Libs
# Standard Libs
# Standard Libs
# Standard Libs
import asyncio
import random
import sqlite3
import time

# First Party
from core import hook
# import messaging from utils, so that i could into action (i.e /me in irssi)
from util import messaging


@hook.hook('command', ['morr'])    #morr dispenser
async def morrr(client, data):
    out = 'hands '
    if data.message == '':
        out += data.nickname
    else:
        tmpstr = data.message
        out += tmpstr.split(' ')[0]
    out += ' a nice butterbrod with '
    out += str(random.randint(2, 8))
    out += ' slices of that norwegian goodness on it.'
    out = f'\x01ACTION {out}\x01'
    asyncio.create_task(client.message(data.target, out))


@hook.hook('command', ['s8ball'])    #shitty version of 8ball
async def sball(client, data):
    out = 'your dumb ass didn\'t even ask a question'
    if data.message != '':
        choices = [
            "not today, ho", "ask Kali_",
            "ask your friendly neighbourhood cat", "i dont know", "yeh", "no",
            "nope", "yes, but only if you're gay", "ask shitbot", "maybe",
            "ask the same thing 12 seconds later", "probably",
            "if you have the need to ask that, then you might as well kill yourself",
            "ask your gay cat", "yes, but you will end up a soyboy in a vape shop",
            "that was a stupid question", "only if its ironic",
            "there is no good awnser to this one", "no thats gay",
            "ask adrift", "so we have a smartass, eh?"
        ]
        awnser = random.choice(choices)
        out = 'says... '
        out += awnser
        out = f'\x01ACTION {out}\x01'
    asyncio.create_task(client.message(data.target, out))
<<<<<<< HEAD


@hook.hook('event', ['JOIN'])
async def abuse_kimi_and_ine(client, data):
    nick = data.nickname
    nick = nick.lower()
    
    if nick == 'kimi':
        asyncio.create_task(client.message(data.target, '\x02[QUALITY OF CHANNEL SIGNIFICANTLY DECREASED]\x02'))
    
    
=======
>>>>>>> ea6f341077c6add8bfdcaed5119610c323799ad8
