
# PHASENOX Design Patterns

Version: 2.0

Status: ACTIVE

---

# Purpose

This document defines the approved architectural patterns used throughout
PHASENOX. New code should reuse these patterns instead of inventing new ones.

---

# Provider Pattern

Purpose

Abstract external technologies.

Examples

- LLM Providers
- Embedding Providers
- Audio Providers
- Vision Providers
- Storage Providers

---

# Dependency Injection

Purpose

Dependencies are injected, never constructed internally.

Benefits

- Testability
- Replaceability
- Loose coupling

---

# Builder Pattern

Purpose

Build complex prompts, reports and execution contexts.

Examples

- PromptBuilder
- ReferencePromptBuilder
- ReportBuilder

---

# Strategy Pattern

Purpose

Allow interchangeable algorithms.

Examples

- Comparison Strategy
- Routing Strategy
- Planning Strategy

---

# Adapter Pattern

Purpose

Wrap third-party APIs behind stable interfaces.

---

# Factory Pattern

Purpose

Instantiate providers and services through contracts.

---

# Repository Pattern

Purpose

Access structured knowledge without exposing storage details.

Examples

- Knowledge Graph
- Vector Store
- Reference Library

---

# Pipeline Pattern

Purpose

Execute ordered processing stages.

Pipeline

Input
↓
Perception
↓
Understanding
↓
Reasoning
↓
Decision
↓
Action
↓
Creation

---

# State Pattern

Purpose

Share immutable execution state between stages.

---

# Agent Pattern

Purpose

Split complex intelligence into specialized agents.

Current Direction

- Mix Agent
- Master Agent
- Reference Agent
- Psychoacoustic Agent
- Producer Agent
- Composer Agent
- Teacher Agent

---

# Blackboard Pattern

Purpose

Allow multiple agents to collaborate using shared context.

Status

Planned.

---

# Knowledge Graph Pattern

Purpose

Separate engineering knowledge from reasoning logic.

Knowledge Sources

- AES
- ITU
- EBU
- Dolby
- Engineering Literature
- Academic Research

---

# Workflow Pattern

Purpose

Coordinate multi-step AI tasks.

Examples

- Reference Analysis
- Mix Review
- Mastering Review
- Audio Generation

---

# Patterns We Avoid

- God Objects
- Hidden Dependencies
- Circular Imports
- Service Locator
- Utility Dumping Grounds
- Global Mutable State

---

# Final Rule

Introduce a new pattern only when an existing pattern cannot solve the problem
without violating the architecture.
