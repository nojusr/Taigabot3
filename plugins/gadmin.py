# Global admin commands, this is a core plugin, DO NOT REMOVE.

# Standard Libs
import asyncio
import itertools
import platform
import time
from datetime import datetime
from sqlite3 import OperationalError

# First Party
import psutil
from core import db, hook
from util import botu, messaging, user


@hook.hook('sieve', ['02-parse-destination-input'])
async def parse_destination_sieve(bot, msg):
    """Is used to parse [channel] destination for gadmin commands."""
    if not msg.user:
        return msg
    if not msg.user.global_admin:
        return msg

    if msg.command is not None:
        commands = bot.plugins['command']
        command = msg.command[1:]
        return_cmds = {'join', 'part', 'cycle', 'say', 'me', 'raw'}

        if command in commands and command not in return_cmds:
            for func in commands[command]:
                adminonly = func.__hook__[1]['admin']
                gadminonly = func.__hook__[1]['gadmin']
                if not adminonly and not gadminonly:
                    return msg

                message = msg.split_message
                try:
                    if message[1][0] == '#':
                        msg.target = message[1]
                        msg.split_message = message.remove(msg.target)
                        msg.message = ' '.join(msg.split_message)
                except IndexError:
                    pass
    return msg


@hook.hook('command', ['gdisable', 'genable'], gadmin=True, autohelp=True)
async def g_genable_gdisable(client, data):
    """
    .genable/.gdisable <list/commands/events/sieves> -- Lists, enables or
    disables commands, events and sieves.
    """
    event_vals = list(client.bot.plugs['event'].values())
    events = [func[0].__name__ for func in (event for event in event_vals)]
    commands = list(client.bot.plugs['command'])
    sieves = list(client.bot.plugs['sieve'])
    init = list(client.bot.plugs['init'])

    nodisable = client.bot.config['servers'][data.server]['no_disable']
    gdisabled = client.bot.config['servers'][data.server]['disabled']

    message = data.split_message

    if message[0] == 'list':
        asyncio.create_task(
            botu.cmd_event_sieve_init_lists(client, data, gdisabled, nodisable,
                                            sieves, events, commands, init))
        return

    for plugin in message:
        plugin = plugin.lower().strip()
        if await botu.is_cmd_event_sieve_init(plugin, data, sieves, events,
                                              commands, init):
            asyncio.create_task(
                client.notice(data.nickname,
                              f'{plugin} is not a sieve, command or event.'))
        elif data.command == 'genable':
            asyncio.create_task(
                botu.remove_from_conf(client, data, plugin, gdisabled,
                                      f'Genabling {plugin}.',
                                      f'{plugin} is not gdisabled.'))
        elif data.command == 'gdisable':
            if plugin in nodisable:
                asyncio.create_task(
                    client.notice(data.nickname,
                                  f'You cannot gdisable {plugin}.'))
            else:
                asyncio.create_task(
                    botu.add_to_conf(client, data, plugin, gdisabled,
                                     f'Gdisabling {plugin}.',
                                     f'{plugin} is already gdisabled.'))


@hook.hook('command', ['gadmins'], gadmin=True, autohelp=True)
async def g_gadmins(client, data):
    """
    .gadmins <list/add/del> [user/mask] -- Lists, adds or deletes users or
    masks from gadmins.
    """
    gadmins = client.bot.config['servers'][data.server]['admins']
    message = data.split_message
    if message[0] == 'list':
        asyncio.create_task(
            client.notice(data.nickname, 'gadmins are: ' + ', '.join(gadmins)))
        return
    conn = client.bot.dbs[data.server]
    masks = await user.parse_masks(client, conn, ' '.join(message[1:]))

    for mask in masks:
        if message[0] == 'del':
            asyncio.create_task(
                botu.del_from_conf(client, data, mask, gadmins,
                                   f'Removing {mask} from gadmins.',
                                   f'{mask} is not a gadmin.'))
        elif message[0] == 'add':
            asyncio.create_task(
                botu.add_to_conf(client, data, mask, gadmins,
                                 f'Adding {mask} to gadmins..',
                                 f'{mask} is already a gadmin.'))


@hook.hook('command', ['stop', 'restart'], gadmin=True)
async def g_stop_restart(client, data):
    """.stop/.restart -- Stops or restarts the bot."""
    if data.command == 'stop':
        asyncio.create_task(client.stop())
    else:
        asyncio.create_task(client.stop(reset=True))


@hook.hook('command', ['nick'], gadmin=True, autohelp=True)
async def g_nick(client, data):
    """.nick <nick> -- Changes the bots nick."""
    new_nick = data.split_message
    if len(new_nick) > 1:
        asyncio.create_task(
            client.notice(data.nickname, 'Nicknames cannot contain spaces.'))
        return

    asyncio.create_task(client.set_nickname(new_nick))
    client.bot.config['servers'][data.server]['nick'] = new_nick


