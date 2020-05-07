# Standard Libs
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from sqlite3 import Connection
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# First Party
from core import config, db, plugins

InputSieveList = List[Callable[['Client', 'ParsedRaw'], 'ParsedRaw']]
OutputSieveList = List[
    Callable[['Client', str, str, Tuple[str, ...], Dict[str, str]],
             Tuple[str, Tuple[str, ...], Dict[str, str]]]]
CommandEventFunc = Callable[['Client', 'ParsedRaw'], None]
CommandEventList = List[CommandEventFunc]
FuncUnion = Union[InputSieveList, OutputSieveList, CommandEventList]
AllPlugsDict = Dict[str, FuncUnion]


def parsemsg(s: str) -> Tuple[str, str, List[str]]:
    """Is used to break IRC messages into prefix, command and args."""
    if not s:
        raise ValueError

    prefix: str = ''
    if s[0] == ':':
        prefix, s = s[1:].split(' ', 1)

    args: List[str]
    if s.find(' :') != -1:
        s, trailing = s.split(' :', 1)
        args = s.split()
        args.append(trailing)
    else:
        args = s.split()
    command: str = args.pop(0)
    return prefix, command, args


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
    plugs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
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
        self.db_dir: Path = self.base_dir / 'persist' / 'db'
        self.log_dir: Path = self.base_dir / 'persist' / 'logs'
        self.plugin_dir: Path = self.base_dir / 'plugins'
        self.config_file: Path = self.base_dir / 'config.json'

        config.reload(self)
        self.plugs: AllPlugsDict = {
            'sieve': {},
            'event': {},
            'command': {},
            'init': {}}
        plugins.reload(self)
        for server in self.config['servers']:
            db.connect(self, server)    # populates self.dbs
