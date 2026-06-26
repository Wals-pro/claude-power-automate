# Azure CLI Setup

The `power-automate` CLI does **not** ship its own login flow, app registration,
or service principal (as of v0.1). It authenticates by shelling out to the
Azure CLI (`az account get-access-token`) using your existing interactive
`az login` session. This page covers installing the Azure CLI, signing in to
the correct Microsoft Entra tenant, verifying that tokens are issued, the
permissions you need, and how to troubleshoot the common failures.

## How the CLI uses Azure

For each request, the CLI asks the Azure CLI for a short-lived OAuth access
token scoped to one of two resources:

| Resource | Used for |
|---|---|
| `https://<org>.crm*.dynamics.com` (your Dataverse environment URL) | Reading and patching solution cloud flows (Dataverse `workflow` rows) |
| `https://api.powerplatform.com/` | Listing environments, run history, and flow runs via the Power Platform API |

It does this by running, roughly:

```bash
az account get-access-token --resource <resource> --output json
# plus --tenant <entra-tenant-id> when an Entra tenant is configured
```

The returned token lives only in memory for the duration of the command. See
[No tokens are stored](#no-tokens-are-stored).

## 1. Install the Azure CLI

Install the official Microsoft `az` CLI for your platform.

### macOS (Homebrew)

```bash
brew update && brew install azure-cli
```

### Windows (winget or MSI)

```powershell
winget install --exact --id Microsoft.AzureCLI
```

Or download the MSI installer from the official docs:
<https://learn.microsoft.com/cli/azure/install-azure-cli-windows>

### Linux (Microsoft install script)

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

For RPM-based distros and manual steps, see:
<https://learn.microsoft.com/cli/azure/install-azure-cli-linux>

Full install reference: <https://learn.microsoft.com/cli/azure/install-azure-cli>

Verify the install:

```bash
az version
```

## 2. Sign in with `az login`

Sign in once with the Microsoft account that has access to the target Power
Platform environment:

```bash
az login
```

This opens a browser for interactive sign-in (including MFA / conditional
access if your tenant requires it). On headless machines, use a device code:

```bash
az login --use-device-code
```

### Different Entra tenant for the Power Platform environment

If the Power Platform environment lives in a **different** Microsoft Entra
tenant than your default Azure login, sign in against that tenant explicitly:

```bash
az login --tenant <entra-tenant-id>
```

Then tell the CLI to request tokens from that same tenant. This maps to the
`--entra-tenant-id` flag (or the `POWER_AUTOMATE_ENTRA_TENANT_ID` environment
variable / the `entra_tenant_id` profile field):

```bash
# Via flag
power-automate status --profile acme --entra-tenant-id <entra-tenant-id>

# Via environment variable
export POWER_AUTOMATE_ENTRA_TENANT_ID=<entra-tenant-id>
power-automate status --profile acme
```

When set, the CLI passes `--tenant <entra-tenant-id>` to every
`az account get-access-token` call so tokens are issued for the correct tenant.

> Use the tenant **ID** (a GUID), not the tenant domain, to avoid ambiguity
> when an account is a guest in multiple tenants.

## 3. Inspect and select your account

Show the currently active subscription and signed-in user:

```bash
az account show
```

List everything the account can see (subscriptions across tenants):

```bash
az account list --output table
```

If you have more than one subscription, set the active one. Token issuance for
Power Platform / Dataverse does not depend on the subscription, but a sensible
default avoids confusion:

```bash
az account set --subscription <subscription-id-or-name>
```

## 4. Verify token issuance

Confirm the Azure CLI can mint tokens for both resources the CLI uses. A
successful call prints a JSON object containing `accessToken`, `expiresOn`, and
`tenant`:

```bash
# Power Platform API
az account get-access-token --resource https://api.powerplatform.com/ --output json

# Dataverse (use your environment's org URL)
az account get-access-token --resource https://<org>.crm4.dynamics.com --output json
```

Add `--tenant <entra-tenant-id>` to either command if the environment is in a
non-default tenant. If both commands return a token, the `power-automate` CLI
will be able to authenticate.

## Required permissions and roles

Token issuance only proves *who* you are. To actually read and manage flows you
also need the right access **inside the Power Platform environment**:

- The signed-in user must be a **member of the target Power Platform
  environment** (have a security role assigned in that environment, e.g. via a
  Dataverse security role) with rights to read and manage the relevant cloud
  flows.
- To read a flow's **run history**, the account may need additional rights
  beyond just seeing flow metadata. If you can list a flow but cannot read its
  runs, the Power Platform API returns `ClientScopeAuthorizationFailed` — the
  CLI surfaces this on `power-automate runs` to mean *"you can see the flow but
  are not authorized to read its run history."* Ask an environment admin to
  grant the appropriate role (typically environment/maker access plus
  permission on the flow's owning solution).
- For **multi-environment scans** (`--all-environments`), the account only sees
  environments it has access to; environments it cannot read are reported as
  per-environment warnings (403 / 404 / no-Dataverse) instead of aborting the
  whole scan.

If you are missing access, contact your Power Platform / Microsoft 365
administrator — these roles are granted on the Microsoft side, not by this
tool.

## Troubleshooting

### `az: command not found` / `az` not on PATH

The Azure CLI is not installed or its install location is not on your `PATH`.
Reinstall per [step 1](#1-install-the-azure-cli) and open a new shell. The CLI
surfaces this as:

> Azure CLI `az` is not installed or not on PATH.

### Token request times out

The CLI aborts an `az` token call that takes too long and reports:

> Azure CLI token request timed out.

This usually means `az` is waiting on an interactive prompt (e.g. your session
expired and it wants you to re-authenticate). Run `az login` again
interactively, complete any browser/MFA step, then retry the command.

### Wrong tenant

Symptoms: tokens are issued but the CLI gets 403/404 from environments it
should see, or `az account show` shows a different tenant than the environment
lives in. Sign in to the correct tenant and request tokens there:

```bash
az login --tenant <entra-tenant-id>
power-automate status --profile acme --entra-tenant-id <entra-tenant-id>
```

### MFA / conditional access

If your tenant enforces MFA or conditional-access policies, `az login` must be
completed **interactively** so the policy challenge can be satisfied. Use:

```bash
az login                 # browser-based, satisfies MFA
az login --use-device-code   # for headless/SSH sessions
```

A non-interactive token request against a stale session will fail; the CLI
reports it as:

> Azure CLI could not provide a Microsoft access token. Run `az login` for the
> target tenant and retry.

### Multiple accounts / cached session confusion

If you have signed in with several accounts and the wrong one is active, clear
all cached credentials and sign in fresh with the correct account:

```bash
az account clear
az login --tenant <entra-tenant-id>
```

Then confirm the active context with `az account show`.

### `accessToken` missing from response

If `az` returns success but no token field, the CLI reports:

> Azure CLI token response did not contain accessToken.

This typically indicates an Azure CLI version issue — update with
`az upgrade` (or reinstall via [step 1](#1-install-the-azure-cli)) and retry.

## No tokens are stored

This tool stores **no secrets and no tokens**. Each access token is fetched
on demand from your existing `az login` session, held only in memory for the
lifetime of a single command, and discarded when the process exits. The only
things the CLI persists are non-secret targets (environment ID, flow ID,
Dataverse URL, Entra tenant ID) in a `profiles.json` file or environment
variables — none of which are credentials. Your Microsoft credentials are
managed entirely by the Azure CLI.

> Replace every `<placeholder>` above (`<org>`, `<entra-tenant-id>`,
> `<subscription-id-or-name>`) with your own values. Do not commit real
> tenant IDs, org GUIDs, or tokens.
