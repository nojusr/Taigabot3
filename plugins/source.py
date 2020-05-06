# source, help, and .bots plugin
# author: nojusr
#
# usage:
#  .help                 -- get help with the bot
#  .bots                 -- confirm the bot's presence in a channel
#  .source               -- get the git repository of the bot

from core import hook


@hook.hook('command', ['help'])
async def bothelp(client, data):
    out =  'You can find description and usage of every plugin '
    out += 'installed in the source at '
    out += 'https://github.com/nojusr/paprika/tree/master/plugins'
    asyncio.create_task(client.message(data.target, out))


@hook.hook('command', ['source'])
async def source(client, data):
    out = 'Here\'s my source: https://github.com/nojusr/paprika'
    asyncio.create_task(client.message(data.target, out))


@hook.hook('command', ['bots'])
async def bots(client, data):
    name = client.bot.config['servers'][data.server]['nick']
    out = f'{name} reporting in!'
    asyncio.create_task(client.message(data.target, out))
