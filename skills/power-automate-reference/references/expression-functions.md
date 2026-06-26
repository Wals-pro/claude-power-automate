# Workflow Definition Language — complete function namespace

Canonical source (open for signatures, arguments, and examples):
https://learn.microsoft.com/en-us/azure/logic-apps/expression-functions-reference

> **This is the full namespace.** If a function name is not in this list, it does
> not exist in cloud flows — do not invent one. These are Workflow Definition
> Language functions, **not** Power Fx. Wrap string literals in single quotes
> (`'text'`), not double quotes.

## String

`chunk`, `concat`, `endsWith`, `formatNumber`, `guid`, `indexOf`, `isFloat`,
`isInt`, `lastIndexOf`, `length`, `nthIndexOf`, `replace`, `slice`, `split`,
`startsWith`, `substring`, `toLower`, `toUpper`, `trim`

## Collection

`chunk`, `contains`, `empty`, `first`, `intersection`, `item`, `join`, `last`,
`length`, `reverse`, `skip`, `sort`, `take`, `union`

## Logical comparison

`and`, `equals`, `greater`, `greaterOrEquals`, `if`, `isFloat`, `isInt`, `less`,
`lessOrEquals`, `not`, `or`

## Conversion

`array`, `base64`, `base64ToBinary`, `base64ToString`, `binary`, `bool`,
`createArray`, `dataUri`, `dataUriToBinary`, `dataUriToString`, `decimal`,
`decodeBase64` (deprecated — use `base64ToString`), `decodeDataUri`,
`decodeUriComponent`, `encodeUriComponent`, `float`, `int`, `json`, `string`,
`uriComponent`, `uriComponentToBinary`, `uriComponentToString`, `xml`

## Math

`add`, `div`, `max`, `min`, `mod`, `mul`, `rand`, `range`, `sub`

## Date and time

`addDays`, `addHours`, `addMinutes`, `addSeconds`, `addToTime`, `convertFromUtc`,
`convertTimeZone`, `convertToUtc`, `dateDifference`, `dayOfMonth`, `dayOfWeek`,
`dayOfYear`, `formatDateTime`, `getFutureTime`, `getPastTime`, `parseDateTime`,
`startOfDay`, `startOfHour`, `startOfMonth`, `subtractFromTime`, `ticks`,
`utcNow`

## Workflow / referencing (runtime values)

`action`, `actions`, `body`, `formDataMultiValues`, `formDataValue`, `item`,
`items`, `iterationIndexes`, `listCallbackUrl`, `multipartBody`, `outputs`,
`parameters`, `result`, `trigger`, `triggerBody`, `triggerFormDataValue`,
`triggerFormDataMultiValues`, `triggerMultipartBody`, `triggerOutputs`,
`variables`, `workflow`

## URI parsing

`uriHost`, `uriPath`, `uriPathAndQuery`, `uriPort`, `uriQuery`, `uriScheme`

## Manipulation (JSON & XML)

`addProperty`, `coalesce`, `removeProperty`, `setProperty`, `xpath`

## Quick null-safe patterns

```text
@body('Get_item')?['Title']
@coalesce(trigger().outputs?.body?['name'], 'fallback')
@first(body('List_rows')?['value'])?['id']
```
