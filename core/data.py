# Standard Libs
import copy
import dataclasses
import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path, PosixPath
from sqlite3 import Connection
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union

# First Party
from core import config, db, plugins

CommandFunc = TypeVar('CommandFunc')
PlugsDict = Dict[str, Dict[str, List[CommandFunc]]]
conf: 'Config' = None


def parsemsg(inp: str) -> Tuple[str, str, List[str]]:
    """Is used to break IRC messages into prefix, command and args."""
    prefix: str = ''
    if inp[0] == ':':
        prefix, inp = inp[1:].split(' ', 1)

    args: List[str]
    if inp.find(' :') != -1:
        inp, trailing = inp.split(' :', 1)
        args = inp.split()
        args.append(trailing)
    else:
        args = inp.split()
    command: str = args.pop(0)
    return prefix, command, args


@dataclass
class UsersDB:
    test: str


@dataclass
class ChannelsDB:
    test: str


@dataclass
class DB:
    users: List[UsersDB]
    channels: List[ChannelsDB]


@dataclass
class User:
    nickname: str
    bot: 'Taigabot'
    realname: str = field(default_factory=str)
    username: str = field(default_factory=str)
    username_user_set: bool = field(default=False)
    userhost: str = field(default_factory=str)
    chan_admin: bool = field(default=False)
    global_admin: bool = field(default=False)
    global_ignored: bool = field(default=False)
    chan_ignored: Dict[str, bool] = field(default_factory=dict)
    channels: List[str] = field(default_factory=list)
    channel_modes: Dict[str, str] = field(default_factory=dict)

    identified: bool = field(default=False)
    whoised: bool = field(default=False)
    part_message: Dict[str, str] = field(default_factory=dict)
    quit_message: str = field(default_factory=str)
    last_message: Tuple[str, str, str, List[str]] = field(
        default_factory=tuple)

    # def __getattribute__(self, key: str) -> None:
    #     value = super().__getattribute__(key)
    #     if key == 'userhost' and value == '':
    #         self.bot.send_whois(object.__getattribute__(self, 'nickname'))
    #     value = super().__getattribute__(key)
    #     return value


@dataclass
class Message:
    bot: 'Taigabot'
    raw_message: Tuple[str, str, str, List[str]]
    tags: str = field(default_factory=str)
    sent_by: str = field(default_factory=str)
    raw_command: str = field(default_factory=str)
    args: List[str] = field(default_factory=list)
    user: User = field(default=None)

    target: str = field(default_factory=str)
    message: str = field(default_factory=str)
    split_message: List[str] = field(default_factory=list)
    command: str = field(default_factory=str)

    def __post_init__(self):
        self.tags = self.raw_message[0]
        self.sent_by = self.raw_message[1]
        self.raw_command = self.raw_message[2]
        self.args = self.raw_message[3]
        if '!' in self.sent_by:
            nick = self.sent_by.split('!')[0]
            if nick in self.bot.users.keys():
                self.user = self.bot.users[nick]

        self.target = self.args[0]
        if len(self.args) == 1:
            self.message = self.args[0]
        else:
            self.message = ' '.join(self.args[1:])
        if ' ' in self.message:
            self.split_message = self.message.split()
        else:
            self.split_message = [self.message]
        self.command = self.split_message[0]


@dataclass
class ServerConfig:
    """Dataclass for server configs."""

    raw_config: Dict[str, Any]
    init: bool = field(default=True)
    command_prefix: str = field(default='.')
    nickserv_nick: str = field(default='nickserv')
    nickserv_command: str = field(default='IDENTIFY {0}')
    port: int = field(default=6697)
    ssl: bool = field(default=True)
    auto_reconnect: bool = field(default=True)
    auto_reconnect_delay: int = field(default=20)
    disabled: List[str] = field(default_factory=list)
    no_disable: List[str] = field(default_factory=list)
    no_log: List[str] = field(default_factory=list)
    ignored: List[str] = field(default_factory=list)
    no_ignore: List[str] = field(default_factory=list)
    admins: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    no_channels: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    owner: str = field(default_factory=str)
    nickname: str = field(default_factory=str)
    nickname_password: str = field(default_factory=str)
    username: str = field(default_factory=str)
    realname: str = field(default_factory=str)
    server: str = field(default_factory=str)
    server_password: str = field(default_factory=str)
    sasl_method: str = field(default_factory=str)
    sasl_cert: str = field(default_factory=str)
    sasl_key: str = field(default_factory=str)

    def __post_init__(self):
        """Parse the raw config into the ServerConfig."""
        self.from_json()
        self.init = False

    def __setattr__(self, key, value) -> None:
        """Set object attributes and save to config if needed."""
        if hasattr(self, 'init') and not self.init:
            if value not in self.raw_config.values() and key not in {
                    'init', 'raw_config'
            }:
                global conf
                if conf:
                    conf.save()
        return super().__setattr__(key, value)

    def from_json(self) -> None:
        """Parse the config from json."""
        for key, value in self.raw_config.items():
            if key in self.__dict__.copy().keys():
                setattr(self, key, value)

    def to_json(self) -> Dict[str, Any]:
        """Parse the dataclass to json."""
        conf = copy.deepcopy(self.__dict__)
        conf.pop('init')
        conf.pop('raw_config')
        return json.loads(json.dumps(conf))


