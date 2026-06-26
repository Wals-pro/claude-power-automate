---
name: power-automate-workflow-patterns
description: >
  Design or modify Microsoft Power Automate cloud-flow architectures using
  proven workflow patterns. Use when building flows, choosing triggers/actions,
  structuring branches/scopes, adding SharePoint/Outlook/Dataverse automation,
  handling retries and errors, or translating n8n-style workflow routines into
  Power Automate without reinventing the process.
---

# Power Automate Workflow Patterns

Use this before designing or restructuring a Power Automate cloud flow. It
adapts n8n-style workflow discipline to Power Automate concepts.

## Pattern Workflow

1. Pick the pattern from `references/cloud-flow-patterns.md`.
2. Identify trigger, data source, transformation, action, and observability
   points.
3. Keep solution-aware flows versioned through local artifacts.
4. Use `power-automate-action-configuration` for connector payloads.
5. Use `power-automate-expression-syntax` for conditions and dynamic content.
6. Use `power-automate-api-client` for pull/diff/deploy/verify.

## Design Rules

- Prefer small, explicit branches over dense nested expressions.
- Use scopes to group transactional steps and error handling.
- Make connector boundaries visible: SharePoint lookup, Outlook send/draft,
  Dataverse write, HTTP call, etc.
- Add observable evidence for critical paths, such as log rows or status
  updates, when the business process needs auditability.
- Keep customer-facing send paths testable without sending directly from Claude.
