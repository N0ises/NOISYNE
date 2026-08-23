# NØISYNE

> **Audio Intelligence System**

NØISYNE is an AI platform for professional audio engineering.

Unlike traditional analyzers that only report measurements, NØISYNE
is designed to perceive, understand, reason, explain, automate, and
eventually create audio using modern AI, DSP, psychoacoustics, and
engineering knowledge.

------------------------------------------------------------------------

# Vision

Build the world's most capable Audio Intelligence System.

------------------------------------------------------------------------

# What Makes NØISYNE Different

Traditional software answers:

-   What is the LUFS?
-   Is there clipping?
-   What is the peak?

NØISYNE answers:

-   Why does the mix sound this way?
-   Should anything actually be changed?
-   What is the engineering reasoning?
-   What would an experienced engineer do?
-   Can AI perform those actions automatically?

------------------------------------------------------------------------

# Core Capabilities

Current

-   Audio Analysis
-   DSP Metrics
-   Engineering Engine
-   Semantic Audio Intelligence
-   Reference Comparison
-   AI Reasoning
-   Mix Intelligence
-   Professional Reports
-   JSON Export
-   Validation

Planned

-   Psychoacoustic Intelligence
-   DAW Automation
-   Plugin Control
-   Knowledge Graph
-   Audio Memory
-   Agent Collaboration
-   Music Generation
-   Autonomous Audio Engineering

------------------------------------------------------------------------

# High-Level Architecture

Infrastructure

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

------------------------------------------------------------------------

# Technology Stack

-   Python
-   PyTorch
-   Transformers
-   CLAP Embeddings
-   Local LLMs
-   DSP
-   Librosa
-   NumPy

Future

-   CUDA optimization
-   ONNX
-   TensorRT
-   Distributed inference

------------------------------------------------------------------------

# Roadmap

Version 1

Professional Audio Intelligence

↓

Version 2

Perceptual Intelligence

↓

Version 3

Autonomous Mixing

↓

Version 4

Audio Foundation Model

↓

Version 5

Autonomous Audio Intelligence System

------------------------------------------------------------------------

# Guiding Principles

-   Perception before Measurement
-   Understanding before Recommendation
-   Explain Every Decision
-   Human-Centered Intelligence
-   Multimodal Understanding
-   Engineering + AI

------------------------------------------------------------------------

# Repository Structure

docs/ Documentation

phasenox/ Canonical core intelligence

brain/ Legacy Python import compatibility shim

tests/ Automated tests

reports/ Generated reports

The installed distribution is `phasenox`. New Python integrations should import
from `phasenox.*`; `brain.*` remains available only as a compatibility namespace.

Canonical installation and interfaces:

```bash
pip install phasenox
pip install "phasenox[pdf]"
phasenox --help
```

```python
from phasenox.application import NoisyneService
```

The `brain` namespace and `SoundBrainService` remain supported compatibility
aliases. The former `noisyne` and `soundbrain` CLI commands are no longer
installed. Application-root precedence is `NOISYNE_ROOT`, then legacy
`SOUNDBRAIN_ROOT`, then automatic structural detection.

------------------------------------------------------------------------

# Status

Core Engine: ✅ Production

Audio Analysis: ✅ Production

Engineering Engine: ✅ Production

Semantic Audio Intelligence: ✅ Verified

Reference AI: ✅ Production

Mix Intelligence: ✅ Production

Plugin Intelligence: ✅ Production

Knowledge Infrastructure: ✅ Production

Memory & Personalization: ✅ Production

Evaluation & Benchmark: ✅ Production

Workflow Integration Contracts: ✅ Production

AI Provider Layer: ✅ Production

CLI: ✅ Production

Release Status: **1.0.0**

Next: V1.1 cleanup, real HTTP LLM providers, full reference segmentation, and
perceptual intelligence research.

------------------------------------------------------------------------

# Long-Term Goal

Create an AI that can think, explain, recommend, automate, and create
professional audio like an experienced engineer while remaining
transparent, auditable, and human-centered.
