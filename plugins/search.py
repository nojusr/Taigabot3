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
searx_instances = [ 'https://search.bunker.is/', 'https://searx.win/', 'https://searx.xyz/', 'https://search.galaxy.cat/', 'https://searx.lnode.net/', 'https://searx.mastodontech.de/', 'https://searx.tuxcloud.net/']
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

    attrs = {
        'q' : ' '.join(split[0:]), 
        'engines': engine,
        'categories': 'general,news,science,social+media',
        'language': 'en-US',
        'format': 'json'
    }

    link = ''
    title = ''
    desc = ''

    for instance in searx_instances:

        r = requests.get(instance, attrs)

        if r.status_code != 200:
            print (f'SEARCH_DEBUG: Failed to get response from {instance}, got status code {r.status_code}')
            continue

        try:
            title = r.json()["results"][0]["title"]
        except:
            print (f'SEARCH_DEBUG: title not found in response')
            pass

        try:
            desc = r.json()["results"][0]["content"]
        except:
            print (f'SEARCH_DEBUG: content not found in response')
            pass

        try:
            link = r.json()["results"][0]["url"]
        except IndexError:
            print (f'SEARCH_DEBUG: Failed to parse response from {instance}, no results found')
            continue

        break

    if link == '':
        asyncio.create_task(client.message(data.target,("No response found.")))
        return

    short_link = _shorten_url(link)

    try:
        desc = desc[0:450]
    except:
        pass

    if title != '' and desc != '':
        output = f'{short_link} -- {title} - {desc}'
    elif desc != '':
        output = f'{short_link} -- [NO TITLE] - {desc}'
    elif title != '':
        output = f'{short_link} -- {title} - [NO DESC]'
    else:
        output = f'{short_link} -- [NO TITLE] - [NO DESC]'

    asyncio.create_task(
        client.message(data.target,(output)))
    return

def _img_search(client, data, engine):
    """multi-engine image search"""
    split = data.split_message


    attrs = {
        'q' : ' '.join(split[0:]),
        'engines': engine,
        'categories': 'images',
        'language': 'en-US',
        'format': 'json'
    }

    link = ''

    for instance in searx_instances:

        r = requests.get(instance, attrs)

        if r.status_code != 200:
            print (f'SEARCH_DEBUG: Failed to get response from {instance}, got status code {r.status_code}')
            continue

        print(r.text)
        print (len(r.json()['results']))
        
        if len(r.json()['results']) <= 0:
            print (f'SEARCH_DEBUG: No results found from {instance}')
            continue

        try:
            link = r.json()["results"][0]["img_src"]
        except:
            print(f'SEARCH_DEBUG: could not find image source from {instance}')
            continue

        break

    if link == '':
        asyncio.create_task(client.message(data.target,("No response found.")))
        return

    short_link = _shorten_url(link)

    output = f'{short_link}'

    asyncio.create_task(
        client.message(data.target,(output)))
    return


@hook.hook('command', ['g'])
async def gsearch(client, data):
    """search via google"""
    _search(client, data, 'google')
    return

@hook.hook('command', ['gi'])
async def gisearch(client, data):
    """search via google"""
    _img_search(client, data, 'google_images')
    return


@hook.hook('command', ['sp'])
async def spsearch(client, data):
    """search via startpage"""
    _search(client, data, 'startpage')
    return

# startpage has no available image search

@hook.hook('command', ['ddg'])
async def ddgsearch(client, data):
    """search via duckduckgo"""
    _search(client, data, 'duckduckgo')
    return


@hook.hook('command', ['ddgi'])
async def ddgisearch(client, data):
    """search via google"""
    _img_search(client, data, 'duckduckgo_images')
    return


@hook.hook('command', ['bing'])
async def bingsearch(client, data):
    """search via bing"""
    _search(client, data, 'bing')
    return

@hook.hook('command', ['bingi'])
async def bingisearch(client, data):
    """search via google"""
    _img_search(client, data, 'bing_images')
    return