# Workflow Definition Language — schema shape

Canonical source:
https://learn.microsoft.com/en-us/azure/logic-apps/workflow-definition-language-schema

## Top-level definition

```json
"definition": {
  "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
  "contentVersion": "1.0.0.0",
  "parameters": { },
  "triggers": { },
  "actions": { },
  "outputs": { },
  "staticResults": { }
}
```

| Key | Required | Notes / limit |
|---|---|---|
| `$schema` | When externally referenced | WDL schema version URL. |
| `contentVersion` | No | Defaults to `"1.0.0.0"`; set it to identify the definition. |
| `parameters` | No | Runtime parameter definitions. Max 50. |
| `triggers` | No | One or more triggers (multiple only via WDL, not the designer). Max 10. |
| `actions` | No | The actions to run after the trigger. Max 250. |
| `outputs` | No | Values returned from a run. Max 10. (To reply to a request, use the `Response` action, not `outputs`.) |
| `staticResults` | No | Mock outputs for testing, referenced by `runtimeConfiguration.staticResult.name`. |

## Trigger / action object shape

```json
"<name>": {
  "type": "<type>",
  "inputs": { },
  "runAfter": { "<previous-action>": [ "Succeeded" ] },
  "runtimeConfiguration": { }
}
```

Recurrence triggers add a `recurrence` object. See `triggers-and-actions.md` for
`type` values and `runAfter` semantics.

## Parameters & secrets

```json
"parameters": {
  "<name>": {
    "type": "<int|float|string|bool|array|object|securestring|secureobject>",
    "defaultValue": <value>,
    "allowedValues": [ ],
    "metadata": { "description": "" }
  }
}
```

Use **`securestring` / `secureobject`** for passwords, keys, and secrets — a `GET`
does **not** return these types. Store secret values in Azure Key Vault and
reference them; never hardcode a secret literal into the definition.

## Operators

| Operator | Use |
|---|---|
| `'` | Wrap string literals: `length('Hello')` (single quotes, never double). |
| `[]` | Index/property access: `myArray[1]`, `obj['prop']`. |
| `.` | Property access: `parameters('customer').name`. |
| `?` | Null-safe access: `triggerBody()?['ContentData']` returns `null` instead of failing when the property/parent is missing. |

## Expressions vs string interpolation

- Whole value is an expression: `"@parameters('name')"`.
- Inside a string: `"Hello @{parameters('name')}"`.
- Escape a literal leading `@` by doubling it: `@@`.
- An interpolated expression always resolves to a string; a whole-value
  expression keeps the underlying type (number stays a number).
