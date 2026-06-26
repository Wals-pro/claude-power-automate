# claude-power-automate

**A Claude Code suite for Microsoft Power Automate development** — eight focused
Agent Skills plus a local, open CLI for inspecting and deploying cloud flows.
No third-party hosted service, no stored secrets.

[![CI](https://github.com/Wals-pro/claude-power-automate/actions/workflows/ci.yml/badge.svg)](https://github.com/Wals-pro/claude-power-automate/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Status: Beta](https://img.shields.io/badge/status-beta%20v0.1-orange.svg)

> ### ⚠️ Beta (v0.3)
> This is early, pre-1.0 software. The CLI surface, command output, skill
> contents, and config schema **may change without notice** between 0.x
> releases. Pin to a tag if you depend on it.
>
> Not affiliated with or endorsed by Microsoft or Anthropic. "Power Automate",
> "Power Platform", and "Dataverse" are trademarks of Microsoft; "Claude" is a
> trademark of Anthropic.

---

## What's in the box

This suite gives an AI coding agent (Claude Code) — and you, at the terminal —
everything needed to build, diagnose, and ship Power Automate **cloud flows**
from local artifacts, the same way teams already manage code.

- **`power-automate` CLI** — a local Python client backed by the Dataverse Web
  API and the Power Platform API. Pull a live flow to a JSON artifact, diff it,
  back it up, deploy it (with verify), create new solution-aware flows, list
  environments/flows, and read run history for forensics.
- **Eight Claude Code Agent Skills** — domain knowledge and guardrails that make
  Claude reliable on Power Automate work instead of guessing.

### The skills

| Skill | Use it for |
|---|---|
| **power-automate-api-client** | Driving the `power-automate` CLI: pull, diff, deploy, create, start/stop, run history, action diagnostics. |
| **power-automate-docs** | A documentation router that points each task to the correct official Microsoft Learn source. |
| **power-automate-reference** | The complete WDL function namespace, trigger/action `type` values, and workflow-definition schema — embedded so the agent verifies names instead of inventing functions. |
| **power-automate-expression-syntax** | Writing/validating expressions, distinguishing Workflow Definition Language (cloud flows) from Power Fx (desktop flows). |
| **power-automate-action-configuration** | Configuring triggers/actions and `connectionReferences` (Outlook, SharePoint, Dataverse, HTTP) from connector references. |
| **power-automate-workflow-patterns** | Designing flow architectures — triggers, scopes, error handling, and translating n8n-style routines into Power Automate. |
| **power-automate-run-forensics** | Read-only incident diagnosis from run history before changing any flow code. |
| **power-automate-solutions** | Solutions and solution-scoped environment variables (incl. Key Vault secrets), connection references, and the DEV → PROD pipeline. |

---

## Why

- **Local and open.** The runtime is plain Python plus official Microsoft APIs.
  No subscription and no session with a third-party hosted service are required
  to deploy.
- **No secrets, ever.** Short-lived OAuth tokens come exclusively from your
  existing `az login` session. The tool stores nothing. The only thing it reads
  is the *non-secret* target of a command (which environment / flow).
- **Versioned flows.** Treat `definition` + `connectionReferences` as artifacts
  you can diff, review, back up, and deploy through a DEV → PROD pipeline.

---

## Install

### CLI

Requires Python 3.10+ and the [Azure CLI](docs/az-cli-setup.md).

```bash
pip install "git+https://github.com/Wals-pro/claude-power-automate@v0.1.0"
power-automate --help
```

Or from a clone:

```bash
git clone https://github.com/Wals-pro/claude-power-automate
cd claude-power-automate
pip install -e .
```

### Skills (Claude Code)

Copy (or symlink) the skills you want into your Claude Code skills directory,
e.g. your project's `.claude/skills/`:

```bash
cp -R skills/power-automate-* /path/to/your/project/.claude/skills/
```

Claude will load each `SKILL.md` and pull in its `references/` on demand.

---

## Quickstart

```bash
# 1. Authenticate (once) with an account that can manage the environment.
az login            # see docs/az-cli-setup.md for cross-tenant / MFA notes

# 2. Point the CLI at a target (flags, env vars, or a profile — see below).
export POWER_AUTOMATE_ENVIRONMENT_ID="00000000-0000-0000-0000-000000000000"
export POWER_AUTOMATE_FLOW_ID="11111111-1111-1111-1111-111111111111"

# 3. Inspect, then pull the live flow to a local artifact.
power-automate status --profile acme
power-automate pull   --profile acme --output flow.json

# 4. Edit flow.json, preview the change, deploy safely (backup + verify).
power-automate diff   --profile acme flow.json --unified
power-automate deploy --profile acme flow.json --dry-run
power-automate deploy --profile acme flow.json
```

`deploy` always reads the live flow first, writes a timestamped backup under
`.power-automate-backups/<profile>/`, patches only the flow definition, and then
reads the flow back to verify the result.

---

## Configuring targets

The CLI never stores secrets. It only resolves the **non-secret target** of a
command — `environment_id`, `flow_id`, `dataverse_url`, `entra_tenant_id` — in
this precedence order:

1. **CLI flags:** `--environment-id`, `--flow-id`, `--dataverse-url`, `--entra-tenant-id`
2. **Environment variables:** `POWER_AUTOMATE_ENVIRONMENT_ID`,
   `POWER_AUTOMATE_FLOW_ID`, `POWER_AUTOMATE_DATAVERSE_URL`,
   `POWER_AUTOMATE_ENTRA_TENANT_ID` (also `POWER_AUTOMATE_<PROFILE>_<FIELD>`)
3. **`profiles.json`** at `~/.config/power-automate-cli/profiles.json` (override
   with `$POWER_AUTOMATE_CONFIG`), selected with `--profile`:

```json
{
  "acme": {
    "environment_id": "00000000-0000-0000-0000-000000000000",
    "flow_id": "11111111-1111-1111-1111-111111111111",
    "dataverse_url": "https://org.crm4.dynamics.com",
    "entra_tenant_id": "22222222-2222-2222-2222-222222222222"
  }
}
```

`dataverse_url` is optional — if omitted, the CLI discovers it from the Power
Platform environment metadata. `entra_tenant_id` is only needed when the
environment lives in a different Entra tenant than your default `az` login.

### Embedding

Host applications can inject their own (e.g. secrets-manager-backed) lookup
without this package depending on it:

```python
from power_automate_cli.config import register_profile_resolver

register_profile_resolver(lambda profile, field: my_store.get(profile, field))
```

---

## Command reference

| Command | What it does |
|---|---|
| `status` | Show the configured flow's name, state, and last-modified time. |
| `pull` / `backup` | Write the live flow's `definition` + `connectionReferences` to JSON. |
| `diff` / `verify` | Compare a local artifact against the live flow (`--unified` for full diffs). |
| `deploy` | Diff → backup → patch → verify. Use `--dry-run` first. |
| `create` | Create a new category-5 cloud flow (use `--solution`, deploy to DEV only). |
| `environments` / `flows` | List environments / cloud flows (`--all-environments` for a user-wide scan). |
| `runs` / `run-detail` | Read run history and per-action detail for forensics. |
| `start` / `stop` | Turn a flow on or off. |
| `solutions` / `solution-components` | List Power Platform solutions; inspect a solution's components. |
| `env-vars` / `env-var-get` | List / show solution environment variables (Secret-type values masked). |
| `env-var-set` | Set a non-secret environment variable value (`--solution`, `--dry-run`); refuses Secret-type. |
| `process-*` | The same operations for non-solution ("process") cloud flows. |

Run `power-automate <command> --help` for the full flag set.

### Solutions & environment variables

The suite is built for solution-based ALM. List solutions and inspect their
components, then read and set the **environment variables** that parameterize a
solution across DEV/PROD:

```bash
power-automate solutions --profile acme
power-automate solution-components --profile acme --solution acme_CoreAutomation
power-automate env-vars --profile acme --solution acme_CoreAutomation
power-automate env-var-set --profile acme acme_ApiBaseUrl "https://api.example.com" --solution acme_CoreAutomation --dry-run
```

> **Secrets stay secret.** Secret-type environment variables are Azure Key
> Vault-backed; the CLI **masks** their values by default (`--reveal-secret`
> shows only the Key Vault reference, never the secret), and `env-var-set`
> **refuses** Secret-type variables so a secret never reaches your shell history
> or Dataverse as plaintext.

See **[docs/az-cli-setup.md](docs/az-cli-setup.md)** for authentication and
**[docs/operations.md](docs/operations.md)** for the deploy runbook.

---

## Development

```bash
pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
```

The test suite mocks all network and Azure CLI calls — no live tenant required.

## License

[MIT](LICENSE) © Wals.pro. See [CHANGELOG.md](CHANGELOG.md) for release notes.