@hook.hook('command', ['say', 'me', 'raw'], gadmin=True, autohelp=True)
async def g_say_me_raw(client, data):
    """
    .say/.me/.raw <target/rawcmd> <message> -- Say or action to target or
    execute raw command.
    """
    message = data.split_message
    target = message[0]
    msg = message[1:]
    command = data.command

    if not len(msg) and command != 'raw':
        doc = ' '.join(g_say_me_raw.__doc__.split())
        asyncio.create_task(client.notice(data.nickname, f'{doc}'))
        return

    if command == 'say':
        if target != '#':
            asyncio.create_task(client.message(target, ' '.join(msg)))
        elif asyncio.create_task(client.in_channel(target)):
            asyncio.create_task(client.message(target, ' '.join(msg)))
    elif command == 'me':
        if target != '#':
            messaging.action(client, target, ' '.join(msg))
        elif asyncio.create_task(client.in_channel(target)):
            messaging.action(client, target, ' '.join(message))
    elif command == 'raw':
        asyncio.create_task(
            client.rawmsg(target,
                          data.message.replace(target, '').strip()))


# TODO: handle 473: ['arteries', '#wednesday', 'Cannot join channel (+i)']
@hook.hook('command', ['join', 'part', 'cycle'], gadmin=True)
async def g_join_part_cycle(client, data):
    """
    .join/.part [#channel] --- Joins or part a list of channels or part current
    channel.
    """
    channels = client.bot.config['servers'][data.server]['channels']
    message = [msg.lower() for msg in data.split_message]
    command = data.command
    no_join = client.bot.config['servers'][data.server]['no_channels']

    if message[0] is None:
        message = [data.target]

    for channel in message:
        channel = channel

        channel = channel.lower()
        
        if channel[0] != '#':
            continue

        if command == 'part' or command == 'cycle':
            if channel not in channels:
                asyncio.create_task(
                    client.notice(data.nickname, f'Not in {channel}.'))
            else:
                asyncio.create_task(client.part(channel))
                asyncio.create_task(
                    client.notice(data.nickname, f'Parting {channel}.'))
                channels.remove(channel)
        time.sleep(0.2)
        if command == 'join' or command == 'cycle':
            if channel not in itertools.chain(no_join):
                channels.append(channel)
                asyncio.create_task(client.rawmsg('JOIN', channel))
                asyncio.create_task(
                    client.notice(data.nickname, 
                    f'Trying to join/cycle {channel}.'))
            else:
                asyncio.create_task(
                    client.notice(data.nickname, f'Already in {channel}.'))
                    


async def _list_tables(client, data, conn):
    tables = db.get_table_names(conn)
    asyncio.create_task(
        client.notice(data.nickname,
                      f'Valid tables are: {", ".join(tables)}.'))


async def _list_columns(client, data, conn, table, setting=False, cols=None):
    if not cols:
        columns = db.get_column_names(conn, table)
    else:
        columns = cols

    if client is not None:
        if not setting:
            asyncio.create_task(
                client.notice(
                    data.nickname,
                    f'Valid columns to match are: {", ".join(columns)}.'))
        else:
            asyncio.create_task(
                client.notice(
                    data.nickname,
                    f'Valid columns to set are: {", ".join(columns)}.'))
    return columns


async def _get_match_value(client, data, message):
    try:
        match_value = message[2]
        return match_value
    except IndexError:
        asyncio.create_task(
            client.notice(data.nickname, 'Need a value to match against.'))
        doc = ' '.join(g_set.__doc__.split())
        asyncio.create_task(client.notice(data.nickname, f'{doc}'))
        return None


async def _get_set_column(client, data, conn, message, table, columns):
    try:
        set_column = message[3]
    except IndexError:
        asyncio.create_task(
            _list_columns(
                client, data, conn, table, setting=True, cols=columns))
        set_column = ''
        return
    finally:
        if set_column not in columns and set_column != '':
            asyncio.create_task(
                _list_columns(
                    client, data, conn, table, setting=True, cols=columns))
            return None
        return set_column


