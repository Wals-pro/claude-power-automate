---
name: power-automate-expression-syntax
description: >
  Write, validate, and debug Microsoft Power Automate expressions. Use for
  Workflow Definition Language expressions in cloud flows, dynamic content,
  runAfter conditions, null-safe property access, variables, trigger/action
  outputs, date/string/array functions, and for deciding when Power Fx applies
  only to desktop-flow or other Power Platform formula surfaces.
---

# Power Automate Expression Syntax

Power Automate cloud flows use Workflow Definition Language expressions.
Power Fx is a separate formula language and is not the default for cloud-flow
JSON.

## Workflow

1. Identify the expression host:
   - Cloud-flow action/condition/JSON: WDL expressions.
   - Desktop flow formula mode: Power Fx.
2. For cloud-flow expressions, read `references/cloud-flow-expressions.md`.
3. For desktop-flow Power Fx, read `references/power-fx-desktop-flows.md`.
4. Validate against live run inputs where possible; expression errors are often
   data-shape errors rather than syntax-only errors.

## Cloud-Flow Guardrails

- Use `@{...}` inside string interpolation and `@...` when the whole value is
  an expression.
- Prefer null-safe access with `?[]` for optional action outputs.
- Use exact action names in `outputs('Action_Name')`, `body('Action_Name')`,
  and `actions('Action_Name')`.
- Avoid copying expressions from rendered docs without checking quotes and
  invisible characters.
