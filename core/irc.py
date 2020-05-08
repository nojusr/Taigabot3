"""An interface for starting an IRC connection, and talking to it."""

# Standard Libs
import asyncio
from asyncio import create_task, open_connection
from base64 import b64encode
from typing import List, Optional, Tuple

# TODO: CNOTICE, CPRIVMSG, NAMESX?, UHNAMES?, WATCH?


class IRC:
    """The main API to IRC used for the bot."""

    def __init__(self, server_config):
        """Init variabless that are mostly used for authenticating and sasl."""
        self.server_config = server_config

    async def create_connection(self, server: str, port: int,
                                ssl: bool) -> None:
        """Create self.reader and self.writer for the server."""
        self.reader, self.writer = await open_connection(
            server, port, ssl=ssl)

    def close_connection(self) -> None:
        """Close the connection for the objects writer."""
        self.writer.close()

    async def send_line(self, message: str) -> None:
        """Send messages to the server with correct line ending."""
        self.writer.write(f'{message}\r\n'.encode('utf-8'))

    async def send_admin(self, server: Optional[str] = None) -> None:
        """Send a ADMIN to the server.

        This gets the admin of the server in RPL_ADMINME and other replies.
        """
        if server:
            await self.send_line(f'ADMIN {server}')
        else:
            await self.send_line('ADMIN')

    async def send_away(self, message: Optional[str] = None) -> None:
        """Send a AWAY to the server.

        This sets your away status to message or clears it.
        """
        if message:
            create_task(self.send_line(f'AWAY :{message}'))
        else:
            create_task(self.send_line('AWAY'))

    async def send_help(self) -> None:
        """Send a HELP to the server.

        Gets the help file of the server.
        """
        create_task(self.send_line('HELP'))

    async def send_info(self, server: Optional[str] = None) -> None:
        """Send a INFO to the server.

        This command gets information describing the server.
        """
        if server:
            create_task(self.send_line(f'INFO {server}'))
        else:
            create_task(self.send_line('INFO'))

    async def send_invite(self, nickname: str, channel: str) -> None:
        """Send a INVITE to the server.

        This command invites a nickname to the channel.
        """
        create_task(self.send_line(f'INVITE {nickname} {channel}'))

    async def send_ison(self, nicknames: List[str]) -> None:
        """Send a ISON to the server.

        This command sees if the nicknames is on the channel.
        """
        create_task(self.send_line(f'ISON {" ".join(nicknames)}'))

    async def send_join(self, channels: List[str]) -> None:
        """Send a JOIN to the server with a list of channels/keys.

        This joins the given channels, with key support.
        Channels with a key should be in the format '#channel key' in the list.
        """
        chans_with_keys = [
            channels.pop(channels.index(chan)).split()
            for chan in channels.copy()
            if ' ' in chan
        ]
        if chans_with_keys:
            channels = [chan[0] for chan in chans_with_keys] + channels
            chans_keys = [chan[1] for chan in chans_with_keys]
            create_task(
                self.send_line(
                    f'JOIN {",".join(channels)} {",".join(chans_keys)}'))
        else:
            create_task(self.send_line(f'JOIN {",".join(channels)}'))

    async def send_kick(self,
                        channel: str,
                        nickname: str,
                        reason: Optional[str] = None) -> None:
        """Send a KICK to the server.

        This command kicks users from the channel, with or without reason.
        """
        if reason:
            create_task(
                self.send_line(f'KICK {channel} {nickname} :{reason}'))
        else:
            create_task(self.send_line(f'KICK {channel} {nickname}'))

    async def send_kickban(self,
                           channel: str,
                           nickname: str,
                           reason: Optional[str] = None) -> None:
        """Send KICK to the server and a MODE ban.

        Kicks and bans the user from the channel.
        """
        create_task(self.send_ban(channel, nickname))
        if '!' in nickname:
            nickname = nickname.split('!')[0]
        create_task(self.send_kick(channel, nickname, reason))

    async def send_ban(self, channel: str, nickname: str) -> None:
        """Send a MODE to ban to the server.

        Ban a user from a channel.
        """
        create_task(self.send_mode(channel, '+b', nickname))

    async def send_unban(self, channel: str, nickname: str) -> None:
        """Send a MODE to unban to the server.

        Unban a user from a channel.
        """
        create_task(self.send_mode(channel, '-b', nickname))

    async def send_knock(self, channel: str,
                         message: Optional[str] = None) -> None:
        """Send a KNOCK to the server.

        This command requests invites to a channel, with optional message.
        """
        if message:
            create_task(self.send_line(f'KNOCK {channel} :{message}'))
        else:
            create_task(self.send_line(f'KNOCK {channel}'))

    async def send_list(self, channels: Optional[List[str]] = None) -> None:
        """Send LIST to list of channels to list users, or to server.

        This gets the list of users in channels, or channels on server in
        various numerics.
        This command also takes conds to filter LIST which are listed in
        ISUPPORT.
        To use cond the channel must be in the format '#channel cond' in the
        list.
        To LIST the server with a cond, have one channel in channels list with
        just a cond and no channel.
        """
        if channels:
            chans_with_conds = [
                channels.pop(channels.index(chan)).split()
                for chan in channels.copy()
                if ' ' in chan
            ]
            if chans_with_conds:
                channels = [chan[0] for chan in chans_with_conds] + channels
                chans_conds = [chan[1] for chan in chans_with_conds]
            if chans_conds:
                create_task(
                    self.send_line(
                        f'LIST {",".join(channels)} {",".join(chans_conds)}'))
            else:
                create_task(self.send_line(f'LIST {",".join(channels)}'))
        else:
            create_task(self.send_line('LIST'))

    async def send_mode(self,
                        target: str,
                        mode: Optional[str] = None,
                        args: Optional[List[str]] = None) -> None:
        """Send a MODE to the target.

        This is used for setting channel/user modes, and getting modes of users
        and channels.
        """
        if mode:
            if args:
                create_task(
                    self.send_line(f'MODE {target} {mode} {" ".join(args)}'))
            else:
                create_task(self.send_line(f'MODE {target} {mode}'))
        else:
            create_task(self.send_line(f'MODE {target}'))

    async def send_motd(self, server: Optional[str] = None) -> None:
        """Send a MOTD to the server.

        This gets the MOTD in the server in various numerics.
        """
        if server:
            create_task(self.send_line(f'MOTD {server}'))
        else:
            create_task(self.send_line('MOTD'))

    async def send_names(self, channels: List[str],
                         server: Optional[str]) -> None:
        """Send NAMES to list of channels.

        This gets the list of users in channels with privilages in various
        numerics.
        """
        if server:
            create_task(
                self.send_line(f'NAMES {",".join(channels)} {server}'))
        else:
            create_task(self.send_line(f'NAMES {",".join(channels)}'))

    async def send_nick(self, nickname: str) -> None:
        """Send a NICK to the server.

        This is sets, or requests a new nickname from the server.
        """
        create_task(self.send_line(f'NICK :{nickname}'))

    async def send_notice(self, targets: List[str], message: str) -> None:
        """Send a NOTICE to a list of targets.

        This is for sending notice messages to channels or users.
        """
        create_task(self.send_line(f'NOTICE {",".join(targets)} :{message}'))

    async def send_part(self,
                        channels: List[str],
                        reason: Optional[str] = None) -> None:
        """Send a PART to the list of channels, with or without reason.

        This parts the given channels, with optional reason
        """
        if reason:
            create_task(
                self.send_line(f'PART {",".join(channels)} :{reason}'))
        else:
            create_task(self.send_line(f'PART {",".join(channels)}'))

    async def send_pass(self, server_password: str) -> None:
        """Send a PASS to the server.

        This sends a server password to the server to join.
        """
        create_task(self.send_line(f'PASS :{server_password}'))

    async def send_ping(self, server: str) -> None:
        """Send a PING to the server.

        This sends a ping to the server to test connection.
        """
        create_task(self.send_line(f'PING {server}'))

    async def send_pong(self, arg: str) -> None:
        """Send a PONG reply to the server.

        This sends a pong to the server with whatever arguments.
        """
        create_task(self.send_line(f'PONG :{arg}'))

    async def send_privmsg(self, targets: List[str], message: str) -> None:
        """Send a PRIVMSG to a list of targets.

        This is for sending messages to channels or users.
        """
        create_task(
            self.send_line(f'(PRIVMSG {",".join(targets)} :{message}'))

    async def send_quit(self, reason: Optional[str] = None) -> None:
        """Send a QUIT to the server, with or without reason.

        This quits the server, with optional reason.
        """
        if reason:
            create_task(self.send_line(f'QUIT :{reason}'))
        else:
            create_task(self.send_line('QUIT'))

    async def send_rules(self) -> None:
        """Send a RULES to the server.

        This gets the rules of the server.
        """
        create_task(self.send_line('RULES'))

    async def send_stats(self, query: str,
                         server: Optional[str] = None) -> None:
        """Send STATS with a query to the server.

        This is for gathering statistics about the server.
        """
        if server:
            create_task(self.send_line(f'STATS {query} {server}'))
        else:
            create_task(self.send_line(f'STATS {query}'))

    async def send_time(self, server: Optional[str] = None) -> None:
        """Send a TIME to the server.

        This requests the local time of the server.
        """
        if server:
            create_task(self.send_line(f'TIME {server}'))
        else:
            create_task(self.send_line('TIME'))

    async def send_topic(self, channel: str,
                         topic: Optional[str] = None) -> None:
        """Send TOPIC to channel channel, with optional arg to change it."""
        if topic:
            create_task(self.send_line(f'TOPIC {channel} :{topic}'))
        else:
            create_task(self.send_line(f'TOPIC {channel}'))

    async def send_user(self, username: str, realname: str) -> None:
        """Send USER to server with username and realname.

        This is for setting your username and realname
        """
        create_task(self.send_line(f'USER {username} * 0 :{realname}'))

    async def send_userhost(self, targets: List[str]) -> None:
        """Send a USERHOST to the server.

        This is for getting information about users.
        """
        if len(targets) <= 5:
            create_task(self.send_line(f'USERHOST {" ".join(targets)}'))

    async def send_users(self, username: str, realname: str) -> None:
        """Send USER to server with username and realname.

        This is for setting your username and realname
        """
        create_task(self.send_line(f'USER {username} * 0 :{realname}'))

    async def send_version(self,
                           target: Optional[str] = None,
                           server: Optional[str] = None) -> None:
        """Send a VERSION to the target, or to the server.

        This gets the VERSION reply from the user or the server in RPL_VERSION.
        """
        if target:
            if server:
                create_task(self.send_line(f'VERSION {server} {target}'))
            else:
                create_task(self.send_line(f'VERSION {target}'))
        else:
            create_task(self.send_line('VERSION'))

    async def send_who(self, nickname: str) -> None:
        """Send WHO to server.

        This is for listing users who match the nickname.
        """
        create_task(self.send_line(f'WHO {nickname}'))

    def send_whois(self, nickname: str) -> None:
        """Send WHOIS to server.

        This is for listing users information.
        This is not async to be used in the User dataclass.
        """
        self.writer.write(f'WHOIS {nickname}\r\n'.encode('utf-8'))

    async def send_whowas(self, nickname: str,
                          count: Optional[str] = None) -> None:
        """Send WHOIS to server.

        This is for listing users information.
        """
        if count:
            create_task(self.send_line(f'WHOWAS {nickname} {count}'))
        else:
            create_task(self.send_line(f'WHOWAS {nickname}'))

    async def send_cap(self, command: str,
                       parameters: Optional[str] = None) -> None:
        """Send a CAP to the server.

        This is used to send any of the CAP subcommands to the server.
        """
        if parameters:
            create_task(self.send_line(f'CAP {command} :{parameters}'))
        else:
            create_task(self.send_line(f'CAP {command}'))

    async def send_authenticate(self, parameters: str) -> None:
        """Send a AUTHENTICATE to the server.

        This is for sending the authentication command used for sasl.
        """
        create_task(self.send_line(f'AUTHENTICATE {parameters}'))

    async def authenticate(self) -> None:
        """Send various messages for authenticating and joining with the server.

        This will send the server password if set, set the users nickname and
        user/real names, and start the capability negotiation.
        """
        if self.server_config.server_password:
            create_task(self.send_pass(self.server_config.server_password))
        create_task(self.send_nick(self.server_config.nickname))
        create_task(
            self.send_user(self.server_config.username,
                           self.server_config.realname))
        if self.server_config.capabilities:
            create_task(self.send_cap('LS', '302'))

    async def cap_ls_reply(self,
                           reply: Tuple[str, str, str, List[str]]) -> None:
        """Handle the reply from a CAP LS.

        This will see what capabilities the server has, and request what we
        want if the server supports it.
        """
        capabilities = reply[3][2].split()
        request = [
            cap for cap in self.server_config.capabilities
            if cap in capabilities
        ]
        if request:
            create_task(self.send_cap('REQ', ' '.join(request)))

    async def cap_ack_reply(self,
                            reply: Tuple[str, str, str, List[str]]) -> None:
        """Handle the reply from a CAP REQ.

        If we have requested sasl it will continue the authentication,
        otherwise we will end the capability negotiation/authentication.
        """
        acknowledged = reply[3][2].split()
        if 'sasl' in acknowledged and self.server_config.sasl_method:
            create_task(
                self.send_authenticate(self.server_config.sasl_method.upper()))
        else:
            create_task(self.send_cap('END'))

    async def authenticate_plus_reply(self) -> None:
        """Handle the reply from an AUTHENTICATE method request.

        This will send the replies for either PLAIN sasl or EXTERNAL sasl to
        finish the authentication.
        """
        method = self.server_config.sasl_method.upper()
        if method == 'PLAIN' and (self.server_config.nick_password and
                                  self.server_config.nickname):
            password = (
                f'{self.server_config.nickname}\0{self.server_config.nickname}'
                f'\0{self.server_config.nick_password}').encode('utf-8')
            create_task(
                self.send_authenticate(b64encode(password).decode('utf-8')))
        elif method == 'EXTERNAL':
            create_task(self.send_authenticate('*'))

    async def parse_message(self, inp: str) -> Tuple[str, str, str, List[str]]:
        """Parse IRC messages into tags, prefix, command and args."""
        # TODO: Parse tags into dict
        tags: str = ''
        if inp[0] == '@':
            tags, inp = inp[1:].split(' ', 1)
        prefix: str = ''
        if inp[0] == ':':
            prefix, inp = inp[1:].split(' ', 1)

        parameters: List[str]
        if inp.find(' :') != -1:
            inp, trailing = inp.split(' :', 1)
            parameters = inp.split()
            parameters.append(trailing)
        else:
            parameters = inp.split()
        command: str = parameters.pop(0)
        return tags, prefix, command, parameters

    async def read_line(self) -> str:
        """Read a line from the server, parse it, and return it.

        This is also used for handling the replies needed for the capability
        negotiation, sasl, and PINGS so must be used in a loop.
        """
        raw_message = (await
                       self.reader.readuntil(b'\r\n')).decode('utf-8')[:-2]
        message = await self.parse_message(raw_message)
        print(raw_message)
        if message[2] == 'PING':
            create_task(self.send_pong(' '.join(message[3][0:])))
        elif message[2] == 'CAP':
            if message[3][1] in {'LS', 'LIST'}:
                create_task(self.cap_ls_reply(message))
            elif message[3][1] == 'ACK':
                create_task(self.cap_ack_reply(message))
        elif message[2] == 'AUTHENTICATE':
            if self.server_config.sasl_method:
                if message[3][0] == '+':
                    create_task(self.authenticate_plus_reply())
        elif message[2] == '903':
            create_task(self.send_cap('END'))
        return raw_message
