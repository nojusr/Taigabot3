# searx search plugin
# author: nojusr
#
# usage:
#  .g [SEARCH QUERY]            - search with google
#  .sp [SEARCH QUERY]           - search with startpage
#  .ddg [SEARCH QUERY]          - search with duckduckgo
#  .bing [SEARCH QUERY]         - search with bing
# image search:
#   append an 'i' to any of the above commands for image search
#   example: .g [SEARCH QUERY] -> .gi [SEARCH QUERY]

# core library
from core import hook

# 3rd party
import asyncio
import requests

# check https://searx.space/ for searx instances
searx_instance_link = 'https://search.blankenberg.eu/'
searx_instances = [ 'https://search.blankenberg.eu/', 'https://rapu.nz/', 'https://searx.lnode.net/', 'https://searx.mastodontech.de/', 'https://searx.tuxcloud.net/']
is_gd_link = 'https://is.gd/create.php'

def _shorten_url(link):
    """ Is used to shorten a link via is.gd"""


    req_data = {'format': 'simple', 'url': link }
    r = requests.get(is_gd_link, req_data)
    if r.status_code == 200:
        return r.text
    else:
        print(f'SEARCH_DEBUG: is.gd fail: {r.status_code}, {r.text}')
        return f'Failed to shorten link: is.gd returned {r.status_code}'

def _search(client, data, engine):
    """multi-engine search"""
    split = data.split_message

    attrs = {'q' : ' '.join(split[0:]), 'engines': engine, 'categories': 'general', 'safesearch': '0', 'format': 'json'}

    link = ''

    for instance in searx_instances:

        r = requests.get(instance, attrs)

        if r.status_code != 200:
            print (f'SEARCH_DEBUG: Failed to get response from {instance}, got status code {r.status_code}')
            continue
        try:
            link = r.json()["results"][0]["url"]
            title = r.json()["results"][0]["title"]
            desc = r.json()["results"][0]["content"]
        except IndexError:
            print (f'SEARCH_DEBUG: Failed to parse response from {instance}, no results found')
            continue

        break

    if link == '':
        asyncio.create_task(client.message(data.target,("No response found.")))
        return

    short_link = _shorten_url(link)

    desc = desc[0:450]

    output = f'{short_link} -- {title} - {desc}'

    asyncio.create_task(
        client.message(data.target,(output)))
    return


@hook.hook('command', ['g'])
async def gsearch(client, data):
    """search via google"""
    _search(client, data, 'google')
    return


@hook.hook('command', ['sp'])
async def spsearch(client, data):
    """search via startpage"""
    _search(client, data, 'startpage')
    return


@hook.hook('command', ['ddg'])
async def ddgsearch(client, data):
    """search via duckduckgo"""
    _search(client, data, 'duckduckgo')
    return


@hook.hook('command', ['bing'])
async def bingsearch(client, data):
    """search via bing"""
    _search(client, data, 'bing')
    return