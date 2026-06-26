# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once it reaches 1.0.

> **Beta (0.x).** This is pre-1.0 software. The CLI surface, command output, skill
> contents, and config schema **may change without notice** between 0.x releases.

## [0.1.0] - 2026-06-26

Initial public release of the **claude-power-automate** suite.

### Added
- **`power-automate` CLI** — a local, open client for Microsoft Power Automate
  cloud flows, backed by the Dataverse Web API and the Power Platform API,
  authenticated through an existing `az login` session. Commands: `status`,
  `pull`, `backup`, `diff`, `verify`, `deploy`, `create`, `flows`,
  `environments`, `runs`, `run-detail`, `start`, `stop`, and the `process-*`
  variants for non-solution cloud flows.
- **Profile/target resolution** with no secret storage: CLI flags →
  `POWER_AUTOMATE_*` environment variables → `profiles.json`. A
  `register_profile_resolver()` hook lets host applications inject their own
  (e.g. secrets-manager-backed) lookup.
- **Six Claude Code Agent Skills** for Power Automate development:
  `power-automate-api-client`, `power-automate-docs`,
  `power-automate-expression-syntax`, `power-automate-action-configuration`,
  `power-automate-workflow-patterns`, and `power-automate-run-forensics`.
- Azure CLI setup guide, operations runbook, and unit test suite.

[0.1.0]: https://github.com/Wals-pro/claude-power-automate/releases/tag/v0.1.0
