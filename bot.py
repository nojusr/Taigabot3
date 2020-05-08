"""Main file for running Taigabot."""

# Standard Libs
import asyncio
import base64
import difflib
import os
import pprint
import signal
import sys
from pathlib import Path
from sqlite3 import Connection
from ssl import SSLContext
from typing import (Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar,
                    Union, cast)

# First Party
from core import config, db, irc, plugins
from core.data import Bot, Config, Message, ParsedRaw, ServerConfig, User
from util import user

#import pydle

DBResult = Optional[List[Tuple[Optional[str], ...]]]
# Used for commands, events, and sieves
CommandFunc = TypeVar('CommandFunc')
CommandDict = Dict[str, List[CommandFunc]]

# PydleClient: pydle.Client = pydle.featurize(
#     pydle.features.RFC1459Support, pydle.features.IRCv3Support,
#     pydle.features.AccountSupport, pydle.features.CTCPSupport,
#     pydle.features.ISUPPORTSupport, pydle.features.TLSSupport)
#:livingstone.freenode.net CAP TestTaiga LS :account-notify extended-join identify-msg multi-prefix sasl
#:irc.x2x.cc CAP TestTaiga LS :away-notify chghost invite-notify multi-prefix sasl userhost-in-names
#:calamity.esper.net CAP TestTaiga LS :account-notify away-notify cap-notify chghost extended-join multi-prefix sasl tls userhost-in-names

#:irc.hellhoundslair.org 005 TestTaiga CALLERID CASEMAPPING=rfc1459 DEAF=D KICKLEN=180 MODES=4 PREFIX=(qaohv)~&@%+ STATUSMSG=~&@%+ EXCEPTS=e INVEX=I NICKLEN=30 NETWORK=Rizon MAXLIST=beI:250 MAXTARGETS=4 :are supported by this server
#:irc.hellhoundslair.org 005 TestTaiga CHANTYPES=# CHANLIMIT=#:250 CHANNELLEN=50 TOPICLEN=390 CHANMODES=beI,k,l,BCMNORScimnpstz NAMESX UHNAMES WATCH=60 KNOCK ELIST=CMNTU SAFELIST AWAYLEN=180 :are supported by this server

#:catastrophe.esper.net 005 TestTaiga CPRIVMSG CNOTICE ETRACE FNC KNOCK MONITOR=100 WHOX CHANTYPES=# EXCEPTS INVEX CHANMODES=eIbq,k,flj,CFLPQTcgimnprstz CHANLIMIT=#:50 :are supported by this server
#:catastrophe.esper.net 005 TestTaiga PREFIX=(ov)@+ MAXLIST=bqeI:100 MODES=4 NETWORK=EsperNet STATUSMSG=@+ CALLERID=g CASEMAPPING=rfc1459 NICKLEN=24 MAXNICKLEN=30 CHANNELLEN=50 TOPICLEN=390 DEAF=D :are supported by this server
#:catastrophe.esper.net 005 TestTaiga TARGMAX=NAMES:1,LIST:1,KICK:1,WHOIS:1,PRIVMSG:4,NOTICE:4,ACCEPT:,MONITOR: EXTBAN=$,acjorsxz CLIENTVER=3.0 SAFELIST ELIST=CTU :are supported by this server

#:card.freenode.net 005 TestTaiga CHANTYPES=# EXCEPTS INVEX CHANMODES=eIbq,k,flj,CFLMPQScgimnprstz CHANLIMIT=#:120 PREFIX=(ov)@+ MAXLIST=bqeI:100 MODES=4 NETWORK=freenode STATUSMSG=@+ CALLERID=g CASEMAPPING=rfc1459 :are supported by this server
#:card.freenode.net 005 TestTaiga CHARSET=ascii NICKLEN=16 CHANNELLEN=50 TOPICLEN=390 DEAF=D FNC TARGMAX=NAMES:1,LIST:1,KICK:1,WHOIS:1,PRIVMSG:4,NOTICE:4,ACCEPT:,MONITOR: EXTBAN=$,ajrxz CLIENTVER=3.0 KNOCK CPRIVMSG CNOTICE :are supported by this server
#:card.freenode.net 005 TestTaiga WHOX SAFELIST ELIST=CTU ETRACE :are supported by this server


