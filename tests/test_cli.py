from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from power_automate_cli import cli as pa  # noqa: E402
from power_automate_cli import config as pa_config  # noqa: E402


def response(body, status_code=200):
    r = Mock(status_code=status_code, text=json.dumps(body) if body is not None else "")
    r.json.return_value = body
    return r


class ClientDataTest(unittest.TestCase):
    def test_parse_clientdata_extracts_properties(self):
        raw = json.dumps({
            "properties": {
                "definition": {"actions": {"A": {}}},
                "connectionReferences": {"shared_x": {"connectionName": "x"}},
            },
            "schemaVersion": "1.0.0.0",
        })

        parsed = pa.parse_clientdata(raw)

        self.assertEqual(parsed["properties"]["definition"]["actions"], {"A": {}})

    def test_build_clientdata_preserves_existing_properties(self):
        existing = json.dumps({
            "properties": {
                "definition": {"old": True},
                "connectionReferences": {"old": True},
                "displayName": "Keep me",
            },
            "schemaVersion": "1.0.0.0",
        })
        artifact = {
            "definition": {"new": True},
            "connectionReferences": {"shared": {"connectionName": "c"}},
        }

        result = json.loads(pa.build_clientdata(existing, artifact))

        self.assertEqual(result["properties"]["definition"], {"new": True})
        self.assertEqual(result["properties"]["connectionReferences"], {"shared": {"connectionName": "c"}})
        self.assertEqual(result["properties"]["displayName"], "Keep me")

    def test_diff_artifacts_detects_connection_changes(self):
        live = {"definition": {"a": 1}, "connectionReferences": {"x": 1}}
        local = {"definition": {"a": 1}, "connectionReferences": {"x": 2}}

        result = pa.diff_artifacts(live, local)

        self.assertTrue(result["changed"])
        self.assertFalse(result["sections"]["definition"]["changed"])
        self.assertTrue(result["sections"]["connectionReferences"]["changed"])

    def test_artifact_from_process_flow_extracts_definition(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1", flow_id="flow-1")
        flow = {
            "name": "flow-1",
            "properties": {
                "displayName": "Customer folders",
                "state": "Started",
                "definition": {"actions": {"A": {}}},
                "connectionReferences": {"shared_x": {"connectionName": "c"}},
            },
        }

        artifact = pa.artifact_from_process_flow(config, flow)

        self.assertEqual(artifact["flowName"], "flow-1")
        self.assertEqual(artifact["displayName"], "Customer folders")
        self.assertEqual(artifact["definition"]["actions"], {"A": {}})
        self.assertEqual(artifact["connectionReferences"]["shared_x"]["connectionName"], "c")

    def test_build_process_flow_preserves_existing_properties(self):
        existing = {
            "name": "flow-1",
            "properties": {
                "displayName": "Old",
                "environment": {"name": "env-1"},
                "definition": {"old": True},
                "connectionReferences": {"old": True},
                "state": "Started",
            },
        }
        artifact = {
            "displayName": "New",
            "definition": {"new": True},
            "connectionReferences": {"shared": {"connectionName": "c"}},
        }

        result = pa.build_process_flow(existing, artifact)

        self.assertEqual(result["properties"]["definition"], {"new": True})
        self.assertEqual(result["properties"]["connectionReferences"], {"shared": {"connectionName": "c"}})
        self.assertEqual(result["properties"]["displayName"], "New")
        self.assertEqual(result["properties"]["environment"], {"name": "env-1"})
        self.assertEqual(result["properties"]["workflowEntityId"], "flow-1")
        self.assertEqual(result["telemetryMetadata"], {"modifiedSources": "Portal"})


class ConfigTest(unittest.TestCase):
    def test_load_config_uses_resolver_fields(self):
        args = Mock(
            profile="acme",
            environment_id=None,
            flow_id=None,
            dataverse_url=None,
            entra_tenant_id=None,
        )

        values = {
            "environment_id": "env-1",
            "flow_id": "flow-1",
            "dataverse_url": "https://org.crm4.dynamics.com",
            "entra_tenant_id": "tenant-1",
        }

        def fake_resolve(profile, field):
            self.assertEqual(profile, "acme")
            return values[field]

        with patch.object(pa, "resolve_field", side_effect=fake_resolve):
            config = pa.load_pa_config(args)

        self.assertEqual(config.environment_id, "env-1")
        self.assertEqual(config.flow_id, "flow-1")
        self.assertEqual(config.dataverse_url, "https://org.crm4.dynamics.com")
        self.assertEqual(config.entra_tenant_id, "tenant-1")


class ClientTest(unittest.TestCase):
    def test_discover_dataverse_url_uses_environment_url(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1", flow_id="flow-1")
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        response = Mock(status_code=200, text='{"url":"https://org.crm4.dynamics.com"}')
        response.json.return_value = {"url": "https://org.crm4.dynamics.com"}
        session = Mock()
        session.request.return_value = response

        client = pa.PowerAutomateClient(config, token_provider, session)

        self.assertEqual(client.discover_dataverse_url(), "https://org.crm4.dynamics.com")

    def test_list_environments_follows_next_link(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1")
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.side_effect = [
            response({"value": [{"name": "env-1"}], "@odata.nextLink": "https://next.example/page2"}),
            response({"value": [{"name": "env-2"}]}),
        ]
        client = pa.PowerAutomateClient(config, token_provider, session)

        environments = client.list_environments()

        self.assertEqual([env["name"] for env in environments], ["env-1", "env-2"])
        self.assertEqual(session.request.call_args_list[1].args[1], "https://next.example/page2")

    def test_list_flows_queries_cloud_flows_and_excludes_off_by_default(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1")
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.return_value = response({"value": [{"workflowid": "flow-1", "name": "Flow"}]})
        client = pa.PowerAutomateClient(config, token_provider, session)

        flows = client.list_flows({"name": "env-1", "url": "https://org.crm4.dynamics.com"})

        self.assertEqual(flows[0]["_environmentId"], "env-1")
        requested_url = session.request.call_args.args[1]
        self.assertIn("workflows?", requested_url)
        self.assertIn("category+eq+5", requested_url)
        self.assertIn("statecode+eq+1", requested_url)

    def test_list_flows_include_off_removes_state_filter(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1")
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.return_value = response({"value": []})
        client = pa.PowerAutomateClient(config, token_provider, session)

        client.list_flows({"name": "env-1", "url": "https://org.crm4.dynamics.com"}, include_off=True)

        requested_url = session.request.call_args.args[1]
        self.assertIn("category+eq+5", requested_url)
        self.assertNotIn("statecode+eq+1", requested_url)

    def test_process_flow_uses_flow_service_resource(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1", flow_id="flow-1")
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.return_value = response({"name": "flow-1", "properties": {}})
        client = pa.PowerAutomateClient(config, token_provider, session)

        client.get_process_flow()

        token_provider.token_for.assert_called_with("https://service.flow.microsoft.com/")
        requested_url = session.request.call_args.args[1]
        self.assertIn("/providers/Microsoft.ProcessSimple/environments/env-1/flows/flow-1?", requested_url)
        self.assertIn("api-version=2016-11-01", requested_url)

    def test_update_process_flow_uses_environment_api_patch(self):
        config = pa.PowerAutomateConfig(
            tenant="t",
            environment_id="Default-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeff",
            flow_id="flow-1",
        )
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.return_value = response({"name": "flow-1", "properties": {}})
        client = pa.PowerAutomateClient(config, token_provider, session)

        client.update_process_flow({"name": "flow-1", "properties": {}})

        self.assertEqual(session.request.call_args.args[0], "PATCH")
        requested_url = session.request.call_args.args[1]
        self.assertIn(
            "https://defaultaaaaaaaabbbbccccddddeeeeeeeeee.ff.environment.api.powerplatform.com",
            requested_url,
        )
        self.assertIn("/powerautomate/flows/flow-1?", requested_url)

    def test_process_trigger_callback_url_posts_to_manual_trigger(self):
        config = pa.PowerAutomateConfig(tenant="t", environment_id="env-1", flow_id="flow-1")
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.return_value = response({"value": "https://example.test/trigger"})
        client = pa.PowerAutomateClient(config, token_provider, session)

        result = client.process_trigger_callback_url("manual")

        self.assertEqual(result["value"], "https://example.test/trigger")
        self.assertEqual(session.request.call_args.args[0], "POST")
        requested_url = session.request.call_args.args[1]
        self.assertIn("/triggers/manual/listCallbackUrl?", requested_url)
        self.assertNotIn("?api-version=2016-11-01/triggers/", requested_url)

    def test_environment_api_host_uses_first_30_and_last_2_hex_chars(self):
        self.assertEqual(
            pa.environment_api_host("Default-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeff"),
            "https://defaultaaaaaaaabbbbccccddddeeeeeeeeee.ff.environment.api.powerplatform.com",
        )
        self.assertEqual(
            pa.environment_api_host("12345678-90ab-cdef-1234-567890abcd99"),
            "https://1234567890abcdef1234567890abcd.99.environment.api.powerplatform.com",
        )

    def test_scan_flows_preserves_warnings_during_all_environment_scan(self):
        client = Mock()
        client.list_environments.return_value = [
            {"name": "env-ok", "url": "https://ok.crm4.dynamics.com"},
            {"name": "env-denied", "url": "https://denied.crm4.dynamics.com"},
        ]

        def fake_list_flows(env, include_off=False):
            if env["name"] == "env-denied":
                raise pa.PowerAutomateError("HTTP 403")
            return [{"workflowid": "flow-1", "name": "Flow", "statecode": 1}]

        client.list_flows.side_effect = fake_list_flows

        result = pa.scan_flows(client, all_environments=True, include_off=False)

        self.assertEqual(result["flows"][0]["flowId"], "flow-1")
        self.assertEqual(result["warnings"][0]["environmentId"], "env-denied")

    def test_cmd_runs_all_environments_outputs_valid_json_with_warnings(self):
        fake_client = Mock()
        fake_client.list_environments.return_value = [
            {"name": "env-ok", "url": "https://ok.crm4.dynamics.com"},
            {"name": "env-denied", "url": "https://denied.crm4.dynamics.com"},
        ]

        def fake_list_flows(env, include_off=False):
            if env["name"] == "env-denied":
                raise pa.PowerAutomateError("HTTP 403")
            return [{"workflowid": "flow-1", "name": "Flow", "statecode": 1}]

        fake_client.list_flows.side_effect = fake_list_flows
        fake_client.list_runs.return_value = {
            "value": [{
                "name": "run-1",
                "properties": {
                    "status": "Succeeded",
                    "startTime": "2026-05-26T10:00:00Z",
                    "endTime": "2026-05-26T10:00:05Z",
                },
            }]
        }
        args = Mock(all_environments=True, include_off=False, top=5, json=True)

        out = StringIO()
        with patch.object(pa, "build_client", return_value=fake_client), redirect_stdout(out):
            rc = pa.cmd_runs(args)

        payload = json.loads(out.getvalue())
        self.assertEqual(rc, 0)
        self.assertEqual(payload["runs"][0]["runId"], "run-1")
        self.assertEqual(payload["warnings"][0]["environmentId"], "env-denied")

    def test_create_workflow_posts_cloud_flow_into_solution(self):
        config = pa.PowerAutomateConfig(
            tenant="t", environment_id="env-1", dataverse_url="https://org.crm4.dynamics.com"
        )
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.return_value = response(
            {"workflowid": "new-flow-1", "name": "FrozenZone"}, status_code=201
        )
        client = pa.PowerAutomateClient(config, token_provider, session)

        created = client.create_workflow(
            name="FrozenZone",
            clientdata="{}",
            description="daily reminder",
            solution_unique_name="ContosoAutomations",
        )

        self.assertEqual(created["workflowid"], "new-flow-1")
        self.assertEqual(session.request.call_args.args[0], "POST")
        requested_url = session.request.call_args.args[1]
        self.assertTrue(requested_url.endswith("/api/data/v9.2/workflows"))
        body = session.request.call_args.kwargs["json"]
        self.assertEqual(body["category"], 5)
        self.assertEqual(body["type"], 1)
        self.assertEqual(body["primaryentity"], "none")
        self.assertEqual(body["name"], "FrozenZone")
        headers = session.request.call_args.kwargs["headers"]
        self.assertEqual(headers["Prefer"], "return=representation")
        self.assertEqual(headers["MSCRM.SolutionUniqueName"], "ContosoAutomations")

    def test_create_workflow_activate_sets_state_on_new_id(self):
        config = pa.PowerAutomateConfig(
            tenant="t", environment_id="env-1", dataverse_url="https://org.crm4.dynamics.com"
        )
        token_provider = Mock()
        token_provider.token_for.return_value = "token"
        session = Mock()
        session.request.side_effect = [
            response({"workflowid": "new-flow-1"}, status_code=201),
            response(None, status_code=204),
        ]
        client = pa.PowerAutomateClient(config, token_provider, session)

        client.create_workflow(name="X", clientdata="{}", activate=True)

        self.assertEqual(session.request.call_count, 2)
        self.assertEqual(session.request.call_args_list[1].args[0], "PATCH")
        self.assertIn("workflows(new-flow-1)", session.request.call_args_list[1].args[1])
        patch_body = session.request.call_args_list[1].kwargs["json"]
        self.assertEqual(patch_body["statecode"], 1)
        self.assertEqual(patch_body["statuscode"], 2)

    def test_format_table_handles_missing_values(self):
        table = pa.format_table([{"flowName": "Flow"}], ["environmentName", "flowName", "error"])

        self.assertIn("environmentName", table)
        self.assertIn("Flow", table)


class AuthTest(unittest.TestCase):
    def test_azure_cli_token_provider_reports_missing_az(self):
        provider = pa.AzureCliTokenProvider()
        with patch.object(subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaises(pa.PowerAutomateError) as ctx:
                provider.token_for("https://api.powerplatform.com/")
        self.assertIn("Azure CLI", str(ctx.exception))

    def test_azure_cli_token_provider_caches_token(self):
        provider = pa.AzureCliTokenProvider()
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"accessToken": "token-1"}),
            stderr="",
        )
        with patch.object(subprocess, "run", return_value=completed) as mock_run:
            self.assertEqual(provider.token_for("https://api.powerplatform.com/"), "token-1")
            self.assertEqual(provider.token_for("https://api.powerplatform.com/"), "token-1")
        self.assertEqual(mock_run.call_count, 1)


class ProfileResolveTest(unittest.TestCase):
    def tearDown(self):
        pa_config.register_profile_resolver(None)

    def test_profile_specific_env_var_wins_over_generic(self):
        with patch.dict(os.environ, {
            "POWER_AUTOMATE_ACME_ENVIRONMENT_ID": "env-acme",
            "POWER_AUTOMATE_ENVIRONMENT_ID": "env-generic",
        }, clear=True):
            self.assertEqual(pa_config.resolve_field("acme", "environment_id"), "env-acme")
            self.assertEqual(pa_config.resolve_field("other", "environment_id"), "env-generic")

    def test_flat_profiles_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "profiles.json"
            cfg.write_text(json.dumps({"acme": {"flow_id": "flow-acme"}}), encoding="utf-8")
            with patch.dict(os.environ, {"POWER_AUTOMATE_CONFIG": str(cfg)}, clear=True):
                self.assertEqual(pa_config.resolve_field("acme", "flow_id"), "flow-acme")
                self.assertIsNone(pa_config.resolve_field("acme", "dataverse_url"))

    def test_profiles_wrapper_form_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "profiles.json"
            cfg.write_text(json.dumps({"profiles": {"acme": {"flow_id": "flow-wrapped"}}}), encoding="utf-8")
            with patch.dict(os.environ, {"POWER_AUTOMATE_CONFIG": str(cfg)}, clear=True):
                self.assertEqual(pa_config.resolve_field("acme", "flow_id"), "flow-wrapped")

    def test_registered_resolver_takes_precedence(self):
        pa_config.register_profile_resolver(
            lambda profile, field: "from-hook" if field == "environment_id" else None
        )
        with patch.dict(os.environ, {"POWER_AUTOMATE_ENVIRONMENT_ID": "from-env"}, clear=True):
            self.assertEqual(pa_config.resolve_field("acme", "environment_id"), "from-hook")
            self.assertIsNone(pa_config.resolve_field("acme", "flow_id"))

    def test_unknown_field_raises(self):
        with self.assertRaises(ValueError):
            pa_config.resolve_field("acme", "not_a_field")


if __name__ == "__main__":
    unittest.main()
