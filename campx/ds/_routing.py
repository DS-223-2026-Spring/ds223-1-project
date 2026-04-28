"""Import routing helpers for local package and DS container layouts."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

DS_DIR = Path(__file__).resolve().parent
REPO_ROOT = DS_DIR.parents[1] if len(DS_DIR.parents) > 1 else DS_DIR


def ensure_repo_root_on_path() -> None:
    """Make `campx.ds` importable when a DS script is run by file path."""

    if not (REPO_ROOT / "campx" / "__init__.py").exists():
        return

    repo_root = str(REPO_ROOT)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


def import_module(module_names: Sequence[str]) -> ModuleType:
    """Import the first available module from equivalent layout names."""

    ensure_repo_root_on_path()
    errors: list[ModuleNotFoundError] = []
    for module_name in module_names:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if _missing_requested_module(exc, module_name):
                errors.append(exc)
                continue
            raise

    attempted = ", ".join(module_names)
    raise ModuleNotFoundError(f"Could not import any of: {attempted}") from errors[-1]


def import_ds_module(relative_module: str) -> ModuleType:
    """Import a DS module in repo package or container top-level layout."""

    return import_module((f"campx.ds.{relative_module}", relative_module))


def load_attr(module_names: Sequence[str], attr_name: str) -> Any:
    """Load an attribute from the first available module."""

    return getattr(import_module(module_names), attr_name)


def load_ds_attr(relative_module: str, attr_name: str) -> Any:
    """Load an attribute from a DS module in either supported layout."""

    return getattr(import_ds_module(relative_module), attr_name)


def _missing_requested_module(exc: ModuleNotFoundError, module_name: str) -> bool:
    missing = exc.name or ""
    return missing == module_name or module_name.startswith(f"{missing}.")