@dataclass
class Config:
    """Dataclass for the config, including all servers."""

    config_file: Path
    config_mtime: float = field(default=0.0)
    init: bool = field(default=True)
    db_dir: str = field(default='./Taigabot3/persist/db/')
    log_dir: str = field(default='./Taigabot3/persist/logs/')
    plugin_dir: str = field(default='./Taigabot3/plugins/')
    valid_command_prefixes: List[str] = field(default_factory=list)
    api_keys: Dict[str, str] = field(default_factory=dict)
    servers: Dict[str, ServerConfig] = field(default_factory=dict)
    raw_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Load the config file an parse into dataclasses."""
        self.from_json()
        self.init = False
        global conf
        conf = self

    def __setattr__(self, key, value) -> None:
        """Set object attributes and save to config if needed."""
        if hasattr(self, 'init') and not self.init:
            if value not in self.raw_config.values():
                if key not in {'init'}:
                    self.save()
        return super().__setattr__(key, value)

    def from_json(self) -> None:
        """Parse the config from json."""
        self.raw_config = self.reload()
        for key, value in self.raw_config.items():
            if key in self.__dict__.copy().keys() and key != 'servers':
                setattr(self, key, value)
            elif key == 'servers':
                for key2, value2 in self.raw_config['servers'].items():
                    self.servers[key2] = ServerConfig(value2)

    def to_json(self) -> Dict[str, Any]:
        """Parse the dataclass to json."""
        conf_dict: Dict[str, Any] = copy.deepcopy(self.__dict__)
        for server_name, server_conf in self.servers.items():
            conf_dict['servers'][server_name] = server_conf.to_json()
        for key, value in self.__dict__.items():
            if type(value) == PosixPath:
                conf_dict[key] = str(value)
            if key in {'raw_config', 'init', 'config_file', 'config_mtime'}:
                conf_dict.pop(key)
        return json.loads(json.dumps(conf_dict))

    def save(self) -> None:
        """Save this dataclass as a json file."""
        json.dump(self.to_json(), self.config_file.open('w'), indent=4)

    def reload(self) -> Dict[str, Any]:
        """Load the config and change the mtime.

        Use from_json in loop to update the dataclass.
        """
        new_mtime: float = self.config_file.stat().st_mtime
        if self.config_mtime != new_mtime:
            if self.config_mtime != 0.0:
                print('<<< Config Reloaded')
            conf: Dict[str, Any] = json.load(self.config_file.open('r'))
            self.config_mtime = new_mtime
            return conf
        return self.raw_config


@dataclass
class ParsedRaw:
    """All the information parsed from the raw messages."""

    raw: str
    server: str

    raw_command: str = field(default_factory=str)
    message: str = field(default_factory=str)
    split_message: List[str] = field(default_factory=list)
    command: Optional[str] = field(default_factory=str)
    mask: Optional[str] = field(default_factory=str)
    nickname: Optional[str] = field(default_factory=str)
    username: Optional[str] = field(default_factory=str)
    host: Optional[str] = field(default_factory=str)
    target: Optional[str] = field(default_factory=str)

    def __post_init__(self):
        """Is used to parse all of the raw messages into parts."""
        self.mask: str = ''
        self.nickname: str = ''
        self.username: str = ''
        self.host: str = ''
        self.target: str = ''
        self.command: str = ''
        self.message: str = ''

        prefix, raw_command, args = parsemsg(self.raw)
        self.raw_command: str = raw_command




        if raw_command in {'PING', 'AWAY', 'QUIT'}:
            self.message = ' '.join(args)
        else:
            self.target = args[0]
            self.command = args[0]
            self.message = ' '.join(args)

            if '@' in prefix:
                split_prefix = re.split('!|@', prefix)
                self.message = ' '.join(args[1:])
                self.nickname = split_prefix[0]
                self.username = split_prefix[1]
                self.host = split_prefix[2]
                self.mask = prefix

            if self.raw_command == 'PRIVMSG':
                self.command = args[1]
                if ' ' in self.command and self.command != ' ':
                    self.command = self.command.split()[0]

                if self.target[0] != '#':
                    self.target = self.nickname




        if ' ' in self.message:
            self.split_message = self.message.split()
        else:
            self.split_message = [self.message]






@dataclass()
class Bot:
    """All information used to run the bot."""

    config: Dict[str, Any] = field(default_factory=dict)
    config_mtime: float = 0.0
    plugs: PlugsDict = field(default_factory=dict)
    plugin_mtimes: Dict[str, float] = field(default_factory=dict)

    dbs: Dict[str, Connection] = field(default_factory=dict)
    lock: threading.Lock = threading.Lock()
    clients: List['Client'] = field(default_factory=list)

    base_dir: Path = field(default_factory=Path)
    db_dir: Path = field(default_factory=Path)
    log_dir: Path = field(default_factory=Path)
    plugin_dir: Path = field(default_factory=Path)

    config_file: Path = field(default_factory=Path)
    plugin_files: Set[Path] = field(default_factory=set)

    def __post_init__(self):
        """Is used to initate values for all the above, excluding clients."""
        self.base_dir: Path = Path('.').resolve()
        self.db_dir: Path = self.base_dir / 'Taigabot3' / 'persist' / 'db'
        self.log_dir: Path = self.base_dir / 'Taigabot3' / 'persist' / 'logs'
        self.plugin_dir: Path = self.base_dir / 'Taigabot3' / 'plugins'
        self.config_file: Path = self.base_dir / 'Taigabot3' / 'config.json'

        config.reload(self)
        self.plugs: PlugsDict = {
            'command': {},
            'event': {},
            'init': {},
            'sieve': {}
        }
        plugins.reload(self)
        for server in self.config['servers']:
            db.connect(self, server)    # populates self.dbs
