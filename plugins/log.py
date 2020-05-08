# Event for logging input.


# Standard Libs
import time
from pathlib import Path

# First Party
from core import hook
from util import user


@hook.hook('event', ['*'])
async def logger(bot, msg):
    """Is for ignoring messages from globally or channel ignored users."""
    nolog = bot.server_config.no_log
    conn = bot.db
    server = bot.server_config.server

    if msg.sent_by is not None:
        host = await user.get_mask(bot, conn, msg.sent_by)
    else:
        host = msg.sent_by

    command = msg.raw_command
    message = msg.message
    target = msg.target
    timestamp = time.strftime('%H:%M:%S')
    output = (f'<{timestamp}> <{server}> <{command}> <{host}> <{target}> '
              f'{message}')
    log_dir = Path(
        bot.full_config.log_dir).resolve() / server / time.strftime('%Y')
    raw_log_dir = log_dir / 'raw'

    if not raw_log_dir.exists():
        raw_log_dir.mkdir(parents=True)

    logfile = time.strftime('%m-%d.log')

    join_msg = ' '.join(msg.raw_message[:-1]) + ' '.join(msg.raw_message[-1])
    with (raw_log_dir / logfile).open('a') as f:
        f.write(f'[{timestamp}] {join_msg}\n')
        f.close()

    if not msg.target:
        return

    log_dir = log_dir / msg.target
    if msg.target not in nolog:
        if not log_dir.exists():
            log_dir.mkdir(parents=True)
        with (log_dir / logfile).open('a') as f:
            f.write(timestamp + join_msg + '\n')
            f.close()
    print(output)
