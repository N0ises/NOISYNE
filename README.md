# PHASENØX

> A modular AI-powered Audio Intelligence Platform.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Status](https://img.shields.io/badge/Status-Active-success)
![Architecture](https://img.shields.io/badge/Architecture-Modular-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

# Overview

PHASENØX is a modular artificial intelligence platform for professional audio analysis, understanding, reasoning, and recommendation.

Unlike traditional audio analyzers that only measure technical metrics, PHASENØX combines deterministic signal processing, machine learning, semantic embeddings, retrieval systems, and large language models into a unified architecture capable of understanding audio from both engineering and musical perspectives.

The project is designed around clean architecture principles where every subsystem has a single responsibility and can evolve independently.

---

# Vision

Create one of the most complete open modular platforms for Audio Intelligence.

PHASENØX aims to become an engineering platform capable of:

- Audio Analysis
- Audio Understanding
- Semantic Audio Search
- Reference Matching
- Audio Reasoning
- AI Assisted Mixing
- AI Assisted Mastering
- Intelligent Recommendations
- Knowledge Retrieval
- Autonomous Audio Engineering

---

# Core Pipeline

```text
Audio Input
      │
      ▼
Deterministic Measurement
      │
      ▼
Engineering Analysis
      │
      ▼
Audio Embeddings
      │
      ▼
Context Builder
      │
      ▼
Reference Retrieval
      │
      ▼
Reasoning Engine
      │
      ▼
Large Language Model
      │
      ▼
Recommendation Engine
      │
      ▼
Professional Report
```

---

# Architecture Principles

- Modular Design
- Layer Isolation
- Dependency Injection
- Runtime Independence
- Provider Agnostic
- AI Model Abstraction
- Reproducible Results
- Testability
- Extensibility

Every component should have one responsibility.

Runtime never depends on domain logic.

Business logic never depends on model implementations.

Models are replaceable without changing the pipeline.

---

# Main Components

```
phasenox/
│
├── runtime/
├── audio/
├── embeddings/
├── intelligence/
├── reasoning/
├── reference/
├── recommendation/
├── memory/
├── rag/
├── reports/
├── llm/
├── services/
├── pipeline/
└── utils/
```

---

# Project Structure

```
<repository-directory>/

phasenox/
tests/
docs/
configs/
scripts/
data/
models/

pyproject.toml
requirements.txt
requirements-dev.txt
pytest.ini
README.md
```

---

# Features

- Modular Runtime
- Dynamic Model Loading
- Dependency Injection
- Audio Feature Extraction
- Loudness Analysis
- Spectral Analysis
- Semantic Audio Embeddings
- Similarity Search
- Reference Analysis
- RAG Integration
- LLM Reasoning
- Recommendation Engine
- Report Generation

---

# Supported AI Models

Current architecture supports multiple providers.

Examples include:

- CLAP
- BGE
- Whisper
- Qwen
- Sentence Transformers

Additional providers can be integrated without modifying the Runtime.

---

# Design Goals

- Production Ready
- Easily Extendable
- GPU Friendly
- CPU Compatible
- Clean APIs
- Fully Tested
- Architecture First

---

# Installation

Install the published package:

```bash
pip install phasenox
```

Install optional PDF/OCR support when required:

```bash
pip install "phasenox[pdf]"
```

For development from a source checkout:

Clone the repository

```bash
git clone <repository-url>
cd <repository-directory>
```

Create virtual environment

```bash
python -m venv .venv
```

Activate

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -e .
pip install -r requirements-dev.txt
```

Canonical product and compatibility identities:

```text
Product: PHASENØX
ASCII identity: PHASENOX
Distribution: phasenox
Canonical Python package: phasenox
Legacy Python package: brain (compatibility only)
Canonical CLI: phasenox
Canonical service: PhasenoxService
Legacy services: NoisyneService, SoundBrainService (compatibility aliases)
```

New integrations should use canonical imports:

```python
from phasenox.application import PhasenoxService
```

Existing `brain.*` imports remain supported during the compatibility period.

Use the canonical CLI for new workflows:

```bash
phasenox --help
```

Application-root precedence is `PHASENOX_ROOT`, then the legacy
`NOISYNE_ROOT`, then `SOUNDBRAIN_ROOT`, then automatic structural detection.

The product and distribution are PHASENØX/phasenox.

```text
Repository: N0ises/NOISYNE
Repository rename: completed
Canonical origin: https://github.com/N0ises/NOISYNE.git
```

The canonical repository URL and local `origin` now use the final NOISYNE
repository identity directly and do not rely on the legacy redirect.

---

# Running Tests

```bash
pytest
```

---

# Documentation

Complete project documentation is available inside the `docs/` directory.

Main documents include:

- [Technical Rename Freeze](docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md)
- Architecture
- Vision
- Engineering Guidelines
- Roadmap
- Design Patterns
- Technical Debt
- Execution Plan
- Security
- Contribution Guide

---

# Development Philosophy

PHASENØX follows an Architecture First development model.

Every new feature must satisfy the following principles:

- No circular dependencies
- Single Responsibility
- Layer Isolation
- Test Coverage
- Documentation
- Backward Compatibility

Implementation comes after architecture.

---

# Current Status

Current development focuses on building the core platform before advanced AI capabilities.

Major milestones include:

- Runtime
- Audio Intelligence
- Reference Intelligence
- Reasoning
- Recommendation
- Memory
- Knowledge
- Autonomous Engineering

---

# License

MIT License

---

# Author

Hamid Haddadi

---

PHASENØX is an ongoing long-term engineering project focused on building a scalable, modular, and production-ready Audio Intelligence platform.
