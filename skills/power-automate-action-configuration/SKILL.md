---
name: power-automate-action-configuration
description: >
  Configure Microsoft Power Automate cloud-flow triggers and actions from JSON,
  connector references, or designer semantics. Use for operation inputs,
  connector schemas, Office 365 Outlook email actions, SharePoint actions,
  Dataverse actions, connectionReferences, runAfter, retry policies, secure
  inputs/outputs, and action payload shape decisions.
---

# Power Automate Action Configuration

Use this when editing `definition.actions`, `definition.triggers`, or
`connectionReferences` in a Power Automate cloud-flow artifact.

## Procedure

1. Identify the connector/action key in the JSON and the display action in the
   designer.
2. Read the official connector reference for that connector if payload shape is
   uncertain.
3. Preserve existing `connectionReferences`; only change them when explicitly
   remapping credentials/connections.
4. Keep `runAfter` explicit when moving actions between branches.
5. Validate binary, attachment, and file-content fields against the connector
   docs and at least one live run when possible.

## References

- Read `references/actions-connectors.md` for connector/action patterns.
- Use `power-automate-expression-syntax` for dynamic content.
- Use `power-automate-api-client` for pull/diff/deploy.
