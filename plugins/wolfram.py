# wolfram alpha plugin
# author: nojusr
#
# usage:
# .wa, .calc [QUESTION]              -- ask wolfram alpha any
#                                       mathematical/statistics question
# config:
#   you need to create an appID in https://developer.wolframalpha.com/,
#   and put it in config.json like this:
#     "api_keys": {
#       "wolfram_alpha": "XXXXX-XXXXXX"
#     },

from core import hook

import asyncio
import requests

wolfram_api_url = 'https://api.wolframalpha.com/v1/result'


def _get_wa_api_key(client):
    """This function tries to get the wolfram alpha appID from config"""
    try:
        wa_key = client.bot.config['api_keys']['wolfram_alpha']
        return wa_key
    except KeyError:
        return ''


@hook.hook('command', ['wa', 'calc', 'math'])
async def wolfram(client, data):
    """
    This command interfaces with the wolfram alpha API to get
    mathematical and statistical awnsers
    """

    split = data.split_message

    wa_key = _get_wa_api_key(client)

    print(f'WOLFRAM_DEBUG: wa_key: {wa_key}')

    if wa_key == '':
        asyncio.create_task(client.message(data.target,
                            ('No WolframAlpha appID found. '
                             'Ask your nearest bot admin to '
                             'get one and add it into the config.')))
        return

    query = ' '.join(split)

    req_data = {'appid': wa_key, 'i': query, 'units': 'metric'}

    r = requests.get(wolfram_api_url, req_data)
    print(f'WOLFRAM_DEBUG: final url of request: {r.url}')
    print(f'WOLFRAM_DEBUG: response: {r}')
    print(f'WOLFRAM_DEBUG: actual awnser: {r.text}')

    if r.status_code == 200:
        asyncio.create_task(client.message(data.target, r.text))
    elif r.status_code == 501:
        asyncio.create_task(client.message(data.target,
                            ('Wolfram Alpha returned an error. '
                             'Did you phrase your question correclty?')))
    elif r.status_code == 400:
        asyncio.create_task(client.message(data.target,
                            ('Wolfram Alpha returned an error. '
                             'Did you enter a question?')))
    else:
        print(f'WOLFRAM_ERROR: response_code: {r.status_code}')
        asyncio.create_task(client.message(data.target,
                            'Unknown network error occured.'))
