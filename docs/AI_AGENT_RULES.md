# PHASENOX AI Agent Rules

These rules apply to every implementation sprint.

## General

- Inspect the repository before making changes.
- Use the repository as the source of truth.
- Preserve existing architecture.
- Prefer extension over refactoring.
- Never redesign Runtime or Loader.
- Keep backward compatibility.
- Keep deterministic behavior.

## Sprint Workflow

Odd-numbered sprints (5, 7, 9...)

1. Architecture Specification
2. Architecture Review
3. Implementation
4. Validation

Even-numbered sprints (6, 8, 10...)

1. Implementation
2. Validation

Do not perform an Architecture Specification unless explicitly requested.

## Implementation Rules

- No duplicated models.
- No circular imports.
- No hidden dependencies.
- No breaking API changes.
- Fail gracefully.
- Keep modules independently testable.

## Scope Control

Implement only the requested sprint.

Do not refactor unrelated modules.

Do not fix unrelated issues unless they block the current sprint.

If a blocker is found:

- Stop.
- Explain the blocker.
- Propose the smallest possible fix.
- Continue only after the blocker is resolved.
