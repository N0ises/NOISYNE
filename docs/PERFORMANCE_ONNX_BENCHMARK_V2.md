# NØISYNE V2 — Performance Baseline and ONNX Runtime Benchmark

Sprint 14 establishes a **truthful, machine-specific performance baseline** for the
NØISYNE V2 backend.  It does **not** claim universal speed-ups, it does **not** make
ONNX or GPU the default, and it does **not** implement scheduling, UI, or model
download management.

Core principle:

> **Fastest validated runtime** — not the most hyped runtime.

A runtime candidate (ONNX, quantized, GPU, etc.) is selectable only after it passes
compatibility **and** output-equivalence checks against a trusted canonical runtime.

---

## 1. What Sprint 14 adds

- Strict JSON-safe performance contracts in `noisyne.performance.contracts`.
- Environment snapshot that reports only what it can actually measure.
- Deterministic benchmark methodology (warmup, repeated timed samples,
  cold/warm separation, median/mean/p95 aggregation).
- Representative NØISYNE workload wrappers (auditory frontend, brightness correlate,
  reference comparison).
- Runtime availability, equivalence, and selection foundation.
- Optional PyTorch → ONNX fixture-model export and comparison.
- A developer-facing benchmark entry point: `python -m noisyne.performance`.
- Three conservative capability records:
  - `performance_benchmark_foundation`
  - `runtime_selection_foundation`
  - `onnx_runtime_optimization`

---

## 2. Contracts

All public Sprint 14 contracts inherit from `JsonContract`:

- deterministic `to_dict()` / `from_dict()` round-trip
- finite numerics only (`NaN` / `Inf` rejected)
- enum values serialized as strings
- explicit units in field names (`_seconds`, `_bytes`, `_per_second`)

Key contracts:

| Contract | Purpose |
|----------|---------|
| `PerformanceEnvironment` | OS, Python, CPU, RAM, GPU, CUDA, PyTorch, ONNX Runtime providers. |
| `PerformanceWorkload` | Workload identity, type, duration, determinism, limitations. |
| `PerformanceBenchmarkResult` | One workload × runtime measurement with cold/warm/latency/throughput/memory. |
| `LatencyStatistics` | mean, median, min, max, p95 from timed samples. |
| `MemoryMeasurement` | RAM and GPU allocated / reserved bytes, all nullable. |
| `CompatibilityResult` | `available` / `unavailable` / `incompatible` / `failed`. |
| `EquivalenceResult` | `equivalent` / `within_tolerance` / `different` / `failed` / `not_evaluated`. |
| `RuntimeCandidate` | A runtime with compatibility, equivalence, and benchmark evidence. |
| `RuntimeSelectionPolicy` | Policy for deterministic selection. |
| `RuntimeSelectionResult` | Selected/fallback/rejected outcome with reasons. |
| `BenchmarkFingerprint` | Stable identity for invalidating cached benchmark results. |

No contract contains a universal performance score, hidden weighting, or
confidence percentage.

---

## 3. Environment snapshot

`capture_environment()` builds a `PerformanceEnvironment` from the current host.

Captured when available:

- `os_name`, `os_version`, `architecture`, `python_version`
- `cpu_brand`, `logical_cores`, `total_ram_bytes`
- `gpu_name`, `gpu_total_vram_bytes`, `cuda_available`, `cuda_version`
- `torch_version`, `onnxruntime_version`, `onnxruntime_providers`

Missing or unmeasurable fields are explicitly `None` or empty lists.
The snapshot never fabricates hardware data.

---

## 4. Benchmark methodology

`BenchmarkMethod` declares:

- `warmup_iterations` (default `3`)
- `timed_iterations` (default `10`)

`measure_latency()` produces:

- one `cold` sample (first call)
- `warmup_iterations` `warmup` samples
- `timed_iterations` `timed` samples

`aggregate_timed_samples()` reports median, mean, min, max, and p95 (when
sample count ≥ 2) using **only** the `timed` phase.

`benchmark_callable()` wraps the methodology with optional memory sampling
(uses `psutil` for RAM, `torch.cuda` for GPU when available).  Missing measurement
APIs are recorded as unavailable, not fabricated.

