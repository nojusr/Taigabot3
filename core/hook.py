# Hooks for commands, events, sieves and exception catching.

import functools
from typing import Any, Callable, Dict, List, Union

GenericPluginFunc = Callable[..., Any]
GenericWrapperFunc = Callable[[GenericPluginFunc], GenericPluginFunc]


def hook(hook_type: str,
         arg: List[str],
         admin: bool = False,
         gadmin: bool = False,
         autohelp: bool = False) -> GenericWrapperFunc:
    """Is used for command, event, and sieve hooks."""
    args: Dict[str, Union[List[str], bool]] = {}

    def decorator(func):
        @functools.wraps(func)
        def hook_wrapper(*args, **kwargs) -> GenericPluginFunc:
            return func(*args, **kwargs)

        setattr(hook_wrapper, '__hook__', [hook_type, args])
        return hook_wrapper

    args['name'] = arg
    args['admin'] = admin
    args['gadmin'] = gadmin
    args['autohelp'] = autohelp
    return decorator
