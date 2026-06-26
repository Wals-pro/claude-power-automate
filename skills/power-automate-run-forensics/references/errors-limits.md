# Power Automate Errors, Runs, and Limits

Official references:

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
- Flow runs API:
  https://learn.microsoft.com/en-us/rest/api/power-platform/powerautomate/flow-runs/list-flow-runs

## Investigation Order

1. Is the flow on, off, or suspended?
2. Did the trigger fire?
3. Is there a run in the expected time window?
4. Which action first failed or skipped unexpectedly?
5. Is the error design-time (`InvalidTemplate`) or runtime
   (`ExpressionEvaluationFailed`, connector error, throttling, timeout)?
6. Did a connection fail or require re-authentication?
7. Did limits, concurrency, retry settings, or run retention affect evidence?

## Common Findings

- No run: trigger did not fire, flow is off/suspended, wrong environment, or
  run history aged out.
- Run-history 401 `ClientScopeAuthorizationFailed`: the signed-in account can
  see environment/flow metadata but cannot read run history for that flow.
- Skipped branch: `runAfter`, condition result, or trigger condition did not
  match.
- Invalid template: expression/action JSON is malformed or references a
  missing action.
- Runtime expression failure: live data shape differs from expected shape.
- Connection failure: connector auth expired, permissions changed, DLP policy,
  or deleted connection.
- Attachment/file issue: content was encoded or shaped incorrectly for the
  target connector.

## Operational Notes

- Default run history is limited; capture run evidence promptly.
- Turning off a cloud flow stops new runs; in-progress and pending runs may
  continue.
- Deleting a flow cancels in-progress/pending runs and is not a diagnostic
  action.
- Concurrency control and retry policies can change observed timing and order.
