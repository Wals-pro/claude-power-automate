# Power Fx for Desktop Flows

Official references:

- Power Fx formula reference overview:
  https://learn.microsoft.com/en-us/power-platform/power-fx/formula-reference-cards
- Power Fx in desktop flows:
  https://learn.microsoft.com/en-us/power-automate/desktop-flows/power-fx

## Scope

Use Power Fx references only when the target is a Power Fx-enabled host, such
as Power Automate desktop-flow formula mode. Do not use Power Fx syntax for
cloud-flow JSON actions, conditions, or `clientdata` expressions.

## Practical Differences From Cloud-Flow Expressions

- Power Fx has Excel-like formulas and typed values.
- Cloud flows use WDL functions such as `body()`, `outputs()`, `variables()`,
  and `triggerBody()`.
- A function being available in Power Fx does not imply it is valid in a
  cloud-flow expression.

## Desktop-Flow Checklist

- Confirm the desktop-flow action supports Power Fx mode.
- Check each formula reference article's "Applies to" section.
- Watch for functions that exist in Power Fx generally but are not available in
  desktop flows.
- Validate in the desktop-flow designer when the reference says support is
  partial or host-specific.
