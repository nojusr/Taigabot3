# .bots plugin

# author: ine
#
# usage:
# .bots, .source                    -- show some information about the bot

from core import hook

import asyncio

@hook.hook('command', ['bots'])
async def bots(client, data):
    asyncio.create_task(client.message(data.target, 'Reporting in! [Python]'))

@hook.hook('command', ['source'])
async def source(client, data):
    asyncio.create_task(client.message(data.target, '\x02paprika\x02 - Fuck my shit up https://github.com/nojusr/paprika'))
