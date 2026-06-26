# Cloud-Flow Expressions

Official references:

- Expression cookbook: https://learn.microsoft.com/en-us/power-automate/expression-cookbook
- Use expressions in conditions: https://learn.microsoft.com/en-us/power-automate/use-expressions-in-conditions
- Full Workflow Definition Language function reference:
  https://learn.microsoft.com/en-us/azure/logic-apps/workflow-definition-language-functions-reference

## Syntax Forms

- Whole value expression: `@variables('name')`
- String interpolation: `Hello @{triggerBody()?['name']}`
- Action body: `@body('Get_item')`
- Trigger body: `@triggerBody()`
- Action output: `@outputs('Get_item')`
- Variable: `@variables('CertificateAttachments')`
- Parameter: `@parameters('Parameter Name')`

## Common Function Groups

- Text: `concat`, `replace`, `split`, `substring`, `toLower`, `toUpper`, `trim`
- Dates: `utcNow`, `formatDateTime`, `addDays`, `ticks`, `convertTimeZone`
- Arrays: `first`, `last`, `length`, `join`, `union`, `intersection`
- Objects/JSON: `json`, `coalesce`, `addProperty`, `setProperty`,
  `removeProperty`
- Logic: `if`, `and`, `or`, `not`, `equals`, `greater`, `less`
- Workflow: `body`, `outputs`, `triggerBody`, `triggerOutputs`, `workflow`

## Safe Data Access

Use null-safe operators when source actions can fail, return empty results, or
skip a branch:

```text
@body('Get_item')?['Title']
@outputs('Get_file_content')?['body']
@first(body('List_rows')?['value'])?['name']
```

Use `coalesce()` for fallback values:

```text
@coalesce(body('Get_item')?['Title'], 'Unbenannt')
```

## Common Failure Modes

- `InvalidTemplate`: syntax error, missing action name, wrong argument count, or
  constant expression that fails during save.
- `ExpressionEvaluationFailed`: runtime data did not match the expression, such
  as null property access, invalid date format, or numeric conversion failure.
- Wrong action name: cloud-flow JSON uses internal action keys, not always the
  display text seen in the designer.
- Attachments and binary content: verify whether the connector expects raw
  bytes, base64 text, or an object with `$content`.

## Review Checklist

- Does the expression host expect a full expression or string interpolation?
- Are action names exact and stable in JSON?
- Are optional values null-safe?
- Are arrays handled for empty results?
- Are date/time values formatted explicitly?
- Is binary content attached in the connector's expected shape?
