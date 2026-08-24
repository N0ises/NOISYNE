# PHASENOX Windows packaging

This directory owns the Windows x64 `desktop-core` release-candidate pipeline.
It is intentionally independent from the monolithic development dependency set
in `pyproject.toml`.

The standard profile promises:

- Desktop shell/navigation and Task Center for supported jobs;
- deterministic local audio analysis;
- deterministic reference comparison;
- report preview and export;
- read-only Settings/runtime status; and
- deterministic Intelligence output produced by the core analysis path.

Knowledge/RAG, semantic/model analysis, LLM reasoning, CPU ML, GPU/CUDA, and
model download are unavailable in this profile. Capability truth must expose
those features as unavailable rather than importing or downloading their
runtimes.

`requirements/desktop-core-windows-x64.lock` contains runtime packages only.
It deliberately uses `PySide6-Essentials` instead of the `PySide6` meta-package,
because that meta-package requires the Addons wheel and would reintroduce the
QML/Quick/PDF/WebEngine payload excluded by the Desktop Core contract.
`requirements/build-windows-x64.lock` contains freezer, inspection, SBOM, and
license tooling. Both locks are generated from their adjacent `.in` files with
Python 3.12.10 and hashes enabled.

The build entry point will be `tools/release/build_desktop_core.ps1`. Build
outputs, virtual environments, generated icons/version files, and release
artifacts remain under ignored build/dist directories.
