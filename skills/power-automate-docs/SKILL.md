---
name: power-automate-docs
description: >
  Navigate official Microsoft Power Automate and Power Platform documentation.
  Use when researching Power Automate capabilities, deciding whether a topic
  belongs to cloud-flow expressions, Power Fx desktop flows, Dataverse workflow
  APIs, connector references, limits, errors, or monitoring. Prefer this skill
  before using generic web search for Power Automate tasks.
---

# Power Automate Docs

Use this as the documentation router for Power Automate work. Prefer official
Microsoft Learn sources and local runbooks over third-party examples.

## Procedure

1. Classify the task:
   - Cloud-flow JSON/API work: use Workflow Definition Language and Dataverse
     workflow docs.
   - Desktop-flow formulas: use Power Fx desktop-flow docs.
   - Connector/action configuration: use connector reference docs.
   - Failed run/debugging: use error, limits, and run-history docs.
2. Read `references/doc-map.md` for the right source links and caveats.
3. If changing local artifacts, pair this with:
   - `power-automate-api-client` for pull/diff/deploy/status/runs,
   - `power-automate-expression-syntax` for expressions,
   - `power-automate-action-configuration` for action payloads,
   - `power-automate-run-forensics` for execution analysis,
   - `power-automate-reference` for the exact function/trigger/action namespace
     and the workflow-definition schema.

## Rules

- Do not treat Power Fx as the default expression language for cloud flows.
- Do not use closed hosted MCP services as the source of truth.
- When information may have changed, verify against Microsoft Learn before
  editing code or workflows.
