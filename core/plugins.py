# File for loading and reloading plugin files.

# Standard Libs
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, cast

namespace: Dict[str, Any] = {}
GenericPluginFunc = Callable[[Any, Any], Any]
Plugins = Dict[str, List[GenericPluginFunc]]


def _compile_plugins(plug: Path, reloading: bool) -> Optional[Exception]:
    """Is for compiling the plugins into the namespace variable."""
    try:
        global namespace
        eval(compile(plug.open('U').read(), plug, 'exec'), namespace)
    except Exception as e:
        print(f'Error Loading plugin: {type(e).__name__} {e}.')
        if reloading:
            print('Continuing use of old plugin.')
        return e
    return None


def _add_replace(plugins: Plugins, function: GenericPluginFunc,
                 hook_name: str) -> None:
    """Is for adding or replacing plugins in the Plugins dict."""
    for func in plugins[hook_name]:
        if func.__name__ == function.__name__:
            plugins[hook_name].remove(func)
            plugins[hook_name].append(function)
        elif function not in plugins[hook_name]:
            plugins[hook_name].append(function)


def load(bot: Any, plug: Path, reloading: bool = False) -> Optional[Exception]:
    """
    Is used to load functions from plugin file, use reload.

    Compiles the plugin file into the namespace dict, then
    loop over the namespace sorting the functions into bot.plugs
    dict based on .__hook__ values(sieve, event, command).
    Returns the exception if one occured while compiling the plugin.
    """
    c: Optional[Exception] = _compile_plugins(plug, reloading)
    if c:
        return c

    global namespace
    for function in list(namespace.values()):
        try:
            hook: List[Union[Plugins, Dict[str, List[str]]]]
            hook = function.__hook__
            for hook_name in cast(str, hook[1]['name']):
                plugins: Plugins = bot.plugs[hook[0]]
                try:
                    _add_replace(plugins, function, hook_name)
                except KeyError:
                    plugins[hook_name] = [function]
        except AttributeError:
            pass
    return None


def reload(bot: Any) -> Optional[Exception]:
    """
    Is used to load, or reload plugins, use instead of load.

    If a plugin has not been loaded before, get modify times, and load it.
    Otherwise if the modify time has changed on a loaded plugin reload the
    plugin and change the modify time.
    """
    bot.plugin_files = set(bot.plugin_dir.glob('*.py'))
    mtimes: Dict[str, Dict[str, float]] = bot.plugin_mtimes
    for plug in bot.plugin_files:
        new_mtime = plug.stat().st_mtime
        plugin_mtime: Dict[str, float]
        try:
            plugin_mtime = mtimes[plug]
        except KeyError:
            plugin_mtime = mtimes[plug] = {}

        if not plugin_mtime:
            mtimes[plug] = new_mtime
            return load(bot, plug)
        elif plugin_mtime != new_mtime:
            print(f'<<< RELOADING: {plug}')
            mtimes[plug] = new_mtime
            return load(bot, plug, reloading=True)
    return None
