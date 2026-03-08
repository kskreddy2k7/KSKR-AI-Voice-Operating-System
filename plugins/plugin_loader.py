"""
Plugin Loader
-------------
Dynamically discovers and loads KSKR Voice OS plugins from the ``plugins/``
directory.

Plugin contract
~~~~~~~~~~~~~~~
Every plugin is a Python module (or package) that exposes:

``PLUGIN_NAME``   – str   – human-readable plugin name
``PLUGIN_INTENTS``– list  – list of intent strings this plugin handles
                             (e.g. ``["weather", "forecast"]``)
``handle(command)``       – callable that receives a
                             :class:`~nlp.command_parser.Command` and returns
                             a response string.

Plugins may optionally expose:
``setup()``               – called once when the plugin is loaded.
``teardown()``            – called when the plugin is unloaded.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("plugins", {})
    except Exception as exc:
        logger.warning("PluginLoader: could not load config – %s", exc)
        return {}


class PluginLoader:
    """Discovers and manages plugins at runtime."""

    def __init__(self, plugin_dir: Optional[str] = None) -> None:
        cfg = _load_config()
        _dir = plugin_dir or cfg.get("directory", "plugins")
        self._plugin_dir = Path(_dir)
        self._plugins: Dict[str, Any] = {}   # name → module
        self._intent_map: Dict[str, Any] = {}  # intent → module

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self) -> List[str]:
        """Scan *plugin_dir* and load all valid plugin modules.

        Returns a list of successfully loaded plugin names.
        """
        loaded = []
        if not self._plugin_dir.exists():
            logger.warning("PluginLoader: plugin directory '%s' does not exist.", self._plugin_dir)
            return loaded

        for path in sorted(self._plugin_dir.iterdir()):
            if path.name.startswith("_") or path.name == "plugin_loader.py":
                continue
            if path.is_dir() and (path / "__init__.py").exists():
                module_name = path.name
            elif path.suffix == ".py":
                module_name = path.stem
            else:
                continue

            name = self._load_plugin(path, module_name)
            if name:
                loaded.append(name)

        logger.info("PluginLoader: loaded %d plugin(s): %s", len(loaded), loaded)
        return loaded

    def handle(self, command) -> Optional[str]:
        """Dispatch *command* to the appropriate plugin.

        Returns the plugin's response string, or *None* if no plugin matches.
        """
        intent = command.intent.lower()
        plugin = self._intent_map.get(intent)
        if plugin is None:
            # Try prefix match
            for key, mod in self._intent_map.items():
                if intent.startswith(key) or key.startswith(intent):
                    plugin = mod
                    break

        if plugin is None:
            return None

        try:
            return plugin.handle(command)
        except Exception as exc:
            logger.error(
                "PluginLoader: plugin '%s' raised an error – %s",
                getattr(plugin, "PLUGIN_NAME", "unknown"),
                exc,
            )
            return None

    def list_plugins(self) -> List[str]:
        """Return names of all loaded plugins."""
        return list(self._plugins.keys())

    def unload(self, name: str) -> bool:
        """Unload a plugin by name.  Returns *True* on success."""
        plugin = self._plugins.pop(name, None)
        if plugin is None:
            return False
        # Remove from intent map
        for intent in list(self._intent_map.keys()):
            if self._intent_map[intent] is plugin:
                del self._intent_map[intent]
        if hasattr(plugin, "teardown"):
            try:
                plugin.teardown()
            except Exception as exc:
                logger.warning("PluginLoader: teardown error for '%s' – %s", name, exc)
        logger.info("PluginLoader: unloaded plugin '%s'.", name)
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_plugin(self, path: Path, module_name: str) -> Optional[str]:
        try:
            full_module = f"plugins.{module_name}"
            if full_module in sys.modules:
                mod = sys.modules[full_module]
            else:
                spec = importlib.util.spec_from_file_location(
                    full_module,
                    str(path / "__init__.py") if path.is_dir() else str(path),
                )
                if spec is None or spec.loader is None:
                    return None
                mod = importlib.util.module_from_spec(spec)
                sys.modules[full_module] = mod
                spec.loader.exec_module(mod)  # type: ignore[attr-defined]

            # Validate contract
            plugin_name = getattr(mod, "PLUGIN_NAME", module_name)
            intents = getattr(mod, "PLUGIN_INTENTS", [])
            if not hasattr(mod, "handle"):
                logger.warning(
                    "PluginLoader: '%s' has no handle() function – skipped.", module_name
                )
                return None

            # Setup
            if hasattr(mod, "setup"):
                try:
                    mod.setup()
                except Exception as exc:
                    logger.warning("PluginLoader: setup() failed for '%s' – %s", plugin_name, exc)

            self._plugins[plugin_name] = mod
            for intent in intents:
                self._intent_map[intent.lower()] = mod

            logger.info(
                "PluginLoader: loaded '%s' (intents: %s).", plugin_name, intents
            )
            return plugin_name

        except Exception as exc:
            logger.error("PluginLoader: failed to load '%s' – %s", module_name, exc)
            return None
