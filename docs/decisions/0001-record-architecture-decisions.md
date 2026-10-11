# ADR-0001: Record architecture decisions

- Status: Accepted
- Date: 2026-10-11

## Context
John asked for a decisions record alongside the code, changelog and notes.

## Decision
Keep one Markdown file per decision in `docs/decisions/`, numbered `NNNN-title.md`,
with Status (Proposed / Accepted / Rejected / Superseded by ADR-NNNN), Date,
Context, Decision, Consequences. A Proposed ADR is not acted on until John accepts it.

## Consequences
Decisions are reviewable in git history. Superseded ADRs stay in place and point forward.
