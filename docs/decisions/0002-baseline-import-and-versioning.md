# ADR-0002: Baseline import and versioning

- Status: Accepted (defaults chosen by Claude; John may change)
- Date: 2026-10-11

## Context
The code arrived as a tar archive with no git history. The archive notes mention a
`newcmds` branch and older command code that are not in the archive.

## Decision
- Import the archive unchanged as version 0.1.0 so every later change is a reviewable diff.
- Use Semantic Versioning, one version for the whole package (firmware + client),
  stored in `VERSION`. Pre-1.0 while the protocol is still changing.
- Keep the repository in the project's shared folder at `/mnt/project-files/wifi-terminal/`.
- Exclude private keys, editor swap files and logs.

## Consequences
If John's original repository (with `newcmds`) turns up, it should be imported as
history underneath this baseline rather than replacing it.
