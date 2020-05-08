# File for loading and reloading plugin files.

# Standard Libs
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

namespace: Dict[str, Any] = {}
GenericPluginFunc = Callable[[Any, Any], Any]
Plugins = Dict[str, List[GenericPluginFunc]]


def _compile_plugins(plugin: Path, reloading: bool) -> Optional[Exception]:
    """Is for compiling the plugins into the namespace variable."""
    try:
        global namespace
        eval(compile(plugin.open('U').read(), plugin, 'exec'), namespace)
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


def load(plugin: Path,
         old_plugins: Dict[str, Dict[str, Callable]],
         reloading: bool = False) -> Dict[str, Any]:
    """
    Is used to load functions from plugin file, use reload.

    Compiles the plugin file into the namespace dict, then
    loop over the namespace sorting the functions into plugs
    dict based on .__hook__ values(sieve, event, command).
    Returns the exception if one occured while compiling the plugin.
    """
    comp: Optional[Exception] = _compile_plugins(plugin, reloading)
    if comp:
        return comp

    global namespace
    plugins: Plugins = old_plugins
    for function in list(namespace.values()):
        try:
            hook = function.__hook__
            for hook_name in cast(str, hook[1]['name']):
                new_plugins = old_plugins[hook[0]]
                try:
                    _add_replace(new_plugins, function, hook_name)
                except KeyError:
                    new_plugins[hook_name] = [function]
                plugins[hook[0]] = new_plugins
        except AttributeError:
            pass
    return plugins


def reload(plugin_dir: Path, plugin_mtimes: Dict[Path, float],
           old_plugins: Dict[str, Dict[str, Callable]]) -> Optional[Exception]:
    """
    Is used to load, or reload plugins, use instead of load.

    If a plugin has not been loaded before, get modify times, and load it.
    Otherwise if the modify time has changed on a loaded plugin reload the
    plugin and change the modify time.
    """
    plugin_files = set(plugin_dir.glob('*.py'))
    mtimes: Dict[str, Dict[str, float]] = plugin_mtimes
    for plug in plugin_files:
        new_mtime = plug.stat().st_mtime
        plugin_mtime = float
        try:
            plugin_mtime = mtimes[plug]
        except KeyError:
            plugin_mtime = mtimes[plug] = 0.0

        if plugin_mtime == 0.0:
            mtimes[plug] = new_mtime
            plugins = load(plug, old_plugins)
        elif plugin_mtime < new_mtime:
            print(f'<<< RELOADING: {plug}')
            mtimes[plug] = new_mtime
            plugins = load(plug, old_plugins, reloading=True)
        else:
            plugins = old_plugins
    return mtimes, plugins
