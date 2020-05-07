# miscellaneous functions used in the bot
# author(s): nojusr (add yourself here if you edit this file)
#
# usage:
#   .choose [COMMMA SEPERATED CHOICES]      - make a random choice between
#                                             any comma seperated words
#   .decide [CHOICE 1] or [CHOCIE 2]        - make a random choice between
#                                             two values seperated by 'or'
#   .countdown [SECONDS<20]                 - make a countdown


# first party
from core import hook

# third party
import random
import asyncio
import time

@hook.hook('command', ['choose'])
async def choose(client, data):
    """make a random choice between any comma seperated words"""
    split = data.message.split(',')
    asyncio.create_task(client.message(data.target,(random.choice(split))))
    return


@hook.hook('command', ['decide'])
async def decide(client, data):
    """make a random choice between two values seperated by 'or'"""
    split = data.message.split('or')
    asyncio.create_task(client.message(data.target,(random.choice(split))))
    return


@hook.hook('command', ['countdown'])
async def countdown(client, data):
    """make a countdown"""
    split = data.split_message
    if split[0].isnumeric() == False:
        asyncio.create_task(client.message(data.target,('Please provide a number.')))
        return

    num = int(split[0])

    if num > 20:
        asyncio.create_task(client.message(data.target,('A countdown cannot be longer than 20 seconds')))
        return


    while num >= 1:
        asyncio.create_task(client.message(data.target,(f'{num}...')))
        time.sleep(1)
        num -= 1
        
    asyncio.create_task(client.message(data.target,('Countdown finished!')))
    return