---

## 5. Workloads

Sprint 14 wraps existing deterministic V2 paths so they can be benchmarked
without adding new perception features:

- `AuditoryFrontendWorkload` — Sprint 2 auditory frontend
- `BrightnessDescriptorWorkload` — Sprint 5 brightness correlate
- `ReferenceComparisonWorkload` — Sprint 9 reference comparison

All use deterministic synthetic sine audio.  Workload objects carry explicit
limitations, e.g.:

> "Synthetic sine input; not representative of full music content."

Unit tests use short (~1 s) workloads.  The classes support 10 s / 60 s / 5 min
durations for explicit developer benchmarks.

---

## 6. Resource profiles

Profiles are **policy declarations only** in Sprint 14.  They do not implement
scheduler throttling (deferred to Sprint 16).

- `LOW_RESOURCE` — CPU-only, limited RAM, no discrete GPU assumption, cold-start
  sensitive.
- `BALANCED` — default desktop-class target.
- `PERFORMANCE` — favor throughput where validated.

---

## 7. Runtime candidates

Known backend/device/precision combinations:

| Runtime | Device | Precision | Notes |
|---------|--------|-----------|-------|
| PyTorch | CPU | FP32 | Canonical/reference candidate on most machines. |
| PyTorch | CUDA | FP32 | Available only if `torch.cuda.is_available()` is true. |
| PyTorch | CPU | FP16 | Marked incompatible on CPU. |
| ONNX Runtime | CPU | FP32 | Available if `onnxruntime` is installed. |
| ONNX Runtime | CUDA | FP32 | Available only if `CUDAExecutionProvider` is present. |
| INT8 / BF16 | any | — | Marked incompatible for Sprint 14. |

Unavailable runtimes are valid results, not failures.

---

## 8. Output equivalence

`evaluate_equivalence()` compares a candidate runtime against a canonical
reference on a deterministic fixture.

Supported policies:

- `EXACT` — bit-exact equality; status becomes `EQUIVALENT` only when max
  absolute difference is exactly zero.
- `ABSOLUTE_TOLERANCE` — `max_abs_diff ≤ tolerance_value` → `WITHIN_TOLERANCE`.
- `RELATIVE_TOLERANCE` — `max_rel_diff ≤ tolerance_value`.
- `DOMAIN_SPECIFIC` — placeholder; treated as absolute tolerance for Sprint 14.

Tolerances are **not** universal.  They depend on operation, dtype, precision,
provider, and device.  A faster candidate that fails equivalence is **never**
selected.

---

## 9. Quantization boundary

Sprint 14 models precisions `FP32`, `FP16`, `BF16`, and `INT8` as policy
concepts, but it does **not** blindly quantize production models.

For each quantized candidate the framework records:

- compatibility
- latency change
- memory change
- output deviation / equivalence status

A quantized candidate is selectable only after declared equivalence passes.
In this sprint INT8 and BF16 are conservatively rejected.

---

## 10. Cold / warm / load metrics

Sprint 14 keeps these separate:

- `startup_load_time_seconds` — import / model load cost
- `cold_latency_seconds` — first inference after load
- `warm_statistics` — steady-state repeated inference
- `throughput_per_second` — derived from warm median latency

They are never collapsed into a single headline number.

---

## 11. Memory measurement limitations

Measured when reliable APIs exist:

- Process RSS via `psutil`
- GPU allocated / reserved bytes via `torch.cuda` when CUDA is active
- GPU total / free VRAM only when the API genuinely reports it

If a measurement API is missing, the contract records `None`.
Memory observations are **not** guaranteed peak measurements.

---

## 12. Runtime selection

`select_runtime()` prioritizes, in order:

1. Compatibility (`available`)
2. Output equivalence / validation (if required)
3. Requested device / policy constraints
4. Resource fit
5. Measured performance (lowest warm median latency, then throughput)

If no optimized candidate passes, the policy can fall back to the canonical
runtime.  If fallback is disabled and nothing passes, the result is
`NO_CANDIDATE` with documented rejection reasons.

---

## 13. Canonical / reference runtime

