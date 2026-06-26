---
name: power-automate-api-client
description: >
  Work with Microsoft Power Automate cloud flows through the power-automate
  CLI. Use for pull, diff, deploy, create, start, stop, run history, action
  diagnostics, or replacing a hosted MCP service with local open
  tooling.
---

# Power Automate API Client

Use this skill when changing or diagnosing Power Automate cloud flows from the
command line. The default tool is the `power-automate` CLI, not a hosted MCP service.

## Rules

- Do not use hosted MCP services for deployment unless explicitly requested.
- Never store OAuth access tokens. Short-lived tokens come only from an existing
  `az login` session and are never persisted.
- Resolve the non-secret target (environment_id, flow_id, dataverse_url,
  entra_tenant_id) in this order: CLI flags, then `POWER_AUTOMATE_*` environment
  variables, then a `profiles.json` file. See "Target Resolution" below.
- Authenticate with an existing `az login` session unless a future task adds
  service-principal support.
- Always run `deploy --dry-run` before a real deploy.
- A real deploy must create a live backup and then run `verify`.
- New flows: `create` posts a category-5 cloud flow into the DEV environment.
  Always pass `--solution` (the unmanaged solution, e.g.
  `<your-solution-unique-name>`) so it ships via the DEV->PROD pipeline. Create
  in DEV only; never create/deploy on PROD — PROD changes flow exclusively
  through the deployment pipeline.
- Use `power-automate-docs` for Microsoft documentation routing.
- Use `power-automate-run-forensics` before changing a flow to fix a runtime
  incident.
- Use `power-automate-expression-syntax` and
  `power-automate-action-configuration` before editing `definition`.

## Common Commands

```bash
power-automate status --profile acme
power-automate pull --profile acme --output ./flow.json
power-automate diff --profile acme flows/<flow>.json --unified
power-automate deploy --profile acme flows/<flow>.json --dry-run
power-automate deploy --profile acme flows/<flow>.json
power-automate create --profile acme flows/<flow>.json --name "<display>" --solution <your-solution-unique-name> [--activate] [--dry-run]
power-automate verify --profile acme flows/<flow>.json
power-automate environments --profile acme
power-automate flows --profile acme
power-automate flows --profile acme --all-environments
power-automate runs --profile acme --top 10
power-automate runs --profile acme --all-environments --top 5
power-automate runs --profile acme --all-environments --json
power-automate run-detail --profile acme <run-id>
```

### Solutions & environment variables

```bash
power-automate solutions --profile acme [--unmanaged-only]
power-automate solution-components --profile acme --solution <unique-name>
power-automate env-vars --profile acme [--solution <unique-name>]
power-automate env-var-get --profile acme acme_ApiBaseUrl
power-automate env-var-set --profile acme acme_ApiBaseUrl "https://api.example.com" --solution <unique-name> --dry-run
```

**Secret-type environment variables are masked** by default (Azure Key
Vault-backed); `--reveal-secret` shows only the Key Vault *reference*, never the
secret. `env-var-set` refuses Secret-type variables. For solution/ALM and
environment-variable work, use the `power-automate-solutions` skill.

Default discovery stays within the configured profile environment. Use
`--all-environments` only when the task explicitly needs every environment the
signed-in Azure user can see.

## Target Resolution

The CLI resolves the non-secret target values in this precedence order:

1. **CLI flags** — e.g. `--environment-id`, `--flow-id`, `--dataverse-url`,
   `--entra-tenant-id`.
2. **Environment variables**:
   - `POWER_AUTOMATE_ENVIRONMENT_ID`
   - `POWER_AUTOMATE_FLOW_ID`
   - `POWER_AUTOMATE_DATAVERSE_URL`
   - `POWER_AUTOMATE_ENTRA_TENANT_ID`
3. **profiles.json** at `~/.config/power-automate-cli/profiles.json`, selected
   with `--profile <profile>`:

```json
{
  "acme": {
    "environment_id": "00000000-0000-0000-0000-000000000000",
    "flow_id": "00000000-0000-0000-0000-000000000000",
    "dataverse_url": "https://org.crm4.dynamics.com",
    "entra_tenant_id": "00000000-0000-0000-0000-000000000000"
  }
}
```

`dataverse_url` and `entra_tenant_id` are optional. If `dataverse_url` is
absent, the CLI attempts discovery from the Power Platform environment metadata.

Short-lived OAuth tokens are never stored in any of these locations — they are
sourced exclusively from your current `az login` session.
