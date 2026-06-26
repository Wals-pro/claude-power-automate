---
name: power-automate-reference
description: >
  Authoritative, embedded reference for the Power Automate cloud-flow language
  (Workflow Definition Language / Logic Apps). Use to confirm whether a function,
  trigger, or action exists and its exact name or JSON "type", to check function
  signatures, the workflow-definition schema, runAfter semantics, or operators —
  before writing or validating any cloud-flow expression or JSON. Stops invented
  functions and Power Fx bleeding into cloud flows.
---

# Power Automate Reference

Look here **before** writing or reviewing a cloud-flow expression or action JSON.
This skill ships the canonical Microsoft references inline so you verify names
against the real namespace instead of recalling them from training data (which
goes stale as Microsoft changes the platform).

## Hard rules

- **The function namespace is closed.** If a name is not in
  `references/expression-functions.md`, it does not exist — do not invent or
  guess a function. Pick a real one or compose existing ones.
- **Cloud flows use Workflow Definition Language (WDL) only.** Never use Power Fx
  functions inside cloud-flow JSON. Power Fx is for desktop flows and other Power
  Platform formula surfaces (see `power-automate-expression-syntax`).
- **Secrets** in a workflow definition's `parameters` use the `securestring` /
  `secureobject` types (a `GET` will not return them); real secrets belong in
  Azure Key Vault, never as literals in the definition.
- Use the `?` null-safe operator for optional action/trigger outputs.
- Prefer real control actions (`If` / `Switch` / `Scope` / `Foreach` / `Until`)
  over stacking `Compose` actions to fake logic.

## Procedure

1. Classify what you need:
   - a **function** (name / category / does it exist) → `references/expression-functions.md`
   - a **trigger or action** (`type` value, runAfter) → `references/triggers-and-actions.md`
   - the **definition shape**, parameter types, or operators →
     `references/workflow-definition-language-schema.md`
2. Read the matching reference file and use the exact names/types it lists.
3. Only open the canonical Microsoft Learn link (in each file) when you need the
   newest behavior or an edge detail the reference does not cover.

## Related skills

- `power-automate-expression-syntax` — how to *compose and validate* expressions
  (this skill is the *lookup* of what exists).
- `power-automate-action-configuration` — connector/action payload shapes.
- `power-automate-docs` — router to the wider Microsoft Learn documentation.
- `power-automate-workflow-patterns` — flow architecture (and avoiding Compose
  sprawl).