The existing trusted implementation is the canonical reference.
ONNX, quantized, and GPU candidates are **optimization candidates only**.
Optimization must not silently redefine numerical or scientific truth.

---

## 14. Benchmark fingerprint

`BenchmarkFingerprint` combines environment + runtime + workload + method
identity:

- OS, architecture, Python version
- CPU brand, logical cores, total RAM
- GPU name
- PyTorch / ONNX Runtime versions
- runtime identity, precision, workload ID, benchmark method version

Benchmark results must not be reused across incompatible environments.

---

## 15. Optional developer benchmark entry point

```bash
python -m noisyne.performance --help
python -m noisyne.performance --no-fixture --output benchmark.json
```

The CLI:

- is offline by default
- has no Desktop dependency
- writes JSON output
- skips fixture model benchmarks with `--no-fixture`

---

## 16. Optional dependencies

ONNX Runtime, ONNX, and `psutil` are optional extras:

```toml
[project.optional-dependencies]
performance = ["onnxruntime", "onnx", "psutil"]
```

Core NØISYNE V2 does not require ONNX or CUDA packages.

---

## 17. Observed runtime availability on the development machine

- PyTorch: installed
- CUDA: available (`torch.cuda.is_available()` true)
- ONNX Runtime: installed, providers include `CPUExecutionProvider`
- `onnx` Python package: **not installed in the current venv**
  - Fixture model export is therefore skipped in tests.
  - Install the `performance` extra to enable export.

---

## 18. Blocked / unavailable paths

- Production model ONNX export: not attempted in Sprint 14.
- INT8 / BF16 quantization: rejected by policy.
- CUDA ONNX Runtime: unavailable because `CUDAExecutionProvider` is absent.
- GPU memory measurement on non-CUDA machines: unavailable.

---

## 19. Future consumption

Sprint 15 / Sprint 16 may consume Sprint 14 as follows:

- Use `RuntimeSelectionResult` evidence to choose a runtime for a model-backed
  capability.
- Use `BenchmarkFingerprint` to cache or invalidate benchmark evidence.
- Use `PerformanceProfile` policy names to guide job-scheduler resource choices.
- Extend `PerformanceWorkload` for new model-backed workloads.

Sprint 14 does **not** implement:

- Task Center / job queue / pause-resume
- Async multi-task scheduler
- Desktop resource monitor UI
- Settings UI
- Model download manager
- Installer changes

---

## 20. Explicit non-claims

These statements are intentionally **prohibited** in Sprint 14 outputs and
product messaging:

- ONNX is automatically faster than PyTorch.
- GPU is automatically faster than CPU.
- Quantized precision is automatically acceptable.
- Lower latency means correct output.
- A benchmark on one machine is universal performance.
- A memory observation is a guaranteed peak measurement.
- A retrieval or benchmark score is a confidence percentage.

---

## 21. Validation status

New Sprint 14 capabilities are registered as:

| Capability | Implementation | Validation | Reason |
|------------|----------------|------------|--------|
| `performance_benchmark_foundation` | IMPLEMENTED | FOUNDATION_ONLY | Contracts and methodology exist; real production workloads not exhaustively benchmarked. |
| `runtime_selection_foundation` | IMPLEMENTED | FOUNDATION_ONLY | Deterministic selection logic verified; production runtime matrix not populated. |
| `onnx_runtime_optimization` | IMPLEMENTED | FOUNDATION_ONLY | Framework supports ONNX evaluation; actual production ONNX export not performed. |

They are **not** marked `Production/Ready`.

---

## 22. Files added / changed

- `noisyne/performance/` package
  - `__init__.py`, `__main__.py`
  - `_common.py`
  - `contracts.py`
  - `environment.py`
  - `benchmark.py`
  - `runtime.py`
  - `fixture_model.py`
  - `workloads.py`
  - `benchmark_cli.py`
- `noisyne/runtime/capabilities.py` — three new capabilities
- `pyproject.toml` — `[project.optional-dependencies] performance`
- `tests/test_sprint14_performance_baseline.py`
- `docs/PERFORMANCE_ONNX_BENCHMARK_V2.md`
