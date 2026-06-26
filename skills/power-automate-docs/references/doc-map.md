# Power Automate Documentation Map

Use these official Microsoft sources as the default research map.

## Core Entry Points

- Power Automate documentation: https://learn.microsoft.com/en-us/power-automate/
- Cloud-flow overview: https://learn.microsoft.com/en-us/power-automate/overview-cloud
- Triggers overview: https://learn.microsoft.com/en-us/power-automate/triggers-introduction
- Work with triggers and actions: https://learn.microsoft.com/en-us/power-automate/work-with-triggers

## Expressions

- Cloud-flow expression cookbook: https://learn.microsoft.com/en-us/power-automate/expression-cookbook
- Use expressions in conditions: https://learn.microsoft.com/en-us/power-automate/use-expressions-in-conditions
- Workflow expression functions for Power Automate and Logic Apps:
  https://learn.microsoft.com/en-us/azure/logic-apps/workflow-definition-language-functions-reference
- Power Fx formula reference overview:
  https://learn.microsoft.com/en-us/power-platform/power-fx/formula-reference-cards
- Power Fx in desktop flows:
  https://learn.microsoft.com/en-us/power-automate/desktop-flows/power-fx

Important distinction: cloud flows use Workflow Definition Language
expressions. Power Fx applies to Power Platform hosts and Power Automate
desktop flows; do not use Power Fx syntax in cloud-flow JSON unless the target
surface explicitly supports it.

## APIs and Deployment

- Work with cloud flows using code:
  https://learn.microsoft.com/en-us/power-automate/manage-flows-with-code
- Dataverse Web API overview:
  https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview
- Power Platform API reference:
  https://learn.microsoft.com/en-us/rest/api/power-platform/
- Environment metadata:
  https://learn.microsoft.com/en-us/rest/api/power-platform/environmentmanagement/environments/get-environment-by-id-for-user
- Cloud-flow runs:
  https://learn.microsoft.com/en-us/rest/api/power-platform/powerautomate/flow-runs/list-flow-runs

Default: use the `power-automate` CLI for local pull/diff/deploy instead of
a hosted MCP service.

## Connectors and Actions

- Connector reference index: https://learn.microsoft.com/en-us/connectors/
- Office 365 Outlook connector:
  https://learn.microsoft.com/en-us/connectors/office365connector/
- SharePoint connector:
  https://learn.microsoft.com/en-us/connectors/sharepointonline/
- Dataverse connector:
  https://learn.microsoft.com/en-us/power-automate/dataverse/overview
- Power Automate Management connector:
  https://learn.microsoft.com/en-us/connectors/flowmanagement/

Connector pages define operation names, inputs, outputs, known limits, and
authentication notes. Prefer them over screenshots or UI memory.

## Debugging, Limits, and Operations

- Troubleshoot cloud-flow errors:
  https://learn.microsoft.com/en-us/power-automate/troubleshoot-flow-errors
- Cloud-flow error code reference:
  https://learn.microsoft.com/en-us/power-automate/error-reference
- Fix connection failures:
  https://learn.microsoft.com/en-us/power-automate/fix-connection-failures
- Limits and configuration:
  https://learn.microsoft.com/en-us/power-automate/limits-and-config
- Failure notifications:
  https://learn.microsoft.com/en-us/power-automate/understand-flow-failure-notifications
- Missing run history:
  https://learn.microsoft.com/en-us/troubleshoot/power-platform/power-automate/flow-run-issues/missing-runs-or-triggers-history-for-a-flow
