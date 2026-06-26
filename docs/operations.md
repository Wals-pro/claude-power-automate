# Power Automate API Client

Use the `power-automate` CLI when a solution-aware Power Automate cloud flow
must be inspected or deployed without Flow Studio or any hosted MCP. The client
is local, uses open Python dependencies only, and authenticates through an
existing Azure CLI user session.

For Claude Code workflow work, pair this runbook with the `power-automate-*`
skills. Those skills route Microsoft documentation, expression syntax,
connector/action configuration, workflow patterns, and run forensics. The
patterns translate well from n8n-style workflows.

## Target Resolution

The CLI resolves the non-secret target (`environment_id`, `flow_id`,
`dataverse_url`, `entra_tenant_id`) in this order:

1. CLI flags (e.g. `--environment-id`, `--flow-id`)
2. `POWER_AUTOMATE_*` environment variables
3. A `profiles.json` file at `~/.config/power-automate-cli/profiles.json`

```json
{
  "profiles": {
    "acme": {
      "environment_id": "00000000-0000-0000-0000-000000000000",
      "default_flow_id": "00000000-0000-0000-0000-000000000000",
      "dataverse_url": "https://org.crm4.dynamics.com",
      "entra_tenant_id": "00000000-0000-0000-0000-000000000000"
    }
  }
}
```

`environment_id` and `default_flow_id` are stable identifiers and are not
secrets. `dataverse_url` is optional; if omitted, the client tries to discover
it from the Power Platform environment metadata. Short-lived OAuth tokens come
only from an existing `az login` session and are never stored.

## Authentication

Sign in once with the Microsoft account that has rights to the environment:

```bash
az login
```

The client calls `az account get-access-token` for Dataverse and
`https://api.powerplatform.com/`. No app registration or Flow Studio token is
required.

## Commands

```bash
power-automate status --profile acme
power-automate environments --profile acme
power-automate flows --profile acme
power-automate flows --profile acme --all-environments
power-automate pull --profile acme --output ./flow.json
power-automate diff --profile acme flows/my-flow.json --unified
power-automate deploy --profile acme flows/my-flow.json --dry-run
power-automate deploy --profile acme flows/my-flow.json
power-automate start --profile acme
power-automate runs --profile acme --top 10
power-automate runs --profile acme --all-environments --top 5
power-automate runs --profile acme --all-environments --json
power-automate run-detail --profile acme <run-id>
```

`deploy` always reads the live flow first, writes a timestamped backup under
`.power-automate-backups/<profile>/`, patches only `clientdata`, and then reads
the flow back for verification.

Discovery commands use the signed-in Azure CLI user. By default, `flows` and
`runs` stay in the configured profile environment. Add `--all-environments`
only when you need a user-wide scan across every Power Platform environment the
signed-in account can see. Multi-environment scans collect per-environment
warnings for 403/404/no-Dataverse cases instead of aborting the whole scan.
`ClientScopeAuthorizationFailed` on `runs` means the account can see flow
metadata but does not have permission to read run history for that flow.

## API Shape

Solution cloud flows are stored in Dataverse as `workflow` rows. The flow
definition and connection references are stored as string-encoded JSON in the
`clientdata` column. The local artifact shape remains compatible with the
existing Flow Studio export:

```json
{
  "environmentName": "<environment-id>",
  "flowName": "<workflow-id>",
  "displayName": "<flow name>",
  "definition": {},
  "connectionReferences": {}
}
```

Run history is read through the Power Platform API. Detailed action history
uses the documented workflows agent endpoint and may require the same user to
have sufficient environment/run-history permissions.
