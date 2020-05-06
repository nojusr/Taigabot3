# Event for logging input.


# Standard Libs
import time

# First Party
from core import hook
from util import user


@hook.hook('event', ['*'])
async def logger(client, data):
    """Is for ignoring messages from globally or channel ignored users."""
    bot = client.bot
    nolog = client.bot.config['servers'][data.server]['no_log']
    conn = client.bot.dbs[data.server]
    server = client.bot.config['servers'][data.server]['server']

    if data.nickname is not None:
        host = await user.get_mask(client, conn, data.nickname)
    else:
        host = data.nickname

    command = data.raw_command
    message = data.message
    target = data.target
    timestamp = time.strftime('%H:%M:%S')
    output = (f'<{timestamp}> <{server}> <{command}> <{host}> <{target}> '
              f'{message}')
    log_dir = bot.log_dir / data.server / time.strftime('%Y')
    raw_log_dir = log_dir / 'raw'

    if not raw_log_dir.exists():
        raw_log_dir.mkdir(parents=True)

    logfile = time.strftime('%m-%d.log')

    with (raw_log_dir / logfile).open('a') as f:
        f.write(f'[{timestamp}] {data.raw}\n')
        f.close()

    if not data.target:
        return

    log_dir = log_dir / data.target
    if data.target not in nolog:
        if not log_dir.exists():
            log_dir.mkdir(parents=True)
        with (log_dir / logfile).open('a') as f:
            f.write(timestamp + data.raw + '\n')
            f.close()
    print(output)
