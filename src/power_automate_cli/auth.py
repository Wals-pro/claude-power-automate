"""Microsoft authentication helpers backed by Azure CLI."""
from __future__ import annotations

import json
import subprocess
from typing import Optional, Type


class MicrosoftAuthError(RuntimeError):
    """Raised when an Azure CLI token cannot be acquired."""


class AzureCliTokenProvider:
    """Gets OAuth access tokens from an existing `az login` session."""

    def __init__(
        self,
        entra_tenant_id: Optional[str] = None,
        error_type: Type[Exception] = MicrosoftAuthError,
    ):
        self.entra_tenant_id = entra_tenant_id
        self.error_type = error_type
        self._cache: dict[str, str] = {}

    def token_for(self, resource: str) -> str:
        if resource in self._cache:
            return self._cache[resource]

        cmd = ["az", "account", "get-access-token", "--resource", resource, "--output", "json"]
        if self.entra_tenant_id:
            cmd.extend(["--tenant", self.entra_tenant_id])
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        except FileNotFoundError as exc:
            raise self.error_type("Azure CLI `az` is not installed or not on PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise self.error_type("Azure CLI token request timed out.") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise self.error_type(
                "Azure CLI could not provide a Microsoft access token. Run `az login` "
                "for the target tenant and retry.\n"
                f"{detail}"
            )

        try:
            token = json.loads(result.stdout)["accessToken"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise self.error_type("Azure CLI token response did not contain accessToken.") from exc

        self._cache[resource] = token
        return token
