# youtube search plugin
# author: nojusr
#
# usage:
#  .yt [SEARCH TERM]       -- search for a video on youtube.
#                             links are shortened via is.gd
#
# note: to configure this plugin you need to add a youtube api key
#       into the "api_keys" section of config.json. Example:
#       "api_keys": { "youtube": "XXXXXXXXXXXXXXXXX" }


from core import hook

import asyncio
import requests
from datetime import datetime
import dateutil.parser


def _get_video_time(time_str):
    print(time_str)
    if 'H' in time_str:
        date = datetime.strptime(time_str, 'PT%HH%MM%SS')
    elif 'M' in time_str:
        date = datetime.strptime(time_str, 'PT%MM%SS')
    elif 'S' in time_str:
        date = datetime.strptime(time_str, 'PT%SS')
    else:
        return 'too short'

    out = ''

    if date.hour > 0:
        out += f'{date.hour}h '
    if date.minute > 0:
        out += f'{date.minute}m '
    if date.second > 0:
        out += f'{date.second}s'


    print(f'YOUTUBE_DEBUG: datestr: {out}')
    return out


def _get_video_stats(yt_api_key, vid_id):
    """Returns a short description string of the video"""
    youtube_api_url = 'https://www.googleapis.com/youtube/v3/videos'

    datastr = 'snippet,statistics,contentDetails'

    req_attrs = {'part' : datastr,
                 'key': yt_api_key, 'id': vid_id}

    r = requests.get(youtube_api_url, req_attrs)

    try:
        data = r.json()['items'][0]
    except:
        return 'Failed to get stats.'

    title = data['snippet']['title']
    channel_name = data['snippet']['channelTitle']

    duration_str = data['contentDetails']['duration']
    duration = _get_video_time(duration_str)

    views = int(data['statistics']['viewCount'])

    likes = int(data['statistics']['likeCount'])
    dislikes = int(data['statistics']['dislikeCount'])

    upload_date = data['snippet']['publishedAt']

    upload_datetime = dateutil.parser.parse(upload_date)

    # IRC formatting black magic
    # btw i found the correct IRC color codes here:
    # https://github.com/rossengeorgiev/pydle-irc/blob/master/pydle/colors.py
    out =  f'\02{title}\02'
    out += f' - length \02{duration}\02 - '
    out += f'\x0309↑{likes:,}\x03, '
    out += f'\x0304↓{dislikes:,}\x03 - '
    out += f'\02{views:,}\02 views - \02{channel_name}\02 '
    out += f'on \02{upload_datetime.year:04d}.{upload_datetime.month:02d}.'
    out += f'{upload_datetime.day:02d}\02'
    return out


@hook.hook('command', ['yt', 'youtube'])
async def ytsearch(client, data):

    split = data.split_message

    youtube_api_url = 'https://www.googleapis.com/youtube/v3/search'

    try:
        yt_key = client.bot.config['api_keys']['youtube']
    except KeyError:
        asyncio.create_task(
            client.message(
                data.target,
                ('No Youtube API key found. Please create a Google '
                 'API account and add it to the config file.')))
        return

    req_params = {'part': 'snippet', 'key' : yt_key, 'maxResults': '1',
                  'order': 'relevance', 'q': ' '.join(split) }

    r = requests.get(youtube_api_url, req_params)

    if r.status_code == 403:
        print(f'YOUTUBE_DEBUG: network error: {r.status_code}')
        print(f'YOUTUBE_DEBUG: {r.text}')
        asyncio.create_task(client.message(data.target,'Youtube API quota exceeded.'))
        return

    if r.status_code != 200:
        print(f'YOUTUBE_DEBUG: network error: {r.status_code}')
        print(f'YOUTUBE_DEBUG: {r.text}')
        asyncio.create_task(client.message(data.target,'Network error occured.'))
        return

    video_url = 'https://youtu.be/'

    if r.json()['pageInfo']['totalResults'] == 0:
        asyncio.create_task(client.message(data.target,
                            'No results found.'))
        return

    try:
        first_item = r.json()['items'][0]
    except KeyError:
        print('YOUTUBE_DEBUG: failed to get first item in response ')
        return

    vid_id = first_item['id']['videoId']

    stats = _get_video_stats(yt_key, vid_id)

    output = f'{stats} - {video_url+vid_id}'

    asyncio.create_task(client.message(data.target, output))