@hook.hook('command', ['set'], gadmin=True)
async def g_set(client, data):
    """
    .set <table> <matchcol> <value> <setcol> <value> -- Changes values in the
    database, and lists valid tables and columns when arguments ommited.
    """
    bot = client.bot
    conn = bot.dbs[data.server]

    if not data.message:
        doc = ' '.join(g_set.__doc__.split())
        asyncio.create_task(client.notice(data.nickname, f'{doc}'))
        asyncio.create_task(_list_tables(client, data, conn))
        return

    message = data.split_message
    table = message[0]
    columns = await _list_columns(None, data, conn, table)

    table_exists = db.get_table(conn, table)
    if isinstance(table_exists, OperationalError):
        asyncio.create_task(_list_tables(client, data, conn))
        return
    if len(message) == 1:
        asyncio.create_task(_list_columns(client, data, conn, table))
        return

    match_col = message[1]
    if match_col not in columns:
        asyncio.create_task(_list_columns(client, data, conn, table))
        return

    match_value = await _get_match_value(client, data, message)
    if not match_value:
        return

    row_exists = db.get_cell(conn, table, match_col, match_col, match_value)
    if not row_exists:
        asyncio.create_task(
            client.notice(data.nickname,
                          f'{match_value} is not in that table.'))
        return

    set_column = await _get_set_column(client, data, conn, message, table,
                                       columns)
    if not set_column:
        return

    value = ' '.join(message[4:])
    if not value:
        asyncio.create_task(
            client.notice(data.nickname, 'Need a value to add.'))
    else:
        conn = client.bot.dbs[data.server]
        asyncio.create_task(
            client.notice(data.nickname, f'Setting {set_column} to {value}.'))
        db.set_cell(conn, table, set_column, value, match_col, match_value)


async def _conv_bytes(by, gb=False):
    """Is for converting bytes to mb."""
    mb = by / 1000000
    if gb:
        mb /= 1000
        size = f'{mb:.2f} GB'
    else:
        size = f'{mb:.2f} MB'
    return size


@hook.hook('command', ['system'], gadmin=True)
async def g_system(client, data):
    """.system -- Sends notice with system information."""
    # sensors_temperatures, sensors_fans, boot_time, pids
    hostname = platform.node()
    ops = platform.platform()

    architecture = '-'.join(platform.architecture())
    cpu = platform.machine()
    cpus = psutil.cpu_count()
    cpu_per = psutil.cpu_percent()
    general = (f'Hostname: \x02{hostname}\x02, Operating System: '
               f'\x02{ops}\x02, Architecture: \x02{architecture}\x02, '
               f'CPU: \x02{cpu}\x02, Cores: \x02{cpus}\x02, CPU Percent: '
               f'\x02{cpu_per}\x02')
    asyncio.create_task(client.notice(data.nickname, general))

    mem = psutil.virtual_memory()
    mem_total = await _conv_bytes(mem.total, gb=True)
    mem_used = await _conv_bytes(mem.used, gb=True)
    mem_available = await _conv_bytes(mem.available, gb=True)
    mem_free = await _conv_bytes(mem.free, gb=True)
    mem_per = mem.percent
    memory = (
        f'Total Memory: \x02{mem_total}\x02, Memory Used: \x02'
        f'{mem_used}\x02, Memory Avaiable: \x02{mem_available}\x02, '
        f'Memory Free: \x02{mem_free}\x02, Memory Percent: \x02{mem_per}\x02')
    asyncio.create_task(client.notice(data.nickname, memory))

    swap = psutil.swap_memory()
    swap_total = await _conv_bytes(swap.total, gb=True)
    swap_used = await _conv_bytes(swap.used, gb=True)
    swap_free = await _conv_bytes(swap.free, gb=True)
    swap_per = swap.percent

    proc = psutil.Process()
    with proc.oneshot():
        cwd = proc.cwd()
    duseage = psutil.disk_usage(cwd)
    disk_total = await _conv_bytes(duseage.total, gb=True)
    disk_used = await _conv_bytes(duseage.used, gb=True)
    disk_free = await _conv_bytes(duseage.free, gb=True)
    disk_per = duseage.percent
    disk = (
        f'Total Swap: \x02{swap_total}\x02, Swap Used: \x02{swap_used}\x02, '
        f'Swap Free: \x02{swap_free}\x02, Swap Percent: \x02{swap_per}\x02, '
        f'CWD Disk Total: \x02{disk_total}\x02, CWD Disk Used: \x02'
        f'{disk_used}\x02, CWD Disk Free: \x02{disk_free}\x02, '
        f'CWD Disk Percent: \x02{disk_per}\x02')
    asyncio.create_task(client.notice(data.nickname, disk))

    net = psutil.net_io_counters()
    net_sent = await _conv_bytes(net.bytes_sent, gb=True)
    net_recv = await _conv_bytes(net.bytes_recv, gb=True)
    connections = len(psutil.net_connections())
    last_boot = datetime.fromtimestamp(psutil.boot_time()).strftime(
        '%Y-%m-%d %H:%M:%S')
    total_procs = len(psutil.pids())
    netboot = (
        f'Network Data Sent: \x02{net_sent}\x02, Network Data Recieved:'
        f' \x02{net_recv}\x02, Total Connections: \x02{connections}\x02, '
        f'Booted: \x02{last_boot}\x02, Total Processes: \x02{total_procs}\x02')
    asyncio.create_task(client.notice(data.nickname, netboot))


