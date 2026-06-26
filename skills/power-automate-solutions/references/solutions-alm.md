# Solutions & ALM reference

Routing notes and stable facts for Power Platform solution work. Verify exact
current behavior against Microsoft Learn when it matters.

## Solution types

- **Unmanaged** — the editable source. Lives in DEV. Components can be added,
  edited, removed. This is what you build in.
- **Managed** — the deployed, locked result. Lives in TEST/PROD. Imported from
  an exported managed solution; not edited in place.
- **Default / Common Data Services Default Solution** — catch-all for
  customizations not yet assigned to a solution. Avoid shipping from here; put
  flows in a named unmanaged solution so they move through the pipeline.

## Environment variables

A variable has a **definition** (`environmentvariabledefinition`: `schemaname`,
`displayname`, `type`, optional `defaultvalue`) and a per-environment **value**
(`environmentvariablevalue`: `value`). Effective value = the environment's value
if set, otherwise the default.

Types (`type` option set):

| Code | Type | Notes |
|---|---|---|
| 100000000 | String | Plain text (URLs, names). Not a secret store — but can still be sensitive config. |
| 100000001 | Number | |
| 100000002 | Boolean | |
| 100000003 | JSON | Structured config. |
| 100000004 | Data Source | Connector data-source binding. |
| 100000005 | **Secret** | **Azure Key Vault-backed.** The stored value is a Key Vault *reference*, not the secret. Set/rotate in Key Vault + portal, not via plain values. |

ALM rule: add the **definition** to the solution; set the **value** per
environment (DEV/PROD differ). The CLI's `env-var-set --solution <name>` keeps
the value associated with the solution.

## Solution component types (common codes)

Seen in `solution-components`:

| Code | Component |
|---|---|
| 1 | Entity (table) |
| 29 | Workflow / Cloud flow |
| 31 | Report |
| 60 | SystemForm |
| 61 | WebResource |
| 62 | SiteMap |
| 90 | PluginAssembly |
| 91 | SDKMessageProcessingStep |
| 92 | ServiceEndpoint |
| 300 | CanvasApp |
| 380 | EnvironmentVariableDefinition |
| 381 | EnvironmentVariableValue |
| 10112 | ConnectionReference |

## Connection references

A `connectionreference` decouples a flow from a specific connection so the same
solution can bind to different connections per environment. They appear as
component type 10112 and in the flow's `connectionReferences`. On import to a new
environment you (re)map them. See `power-automate-action-configuration` for the
in-flow `connectionReferences` shape.

## DEV -> PROD pipeline (high level)

1. Build/edit flows in an **unmanaged** solution in DEV.
2. Add environment variable **definitions** (with sensible DEV values) and
   connection references to the solution.
3. Export as **managed**; import into TEST/PROD.
4. On import, supply the target environment's **values** (env vars) and map
   **connection references**. Managed solution pipelines (Power Platform
   Pipelines) automate this.
5. Never hand-edit managed flows on PROD; change in DEV and re-ship.

## Microsoft Learn sources

- Solutions overview: https://learn.microsoft.com/en-us/power-apps/maker/data-platform/solutions-overview
- Environment variables: https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables
- Use Key Vault secrets in environment variables: https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables-azure-key-vault-secrets
- Connection references: https://learn.microsoft.com/en-us/power-apps/maker/data-platform/create-connection-reference
- Healthy ALM: https://learn.microsoft.com/en-us/power-platform/alm/
- Dataverse Web API (solutions/components): https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview
