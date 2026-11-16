"""Finds the adapters: every Adapter subclass in a module of this package.

Adding a provider is adding a file here; deleting a file removes it.
"""

import importlib
import pkgutil

from app.adapters.base import Adapter


def load_adapters() -> dict[str, Adapter]:
    """One instance of each adapter, keyed by its name."""
    adapters = {}
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, Adapter) and value is not Adapter:
                adapters[value.name] = value()
    return dict(sorted(adapters.items()))


def check_health(adapters: dict[str, Adapter]) -> dict[str, bool]:
    """Run every adapter's available() check."""
    return {name: adapter.available() for name, adapter in adapters.items()}
