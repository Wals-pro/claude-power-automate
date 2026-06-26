---
name: power-automate-run-forensics
description: >
  Diagnose Microsoft Power Automate cloud-flow incidents from run history,
  failed actions, trigger behavior, connection failures, missing runs, skipped
  branches, invalid expressions, throttling, retries, and action outputs before
  changing workflow code. Use with the power-automate CLI runs and
  run-detail commands for read-only evidence gathering.
---

# Power Automate Run Forensics

Start read-only. Confirm what the flow actually did before changing JSON,
connections, or production records.

## Procedure

1. Define boundary: profile, environment ID, flow ID/name, run ID(s), object IDs,
   and absolute time window.
2. Run `power-automate status --profile <profile>` and
   `power-automate runs --profile <profile>` when API access is available.
3. If the flow or environment is unknown, run `power-automate environments`,
   `power-automate flows`, or `power-automate runs --all-environments --top <n>`
   to discover what the signed-in Azure user can see.
4. For a failed or suspicious run, inspect `power-automate run-detail`.
5. Compare trigger data, action inputs, action outputs, branch status, skipped
   actions, and connector error codes.
6. Read `references/errors-limits.md` for Microsoft error/limit guidance.
7. Produce findings before proposing edits.

## Output

Report:

- Boundary checked.
- Evidence reviewed.
- Findings with run IDs and timestamps.
- Impact.
- Root cause or strongest hypothesis.
- Fix target and validation plan.

If evidence is missing, name the missing source and why it matters.
