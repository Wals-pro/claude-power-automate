# Triggers & actions — JSON `type` reference

Canonical source (open for full inputs/outputs per type):
https://learn.microsoft.com/en-us/azure/logic-apps/logic-apps-workflow-actions-triggers

Every trigger and action object carries a `type` (the values below), plus
`inputs` and (for actions) `runAfter`. Use the exact `type` string.

## Triggers

| `type` | Purpose |
|---|---|
| `Recurrence` | Fire on a schedule (uses a `recurrence` object). |
| `Request` | Callable HTTP endpoint — "manual" / when-an-HTTP-request-is-received. |
| `Http` | Poll an HTTP/HTTPS endpoint on a schedule. |
| `HttpWebhook` | Subscribe/unsubscribe to an external service for push callbacks. |
| `ApiConnection` | Poll a Microsoft-managed connector endpoint. |
| `ApiConnectionWebhook` | Push notifications from a managed connector via callback. |

> Flows invoked from a **Power Apps** canvas app use the **Power Apps (V2)**
> trigger, not a bare `Request`/`Http` trigger — otherwise the app can't bind to
> it. Pick the connector-specific trigger the host expects.

## Control actions

| `type` | Purpose |
|---|---|
| `If` | Conditional branch (true/false). |
| `Switch` | Route to a case by expression value. |
| `Scope` | Group actions; evaluate their combined status (error handling). |
| `Foreach` | Loop over array items (parallel by default). |
| `Until` | Loop until a condition is true. |
| `Terminate` | Stop the run with a status. |
| `InitializeVariable` / `SetVariable` / `IncrementVariable` / `AppendToArrayVariable` | Variable lifecycle. |

## Data / built-in actions

| `type` | Purpose |
|---|---|
| `Compose` | Produce a single output from inputs. Don't stack these to fake logic. |
| `ParseJson` | Typed tokens from a JSON payload. |
| `Select` | Map/reshape array items. |
| `Query` | Filter array items. |
| `Join` | Join an array into a delimited string. |
| `Table` | Build a CSV/HTML table from an array. |
| `Http` | Send an HTTP/HTTPS request. |
| `Response` | Reply to an incoming `Request` trigger. |
| `Workflow` | Call a child flow / nested workflow. |
| `Function` | Call an Azure Function. |
| `JavaScriptCode` | Run an inline JavaScript snippet. |
| `Wait` | Pause for a duration or until a time. |

## Managed-API actions

| `type` | Purpose |
|---|---|
| `ApiConnection` | Call a managed connector operation (Office 365, SharePoint, Dataverse, …). |
| `ApiConnectionWebhook` | Managed connector with webhook callback. |

## `runAfter` — sequencing & error handling

`runAfter` maps each prerequisite action name to an array of accepted statuses.
Accepted statuses: `Succeeded`, `Failed`, `Skipped`, `TimedOut`.

```json
"Parse_JSON": {
  "type": "ParseJson",
  "inputs": { },
  "runAfter": { "HTTP_Action": [ "Succeeded" ] }
}
```

- `"runAfter": {}` — the action runs first, immediately after the trigger.
- Multiple keys — all listed actions must reach an accepted status.
- Run-after on `[ "Failed", "TimedOut" ]` is how you build catch/error branches
  (often combined with a `Scope`).
