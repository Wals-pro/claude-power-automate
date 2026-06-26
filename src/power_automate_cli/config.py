"""Profile / connection-target resolution for the Power Automate CLI.

This tool stores **no secrets**. Short-lived OAuth tokens are obtained from an
existing ``az login`` session (see :mod:`power_automate_cli.auth`). The only
thing resolved here is the non-secret *target* of a command: which Power
Platform environment, flow, Dataverse URL and (optionally) Entra tenant to act
against.

Resolution order for each field, first hit wins:

1. An explicit CLI flag (handled by the caller in :mod:`power_automate_cli.cli`).
2. A resolver registered via :func:`register_profile_resolver` — the embedding
   hook. Host applications (e.g. a multi-tenant repo) can inject their own
   lookup, such as a secrets manager, without this package depending on it.
3. Environment variables ``POWER_AUTOMATE_<PROFILE>_<FIELD>`` then
   ``POWER_AUTOMATE_<FIELD>``.
4. A JSON profiles file at ``$POWER_AUTOMATE_CONFIG`` or
   ``~/.config/power-automate-cli/profiles.json``.

Profiles file shape (a top-level ``"profiles"`` wrapper is also accepted)::

    {
      "acme": {
        "environment_id": "00000000-0000-0000-0000-000000000000",
        "flow_id": "11111111-1111-1111-1111-111111111111",
        "dataverse_url": "https://org.crm4.dynamics.com",
        "entra_tenant_id": "22222222-2222-2222-2222-222222222222"
      }
    }
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable, Optional

FIELDS = ("environment_id", "flow_id", "dataverse_url", "entra_tenant_id")

ProfileResolver = Callable[[str, str], Optional[str]]

_resolver: Optional[ProfileResolver] = None


class ProfileNotFound(RuntimeError):
    """Raised when a requested profile/field cannot be resolved anywhere."""


def register_profile_resolver(resolver: Optional[ProfileResolver]) -> None:
    """Install (or clear with ``None``) the embedding resolver hook.

    ``resolver(profile, field)`` should return the value or ``None``. This lets
    a host application bridge its own configuration/secrets store into the CLI
    without this package taking a dependency on it.
    """
    global _resolver
    _resolver = resolver


def _config_path() -> Path:
    override = os.environ.get("POWER_AUTOMATE_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "power-automate-cli" / "profiles.json"


def _from_env(profile: str, field: str) -> Optional[str]:
    suffix = field.upper()
    keys = []
    if profile:
        keys.append(f"POWER_AUTOMATE_{profile.upper().replace('-', '_')}_{suffix}")
    keys.append(f"POWER_AUTOMATE_{suffix}")
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return None


def _from_file(profile: str, field: str) -> Optional[str]:
    path = _config_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    # Accept either a flat {"<profile>": {...}} map or a {"profiles": {...}} wrapper.
    profiles = data["profiles"] if isinstance(data.get("profiles"), dict) else data
    entry = profiles.get(profile) if profile else None
    if not isinstance(entry, dict):
        return None
    value = entry.get(field)
    return str(value) if value not in (None, "") else None


def resolve_field(profile: str, field: str) -> Optional[str]:
    """Resolve a single non-secret target field for ``profile``.

    Returns ``None`` if no source provides the field. Callers treat a missing
    required field (e.g. ``environment_id``) as a user-facing error.
    """
    if field not in FIELDS:
        raise ValueError(f"Unknown field {field!r}; expected one of {FIELDS}.")
    if _resolver is not None:
        try:
            value = _resolver(profile, field)
        except ProfileNotFound:
            value = None
        if value:
            return str(value)
    return _from_env(profile, field) or _from_file(profile, field)
