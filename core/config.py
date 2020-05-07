# Load and interface with config file.

# Standard Libs
import json
from typing import Any, Dict, Optional, Union


def save(bot: Any) -> None:
    """Is used to save the specified config file."""
    json.dump(bot.config, bot.config_file.open('w'), indent=2)
    return None


def load(bot: Any) -> Union[Exception, Dict[str, Any]]:
    """Is used to load the specified config file, use reload."""
    return json.load(bot.config_file.open('r'))


def reload(bot: Any) -> Optional[Exception]:
    """Is used to load/reload the config file."""
    new_mtime: float = bot.config_file.stat().st_mtime
    try:
        if bot.config_mtime != new_mtime:
            if bot.config_mtime != 0.0:
                print('<<< Config Reloaded')
            bot.config_mtime = new_mtime
            bot.config = load(bot)
    except KeyError as e:
        return e
    return None
