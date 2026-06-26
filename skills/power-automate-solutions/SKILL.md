---
name: power-automate-solutions
description: >
  Work with Microsoft Power Platform solutions and solution-scoped environment
  variables from the command line. Use for listing solutions, inspecting
  solution components, reading and setting environment variable values
  (String/Number/Boolean/JSON), handling Secret (Azure Key Vault) variables
  safely, connection references, and shipping flows through a DEV -> PROD
  pipeline via the power-automate CLI.
---

# Power Automate Solutions & Environment Variables

Use this skill for application lifecycle management (ALM) of Power Platform
cloud flows: solutions, environment variables, and the DEV -> PROD pipeline.
The default tool is the `power-automate` CLI.

## Core idea

- **Solutions** are the unit of deployment. Unmanaged solutions hold the
  editable source in DEV; managed solutions are the deployed result in PROD.
- **Environment variables** parameterize a solution so the same flow behaves
  correctly across environments (e.g. a different API base URL or record id in
  DEV vs PROD). A variable has a **definition** (schema name, type, optional
  default) and, per environment, a **value**.
- Create/edit flows in DEV inside an unmanaged solution, then ship the solution
  through the pipeline. Never edit on PROD directly.

## Commands

```bash
# Solutions
power-automate solutions --profile acme                 # list (managed + unmanaged)
power-automate solutions --profile acme --unmanaged-only
power-automate solution-components --profile acme --solution <unique-name>

# Environment variables
power-automate env-vars --profile acme                  # all definitions + current/default values
power-automate env-vars --profile acme --solution <unique-name>   # only this solution's variables
power-automate env-var-get --profile acme acme_ApiBaseUrl
power-automate env-var-set --profile acme acme_ApiBaseUrl "https://api.example.com" --solution <unique-name> --dry-run
power-automate env-var-set --profile acme acme_ApiBaseUrl "https://api.example.com" --solution <unique-name>
```

Add a new flow to a solution at creation time so it ships through the pipeline:

```bash
power-automate create --profile acme flow.json --name "My Flow" --solution <unique-name> --dry-run
```

## Secret-handling rules (read before touching values)

- **Secret-type** environment variables are backed by **Azure Key Vault**. The
  CLI **masks** their values by default (`<secret · Azure Key Vault-backed>`).
  `--reveal-secret` shows only the Key Vault *reference*, never the secret value
  itself.
- `env-var-set` **refuses** Secret-type variables. Configure those in the Power
  Platform portal or via a Key Vault reference — never pass a secret as a CLI
  argument (it would land in shell history, logs, and Dataverse as plaintext).
- Never commit real environment variable values, schema names tied to a real
  customer, or GUIDs into source control. Use placeholders.

## Procedure

1. `solutions` to find the target unmanaged solution.
2. `solution-components --solution <unique-name>` to see what it contains
   (flows = "Workflow / Cloud flow", env vars = "EnvironmentVariableDefinition",
   connection references, etc.).
3. `env-vars --solution <unique-name>` to review the variables the flow depends
   on; confirm types and which have values in this environment.
4. For non-secret config, `env-var-set ... --dry-run` then the real set,
   passing `--solution` so the value belongs to the solution.
5. For secret config, set it in the portal / Key Vault; only confirm presence
   with `env-var-get` (masked).
6. Read `references/solutions-alm.md` for solution types, component-type codes,
   environment variable types, connection references, and DEV -> PROD notes.

## Related skills

- `power-automate-api-client` for pull/diff/deploy/verify of the flow itself.
- `power-automate-action-configuration` for `connectionReferences` inside the
  flow definition.
- `power-automate-run-forensics` when a deployed flow misbehaves per environment
  (often a missing or wrong environment variable value).
