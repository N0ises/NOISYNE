
# Contributing to PHASENOX

Thank you for contributing to PHASENOX.

PHASENOX is an Audio Intelligence System built with an architecture-first philosophy.
Every contribution should improve the long-term quality of the platform.

---

# Before You Start

Read these documents first:

- README.md
- VISION.md
- PHILOSOPHY.md
- ARCHITECTURE.md
- AUDIO_ARCHITECTURE.md
- ROADMAP.md
- DECISIONS.md
- ENGINEERING.md

Architecture has higher priority than implementation.

---

# Contribution Principles

Every contribution should improve one or more of:

- Readability
- Maintainability
- Testability
- Performance
- Documentation
- Extensibility

Never reduce architectural quality to implement a feature faster.

---

# Engineering Rules

- Respect Clean Architecture.
- Keep business logic independent from providers.
- Use dependency injection.
- Avoid circular imports.
- Avoid duplicate business logic.
- Keep modules focused on one responsibility.
- Prefer explicit interfaces.

---

# AI Rules

New AI features should strengthen one or more stages:

- Perception
- Understanding
- Reasoning
- Decision
- Action
- Creation

AI outputs should be explainable whenever practical.

---

# Documentation

Architecture changes require documentation updates.

Behavior changes require tests.

Public APIs should remain documented.

---

# Pull Request Checklist

Before opening a PR:

- Tests pass.
- Documentation updated.
- Architecture respected.
- No hidden dependencies.
- No hardcoded configuration.
- No duplicated business logic.

---

# Commit Messages

Recommended prefixes:

- feat:
- fix:
- refactor:
- docs:
- test:
- perf:
- chore:

---

# Discussions

Discuss major architectural changes before implementation.

Large redesigns should not be merged without review.

---

# Final Principle

Every commit should leave PHASENOX in a better state than before.
