# Hooks for commands, events, sieves and exception catching.

import functools
from typing import Callable, Dict, List, TypeVar, Union

CommandFunc = TypeVar('CommandFunc')
Wrapper = Callable[[CommandFunc], CommandFunc]
WrapperArgs = Dict[str, Union[List[str], bool]]


def hook(
        hook_type: str,
        arg: List[str],
        admin: bool = False,
        gadmin: bool = False,
        autohelp: bool = False) -> Wrapper:
    """Is used for command, event, and sieve hooks."""
    args: WrapperArgs = {}

    def decorator(func):

        @functools.wraps(func)
        def hook_wrapper(*args, **kwargs) -> CommandFunc:
            return func(*args, **kwargs)

        hook_wrapper.__hook__ = [hook_type, args]
        return hook_wrapper

    args['name'] = arg
    args['admin'] = admin
    args['gadmin'] = gadmin
    args['autohelp'] = autohelp
    return decorator
