#!/usr/bin/env python3
"""Local Power Automate control client backed by Dataverse Web API."""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from .auth import AzureCliTokenProvider as BaseAzureCliTokenProvider
from .config import resolve_field

DATAVERSE_API_VERSION = "v9.2"
POWER_PLATFORM_API_VERSION = "2024-10-01"
ENVIRONMENT_API_VERSION = "2024-10-01"
RUN_ACTIONS_API_VERSION = "2022-03-01-preview"
POWER_PLATFORM_RESOURCE = "https://api.powerplatform.com/"
PROCESS_SIMPLE_API_VERSION = "2016-11-01"
FLOW_SERVICE_RESOURCE = "https://service.flow.microsoft.com/"
FLOW_API_BASE = "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"
PROCESS_FLOW_EXPAND = (
    "properties.connectionreferences.apidefinition,"
    "properties.definitionsummary.operations.apioperation,"
    "operationDefinition,"
    "plan,"
    "properties.throttleData,"
    "properties.estimatedsuspensiondata,"
    "properties.licenseData,"
    "properties.billingContext,"
    "properties.throttlingBehavior,"
    "properties.powerFlowType,"
    "properties.protectionStatus,"
    "properties.owningUser"
)

SECRET_ENV_VAR_TYPE = 100000005
ENV_VAR_DEFINITION_COMPONENT_TYPE = 380
SECRET_PLACEHOLDER = "<secret · Azure Key Vault-backed>"
ENV_VAR_TYPE_LABELS = {
    100000000: "String",
    100000001: "Number",
    100000002: "Boolean",
    100000003: "JSON",
    100000004: "Data Source",
    SECRET_ENV_VAR_TYPE: "Secret",
}
SOLUTION_COMPONENT_TYPE_LABELS = {
    1: "Entity",
    29: "Workflow / Cloud flow",
    31: "Report",
    60: "SystemForm",
    61: "WebResource",
    62: "SiteMap",
    90: "PluginAssembly",
    91: "SDKMessageProcessingStep",
    92: "ServiceEndpoint",
    300: "CanvasApp",
    380: "EnvironmentVariableDefinition",
    381: "EnvironmentVariableValue",
    10112: "ConnectionReference",
}


class PowerAutomateError(RuntimeError):
    """Raised for expected CLI/API failures with user-readable messages."""


@dataclass(frozen=True)
class PowerAutomateConfig:
    tenant: str
    environment_id: str
    flow_id: Optional[str] = None
    dataverse_url: Optional[str] = None
    entra_tenant_id: Optional[str] = None


class AzureCliTokenProvider(BaseAzureCliTokenProvider):
    """Power Automate-flavoured Azure CLI token provider."""

    def __init__(self, entra_tenant_id: Optional[str] = None):
        super().__init__(entra_tenant_id=entra_tenant_id, error_type=PowerAutomateError)


