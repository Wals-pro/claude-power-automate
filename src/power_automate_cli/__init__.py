"""Power Automate CLI — a local, open client for Microsoft Power Automate cloud
flows, backed by the Dataverse Web API and the Power Platform API.

Authentication uses an existing ``az login`` session; no app registration,
service principal, or hosted Flow Studio token is required. This package stores
no secrets.

Part of the **claude-power-automate** suite (Claude Code skills + CLI).
"""
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.3.0"