class Taigabot(irc.IRC):

    def __init__(self, config: Config, server_name: str,
                 ssl: Union[bool, SSLContext]):
        self.ssl = ssl
        self.full_config = config
        self.server_name = server_name
        self.server_config: ServerConfig = self.full_config.servers[
            self.server_name]
        self.plugin_dir: Path = Path(self.full_config.plugin_dir).resolve()
        self.plugins: Dict[str, Dict[str, Callable]] = {
            'command': {},
            'event': {},
            'init': {},
            'sieve': {}
        }
        self.plugin_mtimes: Dict[str, float] = {}
        self.plugin_mtimes, self.plugins = plugins.reload(
            self.plugin_dir, self.plugin_mtimes, self.plugins)
        self.users: Dict[str, User] = {}
        self.db: Connection = db.connect(self.full_config.db_dir,
                                         self.server_name)
        super().__init__(self.server_config)

    async def nickserv(self) -> None:
        self.send_privmsg([self.server_config.nickserv_nick],
                          self.server_config.nickserv_command.
                          format(self.server_config.nickname_password))

    async def start(self) -> None:    # on_connect
        await self.connect()
        await asyncio.gather(self.authenticate(), self.read_loop())

    async def authenticate(self) -> None:
        await super().authenticate()
        if 'sasl' not in self.server_config.capabilities:
            if self.server_config.nickname_password:
                await self.nickserv()

    async def connect(self) -> None:
        return await self.create_connection(self.server_config.server,
                                            self.server_config.port, self.ssl)

    async def _run_output_sieves(self, message: str) -> Union[None, str]:
        msg = message
        for name, funcs in self.plugins['sieve'].items():
            if name not in self.server_config.disabled and name.endswith(
                    '-output'):
                for func in funcs:
                    msg = await func(self, msg)
        return msg

    async def send_line(self, message: str) -> None:
        msg = await self._run_output_sieves(message)
        if msg:
            await super().send_line(msg)

    async def send_join(self, channels: List[str]) -> None:
        new_channels = channels
        for channel in channels:
            tmp_channel = channel
            if ' ' in channel:
                tmp_channel = channel.split()[0]
            if tmp_channel in self.server_config.no_channels:
                new_channels.remove(channel)
        if new_channels:
            await super().send_join(new_channels)
        return

    async def _userhost_from_names(self, nick: str) -> Tuple[str, str, str]:
        nickname = nick
        userhost = ''
        username = ''
        if '!' in nick:
            userhost = nick
            nickname = userhost.split('!')[0]
            username = userhost.split('!')[1].split('@')[0]
        return nickname, username, userhost

    async def _chanmodes_from_names(self, nick: str, userhost: str = ''
                                    ) -> Tuple[str, str, str]:
        nickname = nick
        channel_mode = '+'
        for char in nick:
            modes = {'+': 'v', '%': 'h', '@': 'o', '&': 'a', '~': 'q'}
            if char in modes.keys():
                if userhost:
                    userhost = userhost.replace(char, '')
                nickname = nickname.replace(char, '')
                channel_mode += modes[char]
        return nickname, channel_mode, userhost

    async def _chanmodes_from_chans(self, channels: List[str]
                                    ) -> Tuple[Dict[str, str], List[str]]:
        channel_modes = {}
        new_channels = []
        for channel in channels:
            channel, channel_mode, host = await self._chanmodes_from_names(
                channel)
            if channel_mode != '+':
                channel_modes[channel] = channel_mode
            new_channels.append(channel)
        return channel_modes, new_channels

    async def track_users_userhost(self, userhost: str) -> None:
        if '!' in userhost:
            username_user_set = False
            if '~' in userhost:
                username_user_set = True
                userhost = userhost.replace('~', '')
            nickname = userhost.split('!')[0]
            username = userhost.split('!')[1].split('@')[0]
            if nickname not in self.users.keys():
                user = User(nickname, self)
                user.userhost = userhost
                user.username = username
                user.username_user_set = username_user_set
                self.users[nickname] = user
            elif nickname in self.users.keys():
                self.users[nickname].userhost = userhost
                self.users[nickname].username = username
                self.users[nickname].username_user_set = username_user_set

    async def rpl_353(self, message: Message) -> None:
        """NAMES."""
        users = message.split_message[2:]
        channel = message.split_message[1]
        for nick in users:
            nickname, username, userhost = await self._userhost_from_names(
                nick)
            nickname, chan_mode, userhost = await self._chanmodes_from_names(
                nickname, userhost)
            if userhost:
                await self.track_users_userhost(userhost)
                if chan_mode != '+':
                    self.users[nickname].channel_modes[channel] = chan_mode
                if channel not in self.users[nickname].channels:
                    self.users[nickname].channels.append(channel)
            else:
                user = User(nickname, self)
                if chan_mode != '+':
                    user.channel_modes[channel] = chan_mode
                user.channels.append(channel)
                self.users[nickname] = user

    async def rpl_311(self, message: Message) -> None:
        nickname = message.split_message[0]
        username = message.split_message[1]
        userhost = f'{nickname}!{username}@{message.split_message[2]}'
        await self.track_users_userhost(userhost)
        realname = ' '.join(message.split_message[4:])
        self.users[nickname].realname = realname

    async def rpl_319(self, message: Message) -> None:
        """whois channels"""
        nickname = message.split_message[0]
        channel_modes, channels = await self._chanmodes_from_chans(
            message.split_message[1:])
        self.users[nickname].channel_modes = channel_modes
        self.users[nickname].channels = channels

    async def rpl_307(self, message: Message) -> None:
        nickname = message.split_message[0]
        if message.message == f'{nickname} has identified for this nick':
            self.users[nickname].identified = True

    async def rpl_318(self, message: Message) -> None:
        nickname = message.split_message[0]
        self.users[nickname].whoised = True
        print(self.users[nickname])

    async def rpl_333(self, message: Message) -> None:
        userhost = message.split_message[1]
        await self.track_users_userhost(userhost)
        channel = message.split_message[0]
        nickname = userhost.split('!')[0]
        self.users[nickname].channels.append(channel)

    async def rpl_376(self, message: Message) -> None:
        channels = self.server_config.channels
        if channels:
            asyncio.create_task(self.send_join(channels))
        else:
            print('No channels to join.')

    async def rpl_PART(self, message: Message) -> None:
        userhost = message.sent_by
        await self.track_users_userhost(userhost)
        nickname = userhost.split('!')[0]
        channel = message.target
        msg = message.message
        self.users[nickname].part_message[channel] = msg
        self.users[nickname].channels.remove(channel)

    async def rpl_QUIT(self, message: Message) -> None:
        userhost = message.sent_by
        await self.track_users_userhost(userhost)
        nickname = userhost.split('!')[0]
        msg = message.message
        self.users[nickname].quit_message = msg
        self.users[nickname].whoised = False

    async def rpl_JOIN(self, message: Message) -> None:
        userhost = message.sent_by
        await self.track_users_userhost(userhost)
        nickname = userhost.split('!')[0]
        channel = message.target
        self.users[nickname].channels.append(channel)

    async def rpl_NOTICE(self, message: Message) -> None:
        userhost = message.sent_by
        await self.track_users_userhost(userhost)
        nickname = userhost.split('!')[0]
        if nickname in self.users:
            user = self.users[nickname]
            user.last_message = message.raw_message

    async def check_admins(self, user: User, target: str) -> None:
        user.global_admin = user.userhost in self.server_config.admins
        db.add_column(self.db, 'channels', 'admins')
        admins = db.get_cell(self.db, 'channels', 'admins', 'channel', target)
        if admins:
            nadmins: Optional[str] = admins[0][0]
            if nadmins:
                if user.userhost in nadmins.split():
                    user.chan_admin = True
                else:
                    user.chan_admin = False

    async def check_ignored(self, user: User, target: str) -> None:
        user.global_ignored = user.userhost in self.server_config.ignored
        db.add_column(self.db, 'channels', 'ignored')
        ignores = db.get_cell(self.db, 'channels', 'ignored', 'channel',
                              target)
        if ignores:
            nignores: Optional[str] = ignores[0][0]
            if nignores:
                if user.userhost in nignores:
                    user.chan_ignored[target] = True
        user.chan_ignored[target] = False

    async def _run_commands(self, privmsg: Message) -> None:
        pass
        #print(privmsg)

    async def _get_prefix(self, target: str) -> str:
        default_prefix = self.server_config.command_prefix
        if not default_prefix:
            default_prefix = '.'
        if target[0] != '#':
            return default_prefix
        db_prefix = db.get_cell(self.db, 'channels', 'commandprefix',
                                'channel', target)
        if not db_prefix:
            prefix = default_prefix
            db.add_channel(self.db, target, prefix)
        else:
            prefix = db_prefix[0][0]
            valid_prefixes = self.full_config.valid_command_prefixes
            if not prefix or prefix not in valid_prefixes:
                prefix = default_prefix
                db.set_cell(self.db, 'channels', 'commandprefix', prefix,
                            'channel', target)
        return prefix

    async def rpl_PRIVMSG(self, message: Message) -> None:
        userhost = message.sent_by
        await self.track_users_userhost(userhost)
        nickname = userhost.split('!')[0]
        self.users[nickname].last_message = message.raw_message
        if not self.users[nickname].whoised:
            self.send_whois(nickname)
        target = message.target
        await self.check_admins(self.users[nickname], target)
        await self.check_ignored(self.users[nickname], target)
        prefix = await self._get_prefix(target)
        print(prefix)
        asyncio.create_task(self._run_commands(message))

    async def _run_input_sieves(self, privmsg) -> None:
        msg = privmsg
        for name, funcs in self.plugins['sieve'].items():
            if name not in self.server_config.disabled and name.endswith(
                    '-input'):
                for func in funcs:
                    msg = await func(self, msg)
        return msg

    async def _run_inits(self) -> None:
        for name, funcs in self.plugins['init'].items():
            if name not in self.server_config.disabled:
                for func in funcs:
                    await func(self)

    async def _run_events(self, privmsg) -> None:
        events = self.plugins['event']
        if privmsg.raw_command in events:
            for func in events[privmsg.raw_command]:
                if func.__name__.lower() not in self.server_config.disabled:
                    asyncio.create_task(func(self, privmsg))
        if '*' in events:
            for func in events['*']:
                if func.__name__.lower() not in self.server_config.disabled:
                    asyncio.create_task(func(self, privmsg))

    async def read_loop(self) -> None:    # message_handler
        # _run_events
        await self._run_inits()
        while True:
            self.plugin_mtimes, self.plugins = plugins.reload(
                self.plugin_dir, self.plugin_mtimes, self.plugins)
            try:
                raw_message = await self.read_line()
                message = Message(self, await self.parse_message(raw_message))
                message = await self._run_input_sieves(message)
                await self._run_events(message)
                if '!' in message.sent_by:
                    nick = message.sent_by.split('!')[0]
                    if nick in self.users.keys():
                        print(self.users[nick])
                if hasattr(self, f'rpl_{message.raw_command}'):
                    rpl_handler = getattr(self, f'rpl_{message.raw_command}')
                    await rpl_handler(message)
            except asyncio.streams.IncompleteReadError:
                if self.server_config.auto_reconnect:
                    await asyncio.sleep(self.server_config.
                                        auto_reconnect_delay)
                    try:
                        await self.connect()
                    except ConnectionResetError:
                        await self.connect()
                    asyncio.create_task(self.authenticate())