class PowerAutomateClient:
    def __init__(
        self,
        config: PowerAutomateConfig,
        token_provider: AzureCliTokenProvider,
        session: Optional[requests.Session] = None,
    ):
        self.config = config
        self.token_provider = token_provider
        self.session = session or requests.Session()
        self._dataverse_url = normalize_base_url(config.dataverse_url) if config.dataverse_url else None

    @property
    def dataverse_url(self) -> str:
        if self._dataverse_url:
            return self._dataverse_url
        discovered = self.discover_dataverse_url()
        self._dataverse_url = normalize_base_url(discovered)
        return self._dataverse_url

    def discover_dataverse_url(self) -> str:
        url = (
            "https://api.powerplatform.com/environmentmanagement/environments/"
            f"{self.config.environment_id}?api-version={ENVIRONMENT_API_VERSION}"
        )
        try:
            data = self._request("GET", url, resource=POWER_PLATFORM_RESOURCE)
        except PowerAutomateError as exc:
            raise PowerAutomateError(
                "Could not read Power Platform environment metadata. Check that `az login` uses "
                "an account/tenant with access to the environment, or set the Dataverse URL "
                "(--dataverse-url or POWER_AUTOMATE_DATAVERSE_URL).\n"
                f"{exc}"
            ) from exc
        props = data.get("properties") if isinstance(data, dict) else {}
        linked = props.get("linkedEnvironmentMetadata") if isinstance(props, dict) else {}
        candidates = [
            data.get("url") if isinstance(data, dict) else None,
            props.get("dataverseUrl") if isinstance(props, dict) else None,
            props.get("instanceUrl") if isinstance(props, dict) else None,
            linked.get("instanceUrl") if isinstance(linked, dict) else None,
            linked.get("instanceApiUrl") if isinstance(linked, dict) else None,
        ]
        for candidate in candidates:
            if candidate:
                value = str(candidate)
                if ".api.crm" in value:
                    value = value.replace(".api.crm", ".crm", 1)
                return value
        raise PowerAutomateError(
            "Could not discover Dataverse URL for environment. Set --dataverse-url or "
            "POWER_AUTOMATE_DATAVERSE_URL (e.g. https://org.crm4.dynamics.com)."
        )

    def get_environment(self, environment_id: Optional[str] = None) -> dict[str, Any]:
        eid = environment_id or self.config.environment_id
        url = (
            "https://api.powerplatform.com/environmentmanagement/environments/"
            f"{eid}?api-version={ENVIRONMENT_API_VERSION}"
        )
        return self._request("GET", url, resource=POWER_PLATFORM_RESOURCE)

    def list_environments(self) -> list[dict[str, Any]]:
        url = f"https://api.powerplatform.com/environmentmanagement/environments?api-version={ENVIRONMENT_API_VERSION}"
        return self._get_paged(url, POWER_PLATFORM_RESOURCE)

    def list_flows(
        self,
        environment: Optional[dict[str, Any]] = None,
        include_off: bool = False,
    ) -> list[dict[str, Any]]:
        env = environment or self.default_environment()
        dataverse_url = environment_dataverse_url(env)
        if not dataverse_url:
            raise PowerAutomateError(
                f"Environment {environment_id(env)} has no Dataverse URL. "
                "Pass --dataverse-url for the configured tenant or skip this environment."
            )
        filters = ["category eq 5"]
        if not include_off:
            filters.append("statecode eq 1")
        params = {
            "$select": "workflowid,name,statecode,statuscode,modifiedon,createdon,category,type",
            "$filter": " and ".join(filters),
            "$orderby": "modifiedon desc",
        }
        url = f"{normalize_base_url(dataverse_url)}/api/data/{DATAVERSE_API_VERSION}/workflows?{urlencode(params)}"
        flows = self._get_paged(url, normalize_base_url(dataverse_url))
        for flow in flows:
            flow.setdefault("_environmentId", environment_id(env))
            flow.setdefault("_environmentName", environment_name(env))
            flow.setdefault("_dataverseUrl", normalize_base_url(dataverse_url))
        return flows

    def get_workflow(self, flow_id: Optional[str] = None) -> dict[str, Any]:
        fid = require_flow_id(flow_id or self.config.flow_id)
        select = ",".join([
            "workflowid",
            "name",
            "description",
            "statecode",
            "statuscode",
            "modifiedon",
            "createdon",
            "category",
            "type",
            "clientdata",
        ])
        url = f"{self._workflow_url(fid)}?{urlencode({'$select': select})}"
        return self._request("GET", url, resource=self.dataverse_url)

    def patch_clientdata(self, clientdata: str, flow_id: Optional[str] = None) -> None:
        fid = require_flow_id(flow_id or self.config.flow_id)
        self._request("PATCH", self._workflow_url(fid), resource=self.dataverse_url, json_body={"clientdata": clientdata})

    def set_state(self, enabled: bool, flow_id: Optional[str] = None) -> None:
        fid = require_flow_id(flow_id or self.config.flow_id)
        payload = {"statecode": 1 if enabled else 0, "statuscode": 2 if enabled else 1}
        self._request("PATCH", self._workflow_url(fid), resource=self.dataverse_url, json_body=payload)

    def create_workflow(
        self,
        *,
        name: str,
        clientdata: str,
        description: Optional[str] = None,
        primaryentity: str = "none",
        solution_unique_name: Optional[str] = None,
        activate: bool = False,
    ) -> dict[str, Any]:
        """Create a new modern cloud flow (category 5) via the Dataverse Web API.

        Created in Draft (statecode 0); pass ``activate=True`` to turn it on
        afterwards (requires its connection references to resolve). Pass
        ``solution_unique_name`` to add the flow to that unmanaged solution so it
        ships through the normal DEV->PROD deployment pipeline.
        """
        body: dict[str, Any] = {
            "name": name,
            "category": 5,
            "type": 1,
            "primaryentity": primaryentity,
            "clientdata": clientdata,
        }
        if description:
            body["description"] = description
        extra_headers = {"Prefer": "return=representation"}
        if solution_unique_name:
            extra_headers["MSCRM.SolutionUniqueName"] = solution_unique_name
        url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/workflows"
        created = self._request(
            "POST", url, resource=self.dataverse_url, json_body=body, extra_headers=extra_headers
        )
        created = created if isinstance(created, dict) else {}
        new_flow_id = created.get("workflowid")
        if activate and new_flow_id:
            self.set_state(True, flow_id=new_flow_id)
        return created

    def list_solutions(self, include_managed: bool = True) -> list[dict[str, Any]]:
        filters = ["isvisible eq true"]
        if not include_managed:
            filters.append("ismanaged eq false")
        params = {
            "$select": "solutionid,uniquename,friendlyname,version,ismanaged,installedon,modifiedon",
            "$filter": " and ".join(filters),
            "$orderby": "friendlyname asc",
        }
        url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/solutions?{urlencode(params)}"
        return self._get_paged(url, self.dataverse_url)

    def get_solution(self, unique_name: str) -> dict[str, Any]:
        params = {
            "$select": "solutionid,uniquename,friendlyname,version,ismanaged",
            "$filter": f"uniquename eq '{escape_odata(unique_name)}'",
        }
        url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/solutions?{urlencode(params)}"
        rows = self._get_paged(url, self.dataverse_url)
        if not rows:
            raise PowerAutomateError(
                f"Solution not found: {unique_name!r}. Run `solutions` to list available solutions."
            )
        return rows[0]

    def solution_components(self, solution_id: str) -> list[dict[str, Any]]:
        params = {
            "$select": "solutioncomponentid,componenttype,objectid,rootcomponentbehavior",
            "$filter": f"_solutionid_value eq {solution_id}",
        }
        url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/solutioncomponents?{urlencode(params)}"
        return self._get_paged(url, self.dataverse_url)

    def list_environment_variables(self, solution_unique_name: Optional[str] = None) -> list[dict[str, Any]]:
        params = {
            "$select": "environmentvariabledefinitionid,schemaname,displayname,type,defaultvalue,description",
            "$expand": "environmentvariabledefinition_environmentvariablevalue($select=value,environmentvariablevalueid)",
            "$orderby": "schemaname asc",
        }
        if solution_unique_name:
            solution = self.get_solution(solution_unique_name)
            ids = [
                c["objectid"]
                for c in self.solution_components(solution["solutionid"])
                if c.get("componenttype") == ENV_VAR_DEFINITION_COMPONENT_TYPE and c.get("objectid")
            ]
            if not ids:
                return []
            params["$filter"] = " or ".join(f"environmentvariabledefinitionid eq {i}" for i in ids)
        url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/environmentvariabledefinitions?{urlencode(params)}"
        return self._get_paged(url, self.dataverse_url)

    def set_environment_variable_value(
        self,
        schema_name: str,
        value: str,
        solution_unique_name: Optional[str] = None,
    ) -> dict[str, Any]:
        definition = next(
            (d for d in self.list_environment_variables() if d.get("schemaname") == schema_name),
            None,
        )
        if definition is None:
            raise PowerAutomateError(f"Environment variable not found: {schema_name!r}.")
        if is_secret_env_var(definition):
            raise PowerAutomateError(
                "Refusing to set a Secret-type environment variable from a literal value. Secret "
                "variables are backed by Azure Key Vault — configure them in the portal or with a "
                "Key Vault reference, never by passing the secret here."
            )
        definition_id = definition["environmentvariabledefinitionid"]
        existing = definition.get("environmentvariabledefinition_environmentvariablevalue") or []
        extra_headers = {"MSCRM.SolutionUniqueName": solution_unique_name} if solution_unique_name else None
        if existing:
            value_id = existing[0]["environmentvariablevalueid"]
            url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/environmentvariablevalues({value_id})"
            self._request("PATCH", url, resource=self.dataverse_url, json_body={"value": value}, extra_headers=extra_headers)
            return {"schemaName": schema_name, "valueId": value_id, "created": False}
        url = f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/environmentvariablevalues"
        body = {
            "value": value,
            "EnvironmentVariableDefinitionId@odata.bind": f"/environmentvariabledefinitions({definition_id})",
        }
        headers = {"Prefer": "return=representation"}
        if extra_headers:
            headers.update(extra_headers)
        created = self._request("POST", url, resource=self.dataverse_url, json_body=body, extra_headers=headers)
        created = created if isinstance(created, dict) else {}
        return {"schemaName": schema_name, "valueId": created.get("environmentvariablevalueid"), "created": True}

    def list_runs(self, flow_id: Optional[str] = None, environment_id_: Optional[str] = None) -> Any:
        fid = require_flow_id(flow_id or self.config.flow_id)
        eid = environment_id_ or self.config.environment_id
        qs = urlencode({"workflowId": fid, "api-version": POWER_PLATFORM_API_VERSION})
        url = f"https://api.powerplatform.com/powerautomate/environments/{eid}/flowRuns?{qs}"
        return self._request("GET", url, resource=POWER_PLATFORM_RESOURCE, allow_no_content=True)

    def run_actions(self, run_id: str, flow_id: Optional[str] = None) -> Any:
        fid = require_flow_id(flow_id or self.config.flow_id)
        qs = urlencode({"api-version": RUN_ACTIONS_API_VERSION})
        url = (
            "https://api.powerplatform.com/workflowsagent/environments/"
            f"{self.config.environment_id}/aiFlows/{fid}/runs/{run_id}/actions?{qs}"
        )
        return self._request("GET", url, resource=POWER_PLATFORM_RESOURCE, allow_no_content=True)

    def get_process_flow(self, flow_id: Optional[str] = None) -> dict[str, Any]:
        fid = require_flow_id(flow_id or self.config.flow_id)
        return self._request("GET", self._process_flow_url(fid), resource=FLOW_SERVICE_RESOURCE)

    def update_process_flow(self, flow: dict[str, Any], flow_id: Optional[str] = None) -> dict[str, Any]:
        fid = require_flow_id(flow_id or self.config.flow_id)
        return self._request("PATCH", self._process_patch_flow_url(fid), resource=FLOW_SERVICE_RESOURCE, json_body=flow)

    def process_runs(self, flow_id: Optional[str] = None) -> Any:
        fid = require_flow_id(flow_id or self.config.flow_id)
        url = f"{self._process_flow_base_url(fid)}/runs?{urlencode({'api-version': PROCESS_SIMPLE_API_VERSION})}"
        return self._request("GET", url, resource=FLOW_SERVICE_RESOURCE, allow_no_content=True)

    def process_run_actions(self, run_id: str, flow_id: Optional[str] = None) -> Any:
        fid = require_flow_id(flow_id or self.config.flow_id)
        url = (
            f"{self._process_flow_base_url(fid)}/runs/{run_id}/actions?"
            f"{urlencode({'api-version': PROCESS_SIMPLE_API_VERSION})}"
        )
        return self._request("GET", url, resource=FLOW_SERVICE_RESOURCE, allow_no_content=True)

    def process_trigger_callback_url(self, trigger_name: str, flow_id: Optional[str] = None) -> dict[str, Any]:
        fid = require_flow_id(flow_id or self.config.flow_id)
        url = (
            f"{self._process_flow_base_url(fid)}/triggers/{trigger_name}/listCallbackUrl?"
            f"{urlencode({'api-version': PROCESS_SIMPLE_API_VERSION})}"
        )
        return self._request("POST", url, resource=FLOW_SERVICE_RESOURCE)

    def _workflow_url(self, flow_id: str) -> str:
        return f"{self.dataverse_url}/api/data/{DATAVERSE_API_VERSION}/workflows({flow_id})"

    def _process_flow_url(self, flow_id: str) -> str:
        qs = urlencode({"api-version": PROCESS_SIMPLE_API_VERSION})
        return f"{self._process_flow_base_url(flow_id)}?{qs}"

    def _process_flow_base_url(self, flow_id: str) -> str:
        return f"{FLOW_API_BASE}/environments/{self.config.environment_id}/flows/{flow_id}"

    def _process_patch_flow_url(self, flow_id: str) -> str:
        qs = urlencode({
            "api-version": "1",
            "$expand": PROCESS_FLOW_EXPAND,
            "telemetryMetadata": json.dumps({"modifiedSources": "Portal"}, separators=(",", ":")),
        })
        return f"{environment_api_host(self.config.environment_id)}/powerautomate/flows/{flow_id}?{qs}"

    def default_environment(self) -> dict[str, Any]:
        return {
            "id": self.config.environment_id,
            "name": self.config.environment_id,
            "url": self._dataverse_url or self.dataverse_url,
        }

    def _get_paged(self, url: str, resource: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: Optional[str] = url
        while next_url:
            data = self._request("GET", next_url, resource=resource, allow_no_content=True)
            if isinstance(data, dict):
                value = data.get("value")
                if isinstance(value, list):
                    items.extend([item for item in value if isinstance(item, dict)])
                elif data:
                    items.append(data)
                next_url = data.get("@odata.nextLink") or data.get("nextLink")
            elif isinstance(data, list):
                items.extend([item for item in data if isinstance(item, dict)])
                next_url = None
            else:
                next_url = None
        return items

    def _request(
        self,
        method: str,
        url: str,
        resource: str,
        json_body: Optional[dict[str, Any]] = None,
        allow_no_content: bool = False,
        extra_headers: Optional[dict[str, str]] = None,
    ) -> Any:
        token = self.token_provider.token_for(resource)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        if extra_headers:
            headers.update(extra_headers)

        response = self.session.request(method, url, headers=headers, json=json_body, timeout=60)
        if response.status_code == 204 and allow_no_content:
            return {"value": []}
        if response.status_code == 204:
            return None
        if response.status_code >= 400:
            body = response.text[:2000]
            raise PowerAutomateError(f"{method} {url} failed with HTTP {response.status_code}:\n{body}")
        if not response.text.strip():
            return None
        return response.json()


def normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def escape_odata(value: str) -> str:
    return value.replace("'", "''")


def is_secret_env_var(definition: dict[str, Any]) -> bool:
    try:
        return int(definition.get("type")) == SECRET_ENV_VAR_TYPE
    except (TypeError, ValueError):
        return False


def env_var_type_label(definition: dict[str, Any]) -> str:
    raw = definition.get("type")
    try:
        return ENV_VAR_TYPE_LABELS.get(int(raw), str(raw))
    except (TypeError, ValueError):
        return str(raw)


def env_var_current_value(definition: dict[str, Any]) -> Optional[str]:
    values = definition.get("environmentvariabledefinition_environmentvariablevalue") or []
    if values and isinstance(values[0], dict):
        return values[0].get("value")
    return None


def env_var_display(definition: dict[str, Any], raw_value: Optional[str], reveal_secret: bool = False) -> str:
    if raw_value in (None, ""):
        return ""
    if is_secret_env_var(definition) and not reveal_secret:
        return SECRET_PLACEHOLDER
    return str(raw_value)


def solution_component_label(component_type: Any) -> str:
    try:
        return SOLUTION_COMPONENT_TYPE_LABELS.get(int(component_type), f"Type {component_type}")
    except (TypeError, ValueError):
        return f"Type {component_type}"


def require_flow_id(value: Optional[str]) -> str:
    if not value:
        raise PowerAutomateError(
            "Missing flow id. Pass --flow-id, set POWER_AUTOMATE_FLOW_ID, or add it to your profile."
        )
    return value


def environment_id(environment: dict[str, Any]) -> str:
    props = environment.get("properties") if isinstance(environment.get("properties"), dict) else {}
    for key in ("id", "name", "environmentId", "environmentName"):
        value = environment.get(key)
        if value:
            return str(value)
    for key in ("environmentId", "environmentName"):
        value = props.get(key)
        if value:
            return str(value)
    return ""


def environment_name(environment: dict[str, Any]) -> str:
    props = environment.get("properties") if isinstance(environment.get("properties"), dict) else {}
    display = props.get("displayName") or environment.get("displayName")
    return str(display or environment_id(environment))


def environment_dataverse_url(environment: dict[str, Any]) -> Optional[str]:
    props = environment.get("properties") if isinstance(environment.get("properties"), dict) else {}
    linked = props.get("linkedEnvironmentMetadata") if isinstance(props.get("linkedEnvironmentMetadata"), dict) else {}
    candidates = [
        environment.get("url"),
        props.get("dataverseUrl"),
        props.get("instanceUrl"),
        linked.get("instanceUrl"),
        linked.get("instanceApiUrl"),
    ]
    for candidate in candidates:
        if candidate:
            value = str(candidate)
            if ".api.crm" in value:
                value = value.replace(".api.crm", ".crm", 1)
            return normalize_base_url(value)
    return None


def environment_api_host(environment_id_: str) -> str:
    value = environment_id_.lower()
    if value.startswith("default-"):
        compact = value.removeprefix("default-").replace("-", "")
        prefix = "default"
    else:
        compact = value.replace("-", "")
        prefix = ""
    if len(compact) < 3:
        raise PowerAutomateError(f"Cannot derive Power Automate environment API host from {environment_id_!r}.")
    return f"https://{prefix}{compact[:-2]}.{compact[-2:]}.environment.api.powerplatform.com"


def flow_id(flow: dict[str, Any]) -> str:
    return str(flow.get("workflowid") or flow.get("id") or flow.get("name") or "")


def flow_name(flow: dict[str, Any]) -> str:
    return str(flow.get("name") or flow_id(flow))


def values_from_response(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, dict):
        value = response.get("value")
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if response:
            return [response]
        return []
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    return []


def first_present(mapping: dict[str, Any], paths: list[tuple[str, ...]]) -> str:
    for path in paths:
        current: Any = mapping
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current not in (None, ""):
            return str(current)
    return ""


def run_id(run: dict[str, Any]) -> str:
    return first_present(run, [("name",), ("id",), ("runId",), ("properties", "runId")])


def run_status(run: dict[str, Any]) -> str:
    return first_present(run, [("status",), ("properties", "status")])


def run_start_time(run: dict[str, Any]) -> str:
    return first_present(run, [
        ("startTime",),
        ("properties", "startTime"),
        ("properties", "startTimeUtc"),
    ])


def run_end_time(run: dict[str, Any]) -> str:
    return first_present(run, [
        ("endTime",),
        ("properties", "endTime"),
        ("properties", "endTimeUtc"),
    ])


def run_error(run: dict[str, Any]) -> str:
    value = first_present(run, [
        ("error", "message"),
        ("properties", "error", "message"),
        ("properties", "error", "code"),
    ])
    if value:
        return value
    props = run.get("properties") if isinstance(run.get("properties"), dict) else {}
    error_obj = run.get("error") or props.get("error")
    return json.dumps(error_obj, ensure_ascii=False) if error_obj else ""


def normalize_run(environment: dict[str, Any], flow: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    return {
        "environmentName": environment_name(environment),
        "environmentId": environment_id(environment),
        "flowName": flow_name(flow),
        "flowId": flow_id(flow),
        "runId": run_id(run),
        "status": run_status(run),
        "startTime": run_start_time(run),
        "endTime": run_end_time(run),
        "error": run_error(run),
        "raw": run,
    }


def format_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = min(max(widths[col], len(str(row.get(col, "")))), 80)
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    separator = "  ".join("-" * widths[col] for col in columns)
    lines = [header, separator]
    for row in rows:
        cells = []
        for col in columns:
            value = str(row.get(col, ""))
            if len(value) > widths[col]:
                value = value[: max(widths[col] - 1, 0)] + "…"
            cells.append(value.ljust(widths[col]))
        lines.append("  ".join(cells))
    return "\n".join(lines) + "\n"


def parse_clientdata(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {"properties": {}}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PowerAutomateError("workflow.clientdata is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise PowerAutomateError("workflow.clientdata must decode to a JSON object.")
    parsed.setdefault("properties", {})
    return parsed


def artifact_from_workflow(config: PowerAutomateConfig, workflow: dict[str, Any]) -> dict[str, Any]:
    clientdata = parse_clientdata(workflow.get("clientdata"))
    props = clientdata.get("properties") or {}
    return {
        "environmentName": config.environment_id,
        "flowName": workflow.get("workflowid") or config.flow_id,
        "displayName": workflow.get("name"),
        "statecode": workflow.get("statecode"),
        "statuscode": workflow.get("statuscode"),
        "modifiedon": workflow.get("modifiedon"),
        "definition": props.get("definition") or {},
        "connectionReferences": props.get("connectionReferences") or {},
    }


def artifact_from_process_flow(config: PowerAutomateConfig, flow: dict[str, Any]) -> dict[str, Any]:
    props = flow.get("properties") if isinstance(flow.get("properties"), dict) else {}
    return {
        "environmentName": config.environment_id,
        "flowName": flow.get("name") or config.flow_id,
        "displayName": props.get("displayName"),
        "state": props.get("state"),
        "lastModifiedTime": props.get("lastModifiedTime"),
        "definition": props.get("definition") or {},
        "connectionReferences": props.get("connectionReferences") or {},
    }


def load_artifact(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PowerAutomateError(f"Artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PowerAutomateError(f"Artifact is not valid JSON: {path}") from exc
    validate_artifact(data, path)
    return data


def validate_artifact(data: dict[str, Any], path: Path | str = "<artifact>") -> None:
    if not isinstance(data, dict):
        raise PowerAutomateError(f"{path}: artifact must be a JSON object.")
    for key in ("definition", "connectionReferences"):
        if key not in data:
            raise PowerAutomateError(f"{path}: missing required key `{key}`.")
        if not isinstance(data[key], dict):
            raise PowerAutomateError(f"{path}: `{key}` must be an object.")


def build_clientdata(existing_raw: str | dict[str, Any] | None, artifact: dict[str, Any]) -> str:
    validate_artifact(artifact)
    existing = parse_clientdata(existing_raw)
    props = existing.setdefault("properties", {})
    props["definition"] = artifact["definition"]
    props["connectionReferences"] = artifact["connectionReferences"]
    existing.setdefault("schemaVersion", "1.0.0.0")
    return json.dumps(existing, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def build_process_flow(existing: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    validate_artifact(artifact)
    props = existing.get("properties") if isinstance(existing.get("properties"), dict) else {}
    flow_name_value = str(existing.get("name") or artifact.get("flowName") or "")
    environment = props.get("environment") if isinstance(props.get("environment"), dict) else {}
    patch_props = {
        "connectionReferences": artifact["connectionReferences"],
        "definition": artifact["definition"],
        "displayName": artifact.get("displayName") or props.get("displayName"),
        "environment": environment,
        "workflowEntityId": flow_name_value,
    }
    return {
        "name": flow_name_value,
        "properties": {key: value for key, value in patch_props.items() if value not in (None, "")},
        "telemetryMetadata": {"modifiedSources": "Portal"},
    }


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def diff_artifacts(live: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    validate_artifact(live, "<live>")
    validate_artifact(local, "<local>")
    sections = {}
    changed = False
    for key in ("definition", "connectionReferences"):
        live_text = canonical(live[key])
        local_text = canonical(local[key])
        section_changed = live_text != local_text
        changed = changed or section_changed
        sections[key] = {
            "changed": section_changed,
            "diff": "".join(
                difflib.unified_diff(
                    live_text.splitlines(keepends=True),
                    local_text.splitlines(keepends=True),
                    fromfile=f"live/{key}",
                    tofile=f"local/{key}",
                )
            ) if section_changed else "",
        }
    return {"changed": changed, "sections": sections}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_backup_path(tenant: str, flow_id: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(".power-automate-backups") / tenant / f"{flow_id}-{stamp}.json"


def _resolve_optional(profile: str, field: str) -> Optional[str]:
    return resolve_field(profile, field) or None


def load_pa_config(
    args: argparse.Namespace,
    require_flow: bool = True,
    require_environment: bool = True,
) -> PowerAutomateConfig:
    environment_id = args.environment_id or _resolve_optional(args.profile, "environment_id")
    if require_environment and not environment_id:
        raise PowerAutomateError(
            "Missing Power Automate environment. Pass --environment-id, set "
            "POWER_AUTOMATE_ENVIRONMENT_ID, or add it to your profile."
        )
    flow_id = args.flow_id or _resolve_optional(args.profile, "flow_id")
    if require_flow:
        require_flow_id(flow_id)
    return PowerAutomateConfig(
        tenant=args.profile,
        environment_id=environment_id,
        flow_id=flow_id,
        dataverse_url=args.dataverse_url or _resolve_optional(args.profile, "dataverse_url"),
        entra_tenant_id=args.entra_tenant_id or _resolve_optional(args.profile, "entra_tenant_id"),
    )


def build_client(
    args: argparse.Namespace,
    require_flow: bool = True,
    require_environment: bool = True,
) -> PowerAutomateClient:
    config = load_pa_config(args, require_flow=require_flow, require_environment=require_environment)
    return PowerAutomateClient(config=config, token_provider=AzureCliTokenProvider(config.entra_tenant_id))


def cmd_pull(args: argparse.Namespace) -> int:
    client = build_client(args)
    workflow = client.get_workflow()
    artifact = artifact_from_workflow(client.config, workflow)
    if args.output:
        write_json(Path(args.output), artifact)
        print(f"Wrote {args.output}")
    else:
        print(canonical(artifact), end="")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    client = build_client(args)
    artifact = artifact_from_workflow(client.config, client.get_workflow())
    output = Path(args.output) if args.output else default_backup_path(client.config.tenant, client.config.flow_id)
    write_json(output, artifact)
    print(f"Wrote {output}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    client = build_client(args)
    workflow = client.get_workflow()
    result = artifact_from_workflow(client.config, workflow)
    print(canonical({
        "environmentName": result["environmentName"],
        "flowName": result["flowName"],
        "displayName": result["displayName"],
        "statecode": result["statecode"],
        "statuscode": result["statuscode"],
        "modifiedon": result["modifiedon"],
    }), end="")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    client = build_client(args)
    local = load_artifact(Path(args.artifact))
    live = artifact_from_workflow(client.config, client.get_workflow())
    result = diff_artifacts(live, local)
    print(canonical({"changed": result["changed"], "sections": {
        key: {"changed": section["changed"]} for key, section in result["sections"].items()
    }}), end="")
    if args.unified:
        for section in result["sections"].values():
            if section["diff"]:
                print(section["diff"], end="")
    return 2 if result["changed"] else 0


def cmd_verify(args: argparse.Namespace) -> int:
    client = build_client(args)
    local = load_artifact(Path(args.artifact))
    live = artifact_from_workflow(client.config, client.get_workflow())
    result = diff_artifacts(live, local)
    print(canonical({"matches": not result["changed"], "changed": result["changed"]}), end="")
    return 1 if result["changed"] else 0


def cmd_deploy(args: argparse.Namespace) -> int:
    client = build_client(args)
    local = load_artifact(Path(args.artifact))
    workflow = client.get_workflow()
    live = artifact_from_workflow(client.config, workflow)
    result = diff_artifacts(live, local)
    if not result["changed"]:
        print(canonical({"changed": False, "deployed": False, "reason": "live already matches local"}), end="")
        return 0

    new_clientdata = build_clientdata(workflow.get("clientdata"), local)
    if args.dry_run:
        print(canonical({
            "changed": True,
            "deployed": False,
            "dryRun": True,
            "clientdataBytes": len(new_clientdata.encode("utf-8")),
        }), end="")
        return 0

    backup = Path(args.backup) if args.backup else default_backup_path(client.config.tenant, client.config.flow_id)
    write_json(backup, live)
    client.patch_clientdata(new_clientdata)
    readback = artifact_from_workflow(client.config, client.get_workflow())
    verify = diff_artifacts(readback, local)
    print(canonical({
        "changed": True,
        "deployed": True,
        "backup": str(backup),
        "verified": not verify["changed"],
    }), end="")
    return 0 if not verify["changed"] else 1


def cmd_create(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False)
    artifact = load_artifact(Path(args.artifact))
    name = args.name or artifact.get("displayName")
    if not name:
        raise PowerAutomateError("Missing flow name. Pass --name or set `displayName` in the artifact.")
    clientdata = build_clientdata(None, artifact)
    if args.dry_run:
        print(canonical({
            "created": False,
            "dryRun": True,
            "name": name,
            "solution": args.solution,
            "activate": args.activate,
            "clientdataBytes": len(clientdata.encode("utf-8")),
        }), end="")
        return 0
    created = client.create_workflow(
        name=name,
        clientdata=clientdata,
        description=args.description,
        solution_unique_name=args.solution,
        activate=args.activate,
    )
    new_flow_id = created.get("workflowid") if isinstance(created, dict) else None
    print(canonical({
        "created": True,
        "workflowId": new_flow_id,
        "name": name,
        "solution": args.solution,
        "activated": bool(args.activate and new_flow_id),
    }), end="")
    return 0 if new_flow_id else 1


def cmd_process_pull(args: argparse.Namespace) -> int:
    client = build_client(args)
    flow = client.get_process_flow()
    artifact = artifact_from_process_flow(client.config, flow)
    if args.output:
        write_json(Path(args.output), artifact)
        print(f"Wrote {args.output}")
    else:
        print(canonical(artifact), end="")
    return 0


def cmd_process_diff(args: argparse.Namespace) -> int:
    client = build_client(args)
    local = load_artifact(Path(args.artifact))
    live = artifact_from_process_flow(client.config, client.get_process_flow())
    result = diff_artifacts(live, local)
    print(canonical({"changed": result["changed"], "sections": {
        key: {"changed": section["changed"]} for key, section in result["sections"].items()
    }}), end="")
    if args.unified:
        for section in result["sections"].values():
            if section["diff"]:
                print(section["diff"], end="")
    return 2 if result["changed"] else 0


def cmd_process_verify(args: argparse.Namespace) -> int:
    client = build_client(args)
    local = load_artifact(Path(args.artifact))
    live = artifact_from_process_flow(client.config, client.get_process_flow())
    result = diff_artifacts(live, local)
    print(canonical({"matches": not result["changed"], "changed": result["changed"]}), end="")
    return 1 if result["changed"] else 0


def cmd_process_deploy(args: argparse.Namespace) -> int:
    client = build_client(args)
    local = load_artifact(Path(args.artifact))
    flow = client.get_process_flow()
    live = artifact_from_process_flow(client.config, flow)
    result = diff_artifacts(live, local)
    if not result["changed"]:
        print(canonical({"changed": False, "deployed": False, "reason": "live already matches local"}), end="")
        return 0

    updated_flow = build_process_flow(flow, local)
    if args.dry_run:
        print(canonical({
            "changed": True,
            "deployed": False,
            "dryRun": True,
            "definitionActions": len(local["definition"].get("actions", {})),
        }), end="")
        return 0

    backup = Path(args.backup) if args.backup else default_backup_path(client.config.tenant, client.config.flow_id)
    write_json(backup, live)
    client.update_process_flow(updated_flow)
    readback = artifact_from_process_flow(client.config, client.get_process_flow())
    verify = diff_artifacts(readback, local)
    print(canonical({
        "changed": True,
        "deployed": True,
        "backup": str(backup),
        "verified": not verify["changed"],
    }), end="")
    return 0 if not verify["changed"] else 1


def cmd_process_runs(args: argparse.Namespace) -> int:
    client = build_client(args)
    env = client.default_environment()
    flow = client.get_process_flow()
    runs = [normalize_run(env, flow, run) for run in values_from_response(client.process_runs())]
    runs.sort(key=lambda item: item.get("startTime") or "", reverse=True)
    if args.top:
        runs = runs[:args.top]
    if args.json:
        print(canonical({"runs": runs}), end="")
    else:
        print(format_table(runs, [
            "environmentName",
            "environmentId",
            "flowName",
            "flowId",
            "runId",
            "status",
            "startTime",
            "endTime",
            "error",
        ]), end="")
    return 0


def cmd_process_run_detail(args: argparse.Namespace) -> int:
    client = build_client(args)
    print(canonical(client.process_run_actions(args.run_id)), end="")
    return 0


def cmd_process_trigger_url(args: argparse.Namespace) -> int:
    client = build_client(args)
    print(canonical(client.process_trigger_callback_url(args.trigger_name)), end="")
    return 0


def cmd_start_stop(args: argparse.Namespace, enabled: bool) -> int:
    client = build_client(args)
    if args.dry_run:
        print(canonical({"changed": True, "dryRun": True, "statecode": 1 if enabled else 0}), end="")
        return 0
    client.set_state(enabled)
    return cmd_status(args)


def scan_flows(
    client: PowerAutomateClient,
    all_environments: bool,
    include_off: bool,
) -> dict[str, Any]:
    warnings: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    if all_environments:
        environments = client.list_environments()
    else:
        environments = [client.default_environment()]

    for env in environments:
        env_id = environment_id(env)
        env_name = environment_name(env)
        try:
            flows = client.list_flows(env, include_off=include_off)
        except PowerAutomateError as exc:
            if not all_environments:
                raise
            warnings.append({
                "environmentId": env_id,
                "environmentName": env_name,
                "message": str(exc),
            })
            continue
        for flow in flows:
            rows.append({
                "environmentName": env_name,
                "environmentId": env_id,
                "flowName": flow_name(flow),
                "flowId": flow_id(flow),
                "statecode": flow.get("statecode", ""),
                "statuscode": flow.get("statuscode", ""),
                "modifiedon": flow.get("modifiedon", ""),
                "raw": flow,
                "_environment": env,
            })
    return {"flows": rows, "warnings": warnings}


def cmd_environments(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False, require_environment=False)
    environments = client.list_environments()
    rows = [{
        "environmentName": environment_name(env),
        "environmentId": environment_id(env),
        "dataverseUrl": environment_dataverse_url(env) or "",
    } for env in environments]
    if args.json:
        print(canonical({"environments": rows, "raw": environments}), end="")
    else:
        print(format_table(rows, ["environmentName", "environmentId", "dataverseUrl"]), end="")
    return 0


def cmd_flows(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False, require_environment=not args.all_environments)
    result = scan_flows(client, args.all_environments, args.include_off)
    rows = result["flows"]
    if args.json:
        print(canonical({"flows": rows, "warnings": result["warnings"]}), end="")
    else:
        print(format_table(rows, ["environmentName", "environmentId", "flowName", "flowId", "statecode", "modifiedon"]), end="")
        for warning in result["warnings"]:
            print(f"WARNING {warning['environmentName']} ({warning['environmentId']}): {warning['message']}", file=sys.stderr)
    return 0


def cmd_runs(args: argparse.Namespace) -> int:
    client = build_client(
        args,
        require_flow=not args.all_environments,
        require_environment=not args.all_environments,
    )
    warnings: list[dict[str, str]] = []
    normalized: list[dict[str, Any]] = []

    if args.all_environments:
        flow_result = scan_flows(client, True, args.include_off)
        warnings.extend(flow_result["warnings"])
        flow_rows = flow_result["flows"]
    else:
        env = client.default_environment()
        flow = client.get_workflow()
        flow_rows = [{
            "environmentName": environment_name(env),
            "environmentId": environment_id(env),
            "flowName": flow_name(flow),
            "flowId": flow_id(flow),
            "_environment": env,
            "raw": flow,
        }]

    for row in flow_rows:
        env = row["_environment"]
        flow = row["raw"]
        try:
            response = client.list_runs(row["flowId"], row["environmentId"])
        except PowerAutomateError as exc:
            if not args.all_environments:
                raise
            warnings.append({
                "environmentId": row["environmentId"],
                "environmentName": row["environmentName"],
                "flowId": row["flowId"],
                "flowName": row["flowName"],
                "message": str(exc),
            })
            continue
        for run in values_from_response(response):
            normalized.append(normalize_run(env, flow, run))

    normalized.sort(key=lambda item: item.get("startTime") or "", reverse=True)
    if args.top:
        normalized = normalized[:args.top]

    if args.json:
        print(canonical({"runs": normalized, "warnings": warnings}), end="")
    else:
        print(format_table(normalized, [
            "environmentName",
            "environmentId",
            "flowName",
            "flowId",
            "runId",
            "status",
            "startTime",
            "endTime",
            "error",
        ]), end="")
        for warning in warnings:
            print(f"WARNING {warning.get('environmentName', '')} ({warning.get('environmentId', '')}): {warning['message']}", file=sys.stderr)
    return 0


def cmd_run_detail(args: argparse.Namespace) -> int:
    client = build_client(args)
    print(canonical(client.run_actions(args.run_id)), end="")
    return 0


def cmd_solutions(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False)
    solutions = client.list_solutions(include_managed=not args.unmanaged_only)
    rows = [{
        "uniqueName": s.get("uniquename", ""),
        "friendlyName": s.get("friendlyname", ""),
        "version": s.get("version", ""),
        "managed": "managed" if s.get("ismanaged") else "unmanaged",
    } for s in solutions]
    if args.json:
        print(canonical({"solutions": rows}), end="")
    else:
        print(format_table(rows, ["uniqueName", "friendlyName", "version", "managed"]), end="")
    return 0


def cmd_solution_components(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False)
    solution = client.get_solution(args.solution)
    components = client.solution_components(solution["solutionid"])
    rows = [{
        "type": solution_component_label(c.get("componenttype")),
        "componentType": c.get("componenttype", ""),
        "objectId": c.get("objectid", ""),
    } for c in components]
    if args.json:
        print(canonical({"solution": solution.get("uniquename"), "components": rows}), end="")
    else:
        print(format_table(rows, ["type", "componentType", "objectId"]), end="")
    return 0


def cmd_env_vars(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False)
    definitions = client.list_environment_variables(solution_unique_name=args.solution)
    rows = []
    for d in definitions:
        rows.append({
            "schemaName": d.get("schemaname", ""),
            "displayName": d.get("displayname", ""),
            "type": env_var_type_label(d),
            "currentValue": env_var_display(d, env_var_current_value(d), reveal_secret=args.reveal_secret),
            "defaultValue": env_var_display(d, d.get("defaultvalue"), reveal_secret=args.reveal_secret),
        })
    if args.json:
        print(canonical({"environmentVariables": rows}), end="")
    else:
        print(format_table(rows, ["schemaName", "displayName", "type", "currentValue", "defaultValue"]), end="")
    return 0


def cmd_env_var_get(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False)
    definition = next(
        (d for d in client.list_environment_variables() if d.get("schemaname") == args.schema_name),
        None,
    )
    if definition is None:
        raise PowerAutomateError(f"Environment variable not found: {args.schema_name!r}.")
    current = env_var_current_value(definition)
    print(canonical({
        "schemaName": definition.get("schemaname"),
        "displayName": definition.get("displayname"),
        "type": env_var_type_label(definition),
        "isSecret": is_secret_env_var(definition),
        "hasCurrentValue": current not in (None, ""),
        "currentValue": env_var_display(definition, current, reveal_secret=args.reveal_secret),
        "defaultValue": env_var_display(definition, definition.get("defaultvalue"), reveal_secret=args.reveal_secret),
    }), end="")
    return 0


def cmd_env_var_set(args: argparse.Namespace) -> int:
    client = build_client(args, require_flow=False)
    if args.dry_run:
        definition = next(
            (d for d in client.list_environment_variables() if d.get("schemaname") == args.schema_name),
            None,
        )
        if definition is None:
            raise PowerAutomateError(f"Environment variable not found: {args.schema_name!r}.")
        if is_secret_env_var(definition):
            raise PowerAutomateError(
                "Refusing to set a Secret-type environment variable from a literal value. "
                "Secret variables are backed by Azure Key Vault."
            )
        # Never echo the value back — avoid leaking it to stdout/logs.
        print(canonical({"schemaName": args.schema_name, "wouldSet": True, "dryRun": True, "solution": args.solution}), end="")
        return 0
    result = client.set_environment_variable_value(args.schema_name, args.value, solution_unique_name=args.solution)
    print(canonical({**result, "set": True}), end="")
    return 0


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", required=True, help="Profile name; resolves env/flow/dataverse from POWER_AUTOMATE_* env vars or profiles.json, and namespaces local backups")
    parser.add_argument("--environment-id", help="Power Platform environment id")
    parser.add_argument("--flow-id", help="Cloud flow workflow id")
    parser.add_argument("--dataverse-url", help="Dataverse environment URL, e.g. https://org.crm4.dynamics.com")
    parser.add_argument("--entra-tenant-id", help="Optional Microsoft Entra tenant id for az token requests")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("pull", "backup", "status"):
        p = sub.add_parser(name)
        add_common_flags(p)
        if name in ("pull", "backup"):
            p.add_argument("--output", help="Output JSON path")

    p = sub.add_parser("environments")
    add_common_flags(p)
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("flows")
    add_common_flags(p)
    p.add_argument("--all-environments", action="store_true", help="Scan all environments visible to the signed-in user")
    p.add_argument("--include-off", action="store_true", help="Include off/inactive cloud flows")
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("runs")
    add_common_flags(p)
    p.add_argument("--all-environments", action="store_true", help="Scan all environments visible to the signed-in user")
    p.add_argument("--include-off", action="store_true", help="Include off/inactive cloud flows during --all-environments scans")
    p.add_argument("--top", type=int, default=20, help="Maximum number of run rows to print after sorting by startTime")
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("diff")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON")
    p.add_argument("--unified", action="store_true", help="Print unified JSON diffs")

    p = sub.add_parser("verify")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON")

    p = sub.add_parser("deploy")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON")
    p.add_argument("--dry-run", action="store_true", help="Validate and show planned update without PATCH")
    p.add_argument("--backup", help="Backup JSON path; defaults to .power-automate-backups/<tenant>/...")

    p = sub.add_parser("create")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON (definition + connectionReferences)")
    p.add_argument("--name", help="Display name for the new flow (defaults to artifact.displayName)")
    p.add_argument("--description", help="Optional flow description")
    p.add_argument("--solution", help="Unmanaged solution unique name to add the flow to, so it ships via the DEV->PROD pipeline")
    p.add_argument("--activate", action="store_true", help="Turn the flow on after creation")
    p.add_argument("--dry-run", action="store_true", help="Validate and show planned create without POST")

    p = sub.add_parser("process-pull")
    add_common_flags(p)
    p.add_argument("--output", help="Output JSON path")

    p = sub.add_parser("process-diff")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON")
    p.add_argument("--unified", action="store_true", help="Print unified JSON diffs")

    p = sub.add_parser("process-verify")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON")

    p = sub.add_parser("process-deploy")
    add_common_flags(p)
    p.add_argument("artifact", help="Local flow artifact JSON")
    p.add_argument("--dry-run", action="store_true", help="Validate and show planned update without PUT")
    p.add_argument("--backup", help="Backup JSON path; defaults to .power-automate-backups/<tenant>/...")

    p = sub.add_parser("process-runs")
    add_common_flags(p)
    p.add_argument("--top", type=int, default=20, help="Maximum number of run rows to print after sorting by startTime")
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("process-run-detail")
    add_common_flags(p)
    p.add_argument("run_id", help="Run id from `process-runs`")

    p = sub.add_parser("process-trigger-url")
    add_common_flags(p)
    p.add_argument("--trigger-name", default="manual", help="Trigger internal name; defaults to manual")

    for name in ("start", "stop"):
        p = sub.add_parser(name)
        add_common_flags(p)
        p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("run-detail")
    add_common_flags(p)
    p.add_argument("run_id", help="Run id from `runs`")

    p = sub.add_parser("solutions")
    add_common_flags(p)
    p.add_argument("--unmanaged-only", action="store_true", help="List only unmanaged solutions")
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("solution-components")
    add_common_flags(p)
    p.add_argument("--solution", required=True, help="Solution unique name")
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("env-vars")
    add_common_flags(p)
    p.add_argument("--solution", help="Limit to environment variables that are components of this solution")
    p.add_argument("--reveal-secret", action="store_true", help="Show Secret-type values (Key Vault references) instead of masking them; never prints the Key Vault secret itself")
    p.add_argument("--json", action="store_true", help="Print JSON instead of compact table")

    p = sub.add_parser("env-var-get")
    add_common_flags(p)
    p.add_argument("schema_name", help="Environment variable schema name, e.g. acme_ApiBaseUrl")
    p.add_argument("--reveal-secret", action="store_true", help="Show the Secret-type value (Key Vault reference) instead of masking it")

    p = sub.add_parser("env-var-set")
    add_common_flags(p)
    p.add_argument("schema_name", help="Environment variable schema name")
    p.add_argument("value", help="New value (rejected for Secret-type variables — those are Key Vault-backed)")
    p.add_argument("--solution", help="Add/keep the value in this unmanaged solution so it ships via the DEV->PROD pipeline")
    p.add_argument("--dry-run", action="store_true", help="Validate (incl. Secret-type guard) without writing")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "pull":
            return cmd_pull(args)
        if args.command == "backup":
            return cmd_backup(args)
        if args.command == "status":
            return cmd_status(args)
        if args.command == "environments":
            return cmd_environments(args)
        if args.command == "flows":
            return cmd_flows(args)
        if args.command == "diff":
            return cmd_diff(args)
        if args.command == "verify":
            return cmd_verify(args)
        if args.command == "deploy":
            return cmd_deploy(args)
        if args.command == "create":
            return cmd_create(args)
        if args.command == "process-pull":
            return cmd_process_pull(args)
        if args.command == "process-diff":
            return cmd_process_diff(args)
        if args.command == "process-verify":
            return cmd_process_verify(args)
        if args.command == "process-deploy":
            return cmd_process_deploy(args)
        if args.command == "process-runs":
            return cmd_process_runs(args)
        if args.command == "process-run-detail":
            return cmd_process_run_detail(args)
        if args.command == "process-trigger-url":
            return cmd_process_trigger_url(args)
        if args.command == "start":
            return cmd_start_stop(args, True)
        if args.command == "stop":
            return cmd_start_stop(args, False)
        if args.command == "runs":
            return cmd_runs(args)
        if args.command == "run-detail":
            return cmd_run_detail(args)
        if args.command == "solutions":
            return cmd_solutions(args)
        if args.command == "solution-components":
            return cmd_solution_components(args)
        if args.command == "env-vars":
            return cmd_env_vars(args)
        if args.command == "env-var-get":
            return cmd_env_var_get(args)
        if args.command == "env-var-set":
            return cmd_env_var_set(args)
    except PowerAutomateError as exc:
        print(exc, file=sys.stderr)
        return 1
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
