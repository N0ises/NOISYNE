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
Before a release package enables local Torch inference, the project must select and test a
deliberate CPU/GPU distribution policy, build in a controlled environment with adequate disk
space, and add capability-specific hooks rather than inheriting every package in a developer
venv.

PyInstaller also warned that the optional Numba TBB pool could not resolve `tbb12.dll`. The
tested librosa import succeeded without that backend. A production audio workload must either
bundle TBB when required or exclude/avoid that optional execution path.

No Sprint 1 packaging finding requires changing the Qt, Presentation, UI Contract, or
application-adapter boundaries before Sprint 2.