class Client():
    """Taigabot Client."""

    async def stop(self, reset: bool = False) -> None:
        """Is used to stop or restart the bot."""
        global restarted
        restarted = reset
        os.kill(os.getpid(), signal.SIGINT)

    # async def message_handler(self, data: 'ParsedRaw') -> None:
    #     """
    #     Is used for running sieves, events and commands if applicable.

    #     Runs sieves before everything, then events or commands,
    #     depending on the information in data.
    #     """
    #     if not self.server_tag:
    #         return

    #     # get prefix before sieves to add channel to db
    #     # if data.target:
    #     #     prefix: str = await self._get_prefix(data.target)
    #     gdisabled: List[Optional[str]]
    #     gdisabled = self.bot.config['servers'][self.server_tag]['disabled']
    #     ndata: Optional['ParsedRaw'] = await self._run_sieves(data, gdisabled)
    #     if not ndata:
    #         return
    #     data = ndata

    #     asyncio.create_task(self._run_events(data, gdisabled))
    #     if data.nickname and data.mask:
    #         if data.nickname in self.users:
    #             asyncio.create_task(
    #                 self._update_user(data.nickname, data.mask))
    #     if not data.command:
    #         return

    #     if data.command[0] != prefix:
    #         return

    #     data.message = data.message.replace(data.command, '').strip()
    #     data.split_message.remove(data.command)
    #     data.command = data.command[1:]
    #     if data.command.lower() in gdisabled:
    #         asyncio.create_task(
    #             self.notice(data.nickname, f'{data.command} is gdisabled.'))
    #         return
    #     asyncio.create_task(self._run_commands(data))

    # async def _update_user(self, user: str, mask: str) -> None:
    #     """
    #     Is used to update the users db information when they speak.

    #     Runs before sieves so ignored users are in the db.
    #     If user not in db, adds them, otherwise update nick,
    #     or mask if needed.
    #     """
    #     if user == self.nickname:
    #         return
    #     conn: Connection = self.bot.dbs[self.server_tag]

    #     db_mask: DBResult = db.get_cell(conn, 'users', 'mask', 'nick', user)
    #     db_nick: DBResult = db.get_cell(conn, 'users', 'nick', 'mask', mask)

    #     if not db_mask or not db_nick:
    #         db.add_user(conn, user, mask)
    #         return
    #     else:
    #         same_mask = (db_mask[0][0] == mask)
    #         same_nick = (db_nick[0][0] == user)
    #         # if mask changed
    #         if not same_mask and same_nick:
    #             db.set_cell(conn, 'users', 'mask', mask, 'nick', user)
    #         # if nick changed
    #         if same_mask and not same_nick:
    #             db.set_cell(conn, 'users', 'nick', user, 'mask', mask)

    # async def _run_events(self, data: 'ParsedRaw',
    #                       gdisabled: List[Optional[str]]) -> None:
    #     """IS used for running all the events if not disabled."""
    #     events: CommandDict = self.bot.plugs['event']
    #     func = CommandFunc
    #     if data.raw_command in events:
    #         for func in events[data.raw_command]:
    #             if func.__name__.lower() not in gdisabled:
    #                 asyncio.create_task(func(self, data))
    #     if '*' in events:
    #         for func in events['*']:
    #             if func.__name__.lower() not in gdisabled:
    #                 asyncio.create_task(func(self, data))

    # async def _run_inits(self, gdisabled: List[Optional[str]]) -> None:
    #     """IS used for running all the events if not disabled."""
    #     inits: CommandDict = self.bot.plugs['init']
    #     for init in inits.values():
    #         for func in init:
    #             if func.__name__.lower() not in gdisabled:
    #                 asyncio.create_task(func(self))

    async def _run_commands(self, data: 'ParsedRaw') -> None:
        """
        Is used for running user commands if not disabled.

        commands are run if user has correct privilages,
        used correct command, and has long enough input.
        """
        commands: CommandDict = self.bot.plugs['command']
        conn: Connection = self.bot.dbs[self.server_tag]

        if data.mask and data.nickname:
            gadmin: bool = await user.is_gadmin(self, data.server, data.mask)
            admin: bool = await user.is_admin(self, conn, data.nickname,
                                              data.mask)
        else:
            return
        if data.command in commands:
            for func in commands[data.command]:
                hook = func.__hook__[1]    # type: ignore
                if hook['gadmin'] and not gadmin:
                    asyncio.create_task(
                        self.notice(data.nickname,
                                    ('You must be a gadmin to use'
                                     ' that command')))
                    return
                if hook['admin'] and not admin and not gadmin:
                    asyncio.create_task(
                        self.notice(data.nickname,
                                    ('You must be an admin to use'
                                     ' that command')))
                    return
                if not len(data.message) and hook['autohelp']:
                    doc: str = ' '.join(cast(str, func.__doc__).split())
                    asyncio.create_task(self.notice(data.nickname, f'{doc}'))
                    return
                asyncio.create_task(func(self, data))

    # async def _run_sieves(self, data: 'ParsedRaw', gdisabled: List[
    #         Optional[str]]) -> Optional['ParsedRaw']:
    #     """
    #     Is used to run the sieves on the input if not disabled.

    #     Sieves filter data, and return None or modified data,
    #     if None bot takes no futher action on the input.
    #     """
    #     plugs: CommandDict = self.bot.plugs['sieve']
    #     for name, func_list in sorted(plugs.items()):
    #         if name not in gdisabled and name.endswith('-input'):
    #             for func in func_list:
    #                 data = await func(self, data)
    #                 if not data:
    #                     return data
    #     return data

    # async def _get_prefix(self, target: str) -> str:
    #     """
    #     Is used to get or set the channel command prefix.

    #     Returns default for private messages.
    #     If channel has prefix set to non valid prefix, set it to default.
    #     """
    #     default_prefix: str
    #     try:
    #         default_prefix = self.bot.config['servers'][self.server_tag].get(
    #             'command_prefix', '.')
    #     except AttributeError:
    #         default_prefix = '.'

    #     conn: Connection = self.bot.dbs[self.server_tag]
    #     prefix: Optional[str]
    #     if target[0] == '#':
    #         db_prefix: DBResult = db.get_cell(
    #             conn, 'channels', 'commandprefix', 'channel', target)
    #         if not db_prefix:
    #             prefix = default_prefix
    #             db.add_channel(conn, target, prefix)
    #         else:
    #             prefix = db_prefix[0][0]
    #             valid_prefixes: Union[str, List[str]] = self.bot.config.get(
    #                 'valid_command_prefixes', '.')
    #             if not prefix or prefix not in valid_prefixes:
    #                 prefix = default_prefix
    #                 db.set_cell(conn, 'channels', 'commandprefix', prefix,
    #                             'channel', target)
    #     else:
    #         prefix = default_prefix
    #     return prefix

    # changing defaults
    # async def join(self, channel: str, password: str = None) -> None:
    #     """Overwrite the join channel funcion to block channels."""
    #     no_join = self.bot.config['servers'][self.server_tag]['no_channels']
    #     if ',' in channel:
    #         chans = channel.split(',')
    #         for chan in no_join:
    #             if chan in chans:
    #                 chans.remove(chan)
    #         if not chans:
    #             return
    #         channel = ','.join(chans)
    #     else:
    #         for chan in no_join:
    #             if chan == channel:
    #                 return
    #     await super().join(channel, password)

    # async def on_capability_away_notify_available(self, value: Any) -> False:
    #     """Disable away-notify."""
    #     return False

    # async def on_capability_invite_notify_available(self, value: Any) -> False:
    #     """Disable invite-notify."""
    #     return False

    # async def rawmsg(self, command: str, *args: str, **kwargs: str) -> None:
    #     """
    #     Is called to send data, non-disabled sieves are run first.

    #     self.bot is here because the first thing that happens on
    #     connect is sending messages.
    #     Sieves modify the commands, args, or kwargs, if command comes
    #     back None then output is not sent.
    #     """
    #     print(command, args, kwargs)
    #     global bot
    #     self.bot: 'Bot' = bot
    #     gdisabled: List[Optional[str]] = self.bot.config['servers'][
    #         self.server_tag].get('disabled', [])

    #     sieves: CommandDict = self.bot.plugs['sieve']
    #     for name, func_list in sorted(sieves.items()):
    #         if name not in gdisabled and name.endswith('-output'):
    #             for func in func_list:
    #                 command, args, kwargs = await func(
    #                     self, self.server_tag, command, args, kwargs)
    #                 if not command:
    #                     return
    #     if not command:
    #         return
    #     await super().rawmsg(command, *args, **kwargs)

    # async def on_ctcp_version(self, by: str, target: str,
    #                           contents: List[str]) -> None:
    #     """Is overwriting ctcp version to be handled by the events."""
    #     pass

    # async def on_raw(self, message: Any) -> None:
    #     """Is called on raw commands, starts the message handler."""
    #     await super().on_raw(message)
    #     config.reload(self.bot)
    #     plugins.reload(self.bot)

    #     data: 'ParsedRaw' = ParsedRaw(message._raw,
    #                                   self.server_tag)    # noqa: SF01
    #     asyncio.create_task(self.message_handler(data))

    # async def on_connect(self) -> None:
    #     """
    #     Is called when connection to server is successful.

    #     Identifies with services and joins channels.
    #     """
    #     #identify with nickserv, join channels, run init plugins
    #     # await super().on_connect()
    #     # self.logger.setLevel(10)
    #     # server_conf: Dict[str, Any] = self.bot.config['servers'][
    #     #     self.server_tag]

    #     # passwd: str = server_conf.get('nickserv_password', '')
    #     # nickserv: str = server_conf.get('nickserv_nick', 'nickserv')
    #     # nickserv_command: str = server_conf.get('nickserv_command',
    #     #                                         'IDENTIFY {0}')

    #     # if passwd != '':
    #     #     asyncio.create_task(
    #     #         self.message(nickserv, nickserv_command.format(passwd)))

    #     # try:
    #     #     # for channel in server_conf['channels']:
    #     #     #     self.join(channel)
    #     #     asyncio.create_task(self.join(','.join(server_conf['channels'])))
    #     # except KeyError:
    #     #     print('Warning: No channels to join.')
    #     gdisabled = self.bot.config['servers'][self.server_tag]['disabled']
    #     asyncio.create_task(self._run_inits(gdisabled))

    # were unhandled
    # async def on_raw_479(self, message: Any) -> None:
    #     """Is called on invalid channel name."""
    #     pass

    # async def on_raw_716(self, message: Any) -> None:
    #     """Is called when recieved user is +G."""
    #     pass

    # async def on_raw_379(self, message: Any) -> None:
    #     """Is called when recieved whoismodes."""
    #     pass

    # async def on_raw_378(self, message: Any) -> None:
    #     """Is called when recieved whoishost."""
    #     pass

    # async def on_raw_338(self, message: Any) -> None:
    #     """Is called when recieved whoisactually."""
    #     pass