@hook.hook('command', ['bot'], gadmin=True)
async def g_binfo(client, data):
    """.memory -- Shows the current memory usage."""
    proc = psutil.Process()
    with proc.oneshot():
        pid = proc.pid
        cmdline = proc.cmdline()
        cwd = proc.cwd()
        username = proc.username()

        mem = proc.memory_full_info()
        rss = await _conv_bytes(mem.rss)
        vms = await _conv_bytes(mem.vms)
        heap = await _conv_bytes(mem.data)
        stack = await _conv_bytes(mem.stack)
        memper = proc.memory_percent()
        counter = proc.io_counters()
        read = await _conv_bytes(counter.read_count)
        write = await _conv_bytes(counter.write_count)
        files = len(proc.open_files())

        connections = len(proc.connections())
        percent = proc.cpu_percent()
        threads = proc.num_threads()
        nice = proc.nice()
        aff = proc.cpu_affinity()
        num = proc.cpu_num()

    general = (f'Username: \x02{username}\x02, PID: \x02{pid}\x02, cmdline: '
               f'\x02{" ".join(cmdline)}\x02, cwd: \x02{cwd}\x02')
    asyncio.create_task(client.notice(data.nickname, general))
    mem = (f'Real Memory: \x02{rss}\x02, Allocated Memory: \x02{vms}\x02, '
           f'Stack Size: \x02{stack}\x02, Heap Size: \x02{heap}\x02, '
           f'Memory Percent: \x02{memper:.2f}\x02')
    asyncio.create_task(client.notice(data.nickname, mem))
    disk = (
        f'Total Disk Read: \x02{read}\x02, Total Disk Write: \x02{write}\x02, '
        f'Open Files: \x02{files}\x02, Open Net Connections: '
        f'\x02{connections}\x02')
    asyncio.create_task(client.notice(data.nickname, disk))
    aff = ' '.join([str(cpu) for cpu in aff])
    cpu = (f'Bot CPU Percent: \x02{percent}\x02, Used Threads: '
           f'\x02{threads}\x02, Niceness: \x02{nice}\x02, '
           f'CPU Affinity: \x02{aff}\x02, Current Core: \x02{num}\x02')
    asyncio.create_task(client.notice(data.nickname, cpu))


@hook.hook('command', ['ctcp'], gadmin=True, autohelp=True)
async def g_ctcp(client, data):
    """
    .ctcp <target> <command> [message] -- Sends CTCP command to the target,
     with optional message.
    """
    message = data.split_message
    if len(message) <= 1:
        doc = ' '.join(g_ctcp.__doc__.split())
        asyncio.create_task(client.notice(data.nickname, f'{doc}'))
        return
    if len(message) == 2:
        print(message[0], message[1], '')
        asyncio.create_task(client.ctcp(message[0], message[1], ''))
    elif len(message) == 3:
        msg = ' '.join(message[2:])
        asyncio.create_task(client.ctcp(message[0], message[1], msg))
    else:
        doc = ' '.join(g_ctcp.__doc__.split())
        asyncio.create_task(client.notice(data.nickname, f'{doc}'))
        return


@hook.hook('command', ['dbcache'], gadmin=True)
async def dbcache(client, data):
    """
    .dbcache -- Lists all the get caches for the db, order is hits,
    misses, currsize.
    """
    cell = db.get_cell.cache_info()
    cell = f'{cell.hits}, {cell.misses}, {cell.currsize}'
    row = db.get_row.cache_info()
    row = f'{row.hits}, {row.misses}, {row.currsize}'
    row = db.get_row.cache_info()
    row = f'{row.hits}, {row.misses}, {row.currsize}'
    column = db.get_column.cache_info()
    column = f'{column.hits}, {column.misses}, {column.currsize}'
    column_names = db.get_column_names.cache_info()
    column_names = (f'{column_names.hits}, {column_names.misses}, '
                    f'{column_names.currsize}')
    table = db.get_table.cache_info()
    table = f'{table.hits}, {table.misses}, {table.currsize}'
    table_names = db.get_table_names.cache_info()
    table_names = (f'{table_names.hits}, {table_names.misses}, '
                   f'{table_names.currsize}')
    add_column = db.add_column.cache_info()
    add_column = (f'{add_column.hits}, {add_column.misses}, '
                  f'{add_column.currsize}')

    message = (f'Cell: \x02{cell}\x02, Row: \x02{row}\x02 Columns: '
               f'\x02{column}\x02, Column Names: \x02{column_names}\x02, '
               f'Tables: \x02{table}\x02, Table Names: \x02{table_names}\x02, '
               f'Add Column: \x02{add_column}\x02')
    asyncio.create_task(client.notice(data.nickname, message))
