# Desktop UI Sprint 1 Packaging Walking Skeleton

Status: passed with recorded production-packaging work

Environment: Windows 11, Python 3.12.10, PyInstaller 6.22.0, PySide6 6.11.1

This is a feasibility artifact, not a release bundle or installer.

## Gate result

The PyInstaller onedir shell was built and moved to
`E:\Build\SoundBrain-Sprint1-WalkingSkeleton`, outside the source checkout. It was run from
an unrelated temporary working directory.

| Check | Result |
|---|---|
| Native Qt shell starts and closes | Passed; exit code 0 |
| Qt platform plugins | Passed on the native Windows platform plugin |
| NumPy, SciPy, SoundFile and librosa imports | Passed in source and packaged shell |
| Transformers import | Passed in source and packaged shell |
| Torch import | Passed in source; deliberately excluded from this shell package |
| Packaged `runtime.yaml` via `importlib.resources` | Passed |
| Writable user-data path | Passed at `%LOCALAPPDATA%\SoundBrain\soundbrain.desktop`, outside install |
| Model/runtime initialization | No model loaded and no download attempted |
| Artifact footprint | 527,583,373 bytes across 3,893 files |

The probe is executed by the application worker foundation, so representative imports do
not block a Qt event handler.

## PyInstaller configuration truth

The spec explicitly collects the packaged configuration resources and declares hidden
imports for `numpy`, `scipy`, `soundfile`, `librosa`, and `transformers`. Standard PyInstaller
hooks supplied the Qt platform plugins and scientific native libraries.

The walking skeleton excludes Torch/Torchaudio/TorchVision and unrelated optional ML/data
ecosystems such as TensorFlow, JAX, Datasets, spaCy, OpenCV, ONNX Runtime, ChromaDB,
LangChain, NLTK, Pandas, PyArrow, and Tk. These exclusions describe this shell gate only;
they are not a claim that enabled future product capabilities can run without their declared
backends.

## Findings and risks

The first unfiltered build reached final collection but exhausted the C: temp volume. The
development venv contains a CUDA Torch build whose `torch/lib` directory alone is about
4.04 GB, and generic ML hooks recursively collected thousands of optional files. The failed
generated temp build was removed; no repository or user artifact was deleted.

The filtered walking skeleton proves that the Qt/application architecture and packaged
resource/user-path contracts are viable. It does not prove a final model-enabled bundle.

## Desktop Torch distribution decision

The normal Windows Desktop package will use a pinned **CPU-only Torch and Torchaudio
distribution**, built in a clean, controlled packaging environment. It must not inherit CUDA
packages from a development venv. This keeps the default artifact deterministic and usable on
Windows machines without an NVIDIA driver.

GPU acceleration will be a separate, explicit, optional GPU/CUDA distribution (or runtime
add-on if the selected packager supports a safely isolated add-on). It must pin a tested
Torch/CUDA combination and declare its supported driver/GPU matrix. The normal package will
not contain both CPU and CUDA runtimes, and installing the GPU option must not change the UI
contracts.

Desktop startup remains independent of local ML initialization. The adapter probes the
installed runtime lazily; missing/incompatible Torch, unavailable GPU drivers, or missing
model assets produce `Unavailable` or `Degraded` capability snapshots with reasons. They do
not prevent the Qt shell or deterministic V1 analysis from starting. No model/runtime
download may occur during shell startup.

Sprint 18 must validate on clean Windows machines:

- the pinned CPU-only package contains no CUDA DLL payload and can perform a lightweight
  tensor/Torchaudio operation plus representative enabled local-model initialization;
- deterministic analysis, shell startup, and clean shutdown work when optional model assets
  are absent and when local ML probing fails;
- the optional GPU distribution installs independently, reports the effective CUDA device,
  runs representative inference, and degrades cleanly to the supported CPU path (or a clear
  unavailable state) for missing/unsupported drivers;
- CPU and GPU artifact size, licensing, signing, update, uninstall/reinstall, and user-data
  compatibility are recorded;
- capability probes never label a local ML feature Ready solely because Torch imports, and
  no first-run model download is implicit.

PyInstaller also warned that the optional Numba TBB pool could not resolve `tbb12.dll`. The
tested librosa import succeeded without that backend. A production audio workload must either
bundle TBB when required or exclude/avoid that optional execution path.

No Sprint 1 packaging finding requires changing the Qt, Presentation, UI Contract, or
application-adapter boundaries before Sprint 2.

## Live-RAG termination classification

Classification: **UNKNOWN; not attributable to Sprint 1 on current evidence**.

The earlier complete run emitted a Windows native access-violation trace in the
PyArrow/Pandas/Scikit-learn import chain near
`test_soundbrain_service_rag_does_not_crash_when_empty`. Final verification found:

- Sprint 1 changed no RAG, embedding, `SoundBrainService`, or live-RAG test source;
- Sprint 1 project metadata added only optional PySide6, pytest-qt, and PyInstaller extras;
  the existing backend dependency declarations were unchanged;
- the Sprint 1 editable install reported the backend/ML dependencies as already satisfied
  and installed only the desktop/test/packaging packages;
- the isolated live-RAG test passed with normal plugin discovery (`1 passed`) and with all
  third-party pytest plugin autoload disabled (`1 passed`);
- the complete frozen-backend suite, excluding `tests/ui`, passed with plugin autoload
  disabled (`262 passed`);
- `pip check` reported one unrelated pre-existing PDF/OCR dependency mismatch
  (`unstructured-client` expects a newer `pypdfium2`), not a PyArrow/RAG or Desktop conflict.

Because the native termination is no longer reproducible and there is no captured pre-Sprint
run showing the same termination, it cannot honestly be classified as proven pre-existing.
The unchanged backend dependency/source evidence and successful plugin-isolated runs also do
not support classifying it as caused by Sprint 1. No dependency correction or backend change
is justified by the available evidence.
