# last.fm plugin
# author: nojusr
#
# usage:
#  .np [@irc nick OR last.fm username ] -- find out what is playing for
#                                          a last.fm user. Usernames
#                                          are saved and remembered
#
#
# TODO:
# .compat [lastfm_nickname] [lastfm_nickname] -- get compatiblity
#                                                between two lastfm users.
# NOTE .compat can be used like this too:
# .compat @[irc_nick] (compares your saved nick with the argument nick)
# .compat [lastfm_nick] (same as above, but with a lastfm nick)
# .compat @[irc_nick] [lastfm_nick]
# .compat [irc_nick] @[lastfm_nick]
# .compat @[irc_nick] @[irc_nick]


from typing import List
import asyncio
import requests
from datetime import datetime

# import core db functions
from core import db, hook

lfm_api_url = 'https://ws.audioscrobbler.com/2.0/?format=json'


def _get_lastfm_nick(conn, irc_nick):
    names = db.get_column_names(conn, 'users')

    nicks = db.get_row(conn, 'users', 'nick', irc_nick)
    try:
        for i, name in enumerate(names):
            if name == 'lastfm':
                if nicks[0][i] == '':
                    return None
                else:
                    return nicks[0][i]
    except IndexError:
        return None


def _add_lastfm_nick(conn, irc_nick, lastfm_nick):
    nick_check = _get_lastfm_nick(conn, irc_nick)
    db.set_cell(conn, 'users',
                'lastfm', lastfm_nick,
                'nick', irc_nick)

    return lastfm_nick


def _pull_latest_track(api_key, lastfm_nick):
    url = lfm_api_url+f'&method=user.getrecenttracks'
    url += f'&user={lastfm_nick}&api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        try:
            track = response.json()['recenttracks']['track'][0]
            return track
        except:
            print(f'LASTFM_DEBUG: WEBSITE RESPONSE: {response.text}')
            return None


def _pull_track_tags(api_key, track_title, track_artist):
    url = lfm_api_url+f'&method=track.gettoptags&track={track_title}'
    url += f'&artist={track_artist}&api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        try:
            tags_json = response.json()['toptags']['tag'][0:5]
        except IndexError:
            tags_json = response.json()['toptags']['tag']

        if len(tags_json) < 1:
            return 'none'

        tags = ', '.join(tag['name'] for tag in tags_json)
        return tags


def _pull_track_plays(api_key, track_title, track_artist, lastfm_nick):
    url = lfm_api_url+f'&method=track.getinfo&username={lastfm_nick}'
    url += f'&track={track_title}&artist={track_artist}'
    url += f'&api_key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        try:
            playcount_json = response.json()['track']['userplaycount']
            return str(playcount_json)
        except:
            return 'unknown'


def _output_nowplaying(client, data, lastfm_nick,
                       title, artist, album, plays, tags):

    out = f'{lastfm_nick} is listening to "{title}" by \02{artist}\02 from '
    if album == 'an unknown album':
        out += album
    else:
        out += f'the album \02{album}\02'

    out += f', Play count: {plays}, Tags: {tags}.'

    asyncio.create_task(
        client.message(
            data.target, out))

    return


@hook.hook('init', ['lfminit'])
async def lfminit(client):
    """Is used for initializing the database for this plugin"""
    conn = client.bot.dbs[client.server_tag]
    print(('Initializing lastfm column in \'users\''
           f' in /persist/db/{client.server_tag}.db...'))
    db.add_column(conn, 'users', 'lastfm')
    db.ccache()
    print('Last.fm initialization complete.')


@hook.hook('command', ['np'])
async def nowplaying(client, data):
    """.np [@irc nick OR lastfm nick] --- Find out what is currently
    playing for an user."""

    conn = client.bot.dbs[data.server]
    split = data.split_message

    try:
        lastfm_key = client.bot.config['api_keys']['last_fm']
    except KeyError:
        asyncio.create_task(
            client.message(
                data.target,
                ('No last.fm API key found. Please create an API account, '
                 'add it\'s API key to \'api_keys\' in config.json with '
                 'the tag \'last_fm\'')))
        return

    # deal with getting the last.fm nickname

    if len(split) > 0:
        arg = split[0]
        if arg[0] == '@':
            arg = arg[1:]
            lastfm_nick = _get_lastfm_nick(conn, arg)
        else:
            lastfm_nick = _add_lastfm_nick(conn, data.nickname, arg)

        if lastfm_nick is None:
            asyncio.create_task(
                client.message(
                    data.target,
                    'No associated last.fm nickname found.'))
            return
    else:
        lastfm_nick = _get_lastfm_nick(conn, data.nickname)

        if lastfm_nick is None:
            asyncio.create_task(
                client.message(
                    data.target,
                    'No associated last.fm nickname found.'))
            return

    track = _pull_latest_track(lastfm_key, lastfm_nick)

    if track is None:
        asyncio.create_task(
            client.message(
                data.target,
                f'No recent tracks found for {lastfm_nick}.'))
        return

    # extract track data
    title = track['name']
    artist = track['artist']['#text']
    album = track['album']['#text']
    if album == '':
        album = 'an unknown album'

    # gather other data
    tags = _pull_track_tags(lastfm_key, title, artist)
    plays = _pull_track_plays(lastfm_key, title, artist, lastfm_nick)

    # final output
    _output_nowplaying(client, data, lastfm_nick,
                       title, artist, album, plays, tags)
