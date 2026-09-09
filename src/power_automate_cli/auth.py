"""Microsoft authentication helpers backed by Azure CLI."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Type


class MicrosoftAuthError(RuntimeError):
    """Raised when an Azure CLI token cannot be acquired."""


class AzureCliTokenProvider:
    """Gets OAuth access tokens from an existing `az login` session."""

    def __init__(
        self,
        entra_tenant_id: Optional[str] = None,
        error_type: Type[Exception] = MicrosoftAuthError,
        azure_config_dir: Optional[str] = None,
    ):
        self.entra_tenant_id = entra_tenant_id
        self.error_type = error_type
        self.azure_config_dir = azure_config_dir
        self._cache: dict[str, str] = {}

    def _subprocess_env(self) -> Optional[dict[str, str]]:
        """Environment for the ``az`` child process.

        With ``azure_config_dir`` set, the Azure CLI reads its session from that
        directory instead of the shared ``~/.azure``. Each profile can then keep
        its own signed-in account, so several tenants stay usable in parallel and
        no ``az login`` / ``az account set`` switching is needed between them.
        """
        if not self.azure_config_dir:
            return None
        env = dict(os.environ)
        env["AZURE_CONFIG_DIR"] = str(Path(self.azure_config_dir).expanduser())
        return env

    def token_for(self, resource: str) -> str:
        if resource in self._cache:
            return self._cache[resource]

        cmd = ["az", "account", "get-access-token", "--resource", resource, "--output", "json"]
        if self.entra_tenant_id:
            cmd.extend(["--tenant", self.entra_tenant_id])
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=45, env=self._subprocess_env()
            )
        except FileNotFoundError as exc:
            raise self.error_type("Azure CLI `az` is not installed or not on PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise self.error_type("Azure CLI token request timed out.") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            where = (
                f" with AZURE_CONFIG_DIR={Path(self.azure_config_dir).expanduser()}"
                if self.azure_config_dir
                else ""
            )
            raise self.error_type(
                "Azure CLI could not provide a Microsoft access token. Run `az login` "
                f"for the target tenant{where} and retry.\n"
                f"{detail}"
            )

        try:
            token = json.loads(result.stdout)["accessToken"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise self.error_type("Azure CLI token response did not contain accessToken.") from exc

        self._cache[resource] = token
        return token
