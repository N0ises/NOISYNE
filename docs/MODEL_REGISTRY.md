# PHASENOX Model Registry

Version: 1.0

Status: ACTIVE

---

# Purpose

This document defines every AI model used by PHASENOX.

Models are treated as replaceable infrastructure components.

Business logic must never depend on a specific model implementation.

---

# Registry Rules

Every model must define:

- Name
- Purpose
- Provider
- Runtime Loader
- Input
- Output
- Status

---

# Embedding Models

## CLAP

Purpose

Audio embeddings

Provider

Transformers

Status

Production

---

## Future

- MERT
- AudioMAE
- Audio Foundation Model

Status

Planned

---

# Language Models

## Qwen

Purpose

Reasoning

Provider

Transformers

Status

Production

---

## Future

- OpenAI
- Claude
- Gemini
- Ollama
- LM Studio
- Local GGUF Models

---

# Reranking Models

## BGE Reranker

Purpose

Document reranking

Status

Production

---

# Vision Models

Future

- Florence
- Qwen-VL
- InternVL

Status

Planned

---

# Speech Models

Future

- Whisper
- WhisperX

Status

Planned

---

# Runtime Rules

Every model must:

- Load through ModelRuntime
- Support lazy loading
- Support cache
- Be replaceable
- Be configurable
- Never expose provider-specific APIs

---

# Current Production Models

| Domain | Model |
|---------|-------|
| Embedding | CLAP |
| Reasoning | Qwen |
| Reranker | BGE |

---

# Future Registry

Every new AI model must be registered here before entering production.
