# Cloud-Flow Patterns

Official references:

- Cloud-flow overview: https://learn.microsoft.com/en-us/power-automate/overview-cloud
- Triggers overview: https://learn.microsoft.com/en-us/power-automate/triggers-introduction
- Work with triggers and actions:
  https://learn.microsoft.com/en-us/power-automate/work-with-triggers
- Limits and configuration:
  https://learn.microsoft.com/en-us/power-automate/limits-and-config

## Core Patterns

### Event Notification

Trigger from Dataverse, SharePoint, Outlook, HTTP, or custom connector; enrich
data; send notification; log outcome.

Use for release notifications, approval notifications, status changes, and
customer/internal alerts.

### File Enrichment

Trigger on business event; resolve expected file path/name; list or fetch file;
validate file content; attach or link file; log missing-file case.

Use for certificates, invoices, delivery notes, labels, and exports.

### Approval or Gate

Trigger; collect context; request approval; branch on approval result; write
business status; notify stakeholders.

Keep timeout, reassignment, and rejection paths explicit.

### Scheduled Reconciliation

Recurrence trigger; list source records; compare against target state; process
changes; write audit summary; notify only on exceptions or summary cadence.

Use pagination and connector limits deliberately.

### Webhook or HTTP Intake

HTTP trigger; validate schema/signature; normalize payload; branch by event
type; respond quickly; continue heavy work asynchronously when required.

### Error Handling Scope

Group risky connector actions in a scope. Add success/failure scopes with
`runAfter` configured for `Succeeded`, `Failed`, `TimedOut`, or `Skipped` as
appropriate.

## Cross-Cutting Choices

- Trigger type: automated, instant/manual, scheduled, HTTP/request.
- State: variables for transient flow state; Dataverse/SharePoint/log table for
  durable state.
- Branching: Condition/Switch for business decisions; Scopes for operational
  grouping.
- Error handling: retry policy for transient connector issues; explicit
  failure branch for business exceptions.
- Observability: run history is useful but time-limited; critical processes
  need durable logs.

## Review Checklist

- Does the trigger match the business event and expected latency?
- Are connector limits, pagination, and concurrency considered?
- Are missing records/files handled as a business case, not an unhandled error?
- Is there a deterministic test path?
- Are customer-facing sends gated by review/draft policy when Claude is involved?
- Can a failed run be diagnosed from action names, logs, and outputs?
