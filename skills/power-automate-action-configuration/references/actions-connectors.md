# Power Automate Actions and Connectors

Official references:

- Connector reference index: https://learn.microsoft.com/en-us/connectors/
- Work with triggers and actions:
  https://learn.microsoft.com/en-us/power-automate/work-with-triggers
- Office 365 Outlook connector:
  https://learn.microsoft.com/en-us/connectors/office365connector/
- SharePoint connector:
  https://learn.microsoft.com/en-us/connectors/sharepointonline/
- Dataverse connector overview:
  https://learn.microsoft.com/en-us/power-automate/dataverse/overview
- Power Automate Management connector:
  https://learn.microsoft.com/en-us/connectors/flowmanagement/

## JSON Concepts

- `definition.triggers`: starts the flow.
- `definition.actions`: action graph keyed by internal action names.
- `runAfter`: dependency map from previous action key to allowed statuses.
- `inputs.host.apiId`: connector API id.
- `inputs.host.connectionName`: connection reference key or connection name.
- `inputs.host.operationId`: connector operation.
- `inputs.parameters`: operation-specific payload.
- `connectionReferences`: maps connector keys to actual environment
  connections.

## Configuration Rules

- Do not rename action keys casually; expressions and `runAfter` often depend
  on exact names.
- Do not remove `authentication` from connector actions unless the existing
  artifact already omits it for that action type.
- When moving actions into a branch, also move or rewrite downstream
  `runAfter` dependencies.
- Preserve retry, timeout, metadata, and secure data settings unless the change
  explicitly concerns them.
- Treat designer display names as hints. The JSON action key is authoritative.

## Connector-Specific Notes

### Office 365 Outlook

- `Send an email (V2)` commonly uses parameters under `emailMessage/...`.
- Attachments are connector-shaped objects; verify whether content should be
  raw bytes, base64, or an object field from a file-content action.
- Prefer creating drafts outside production send paths when testing customer
  messaging with Claude.

### SharePoint

- File lookup usually needs site address, library/folder path, and file
  identifier/path consistency.
- File content actions may return binary content wrapped by the connector.
- Folder listing filters should account for encoded spaces and exact filenames.

### Dataverse

- Dataverse connector triggers/actions are distinct from the Dataverse Web API
  used by the `power-automate` CLI.
- Confirm table logical names, row IDs, and lookup binding conventions before
  changing payloads.

## Review Checklist

- Is every connector used by an action present in `connectionReferences`?
- Do changed actions still point to the intended connection?
- Are branch dependencies valid after `runAfter` edits?
- Does every expression reference an existing action key?
- Are binary/file/attachment fields in the expected connector shape?
- Does the flow still save and produce a readable first run?
