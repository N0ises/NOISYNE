# PHASENOX Dependency Graph

Version: 1.0

Status: ACTIVE

---

# Purpose

This document defines the allowed dependency directions inside PHASENOX.

It prevents architectural drift, circular dependencies, and hidden coupling.

---

# Dependency Rule

Dependencies always point downward.

Higher layers may depend on lower layers.

Lower layers must never depend on higher layers.

---

# Layer Graph

Application

↓

Services

↓

Reasoning

↓

Knowledge

↓

Engineering

↓

Audio

↓

Runtime

↓

Infrastructure

---

# Runtime

May depend on:

- Configuration
- Model Repository
- Providers
- Logging
- Cache

Must never depend on:

- Audio
- Engineering
- RAG
- Reasoning
- Reports

---

# Audio

May depend on:

- Runtime
- Providers
- Domain Models

Must never depend on:

- RAG
- LLM
- Reports
- UI

---

# Engineering

May depend on:

- Audio
- Runtime

Must never depend on:

- UI
- API

---

# Knowledge

May depend on:

- Runtime
- Embeddings

Must never depend on:

- Reports
- UI

---

# Reasoning

May depend on:

- Knowledge
- Engineering
- Runtime

Must never depend on:

- CLI
- API
- Desktop

---

# Reports

May depend on:

- Reasoning
- Engineering
- Knowledge

Must never be imported by:

- Runtime
- Audio

---

# Product Layer

CLI

API

Desktop

These consume services only.

They never access internal modules directly.

---

# Forbidden

- Circular imports
- Hidden dependencies
- Global mutable state
- Cross-layer shortcuts

---

# Final Rule

When in doubt, follow the dependency graph.

If a dependency violates this document, redesign the architecture instead of bypassing it.
