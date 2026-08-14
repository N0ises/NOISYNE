# ChatGPT Export V2

This tool creates review-friendly exports for large codebases. The default output
folder is `exports/`; it is automatically excluded from later scans.

## NØISYNE developer-tool standard

All development-only commands live in `tools/`. Each tool has one descriptive
entry-point file (for example, `lint_project.py`) and may keep its reusable logic
in a dedicated package under `tools/`. Tools must be safe to run repeatedly,
write generated artifacts outside source packages, provide `--help`, and document
their outputs and examples in this file.

Suggested tools:

```text
tools/
├── export_project.py
├── lint_project.py
├── check_architecture.py
├── benchmark_models.py
├── build_docs.py
├── profile_runtime.py
└── migrate_project.py
```

## Commands

```powershell
# Full export: tree, grouped source files, JSON manifests, and diagnostics
py -3 tools/export_project.py --full

# Export only a module or a nested directory name
py -3 tools/export_project.py --module audio
py -3 tools/export_project.py --module embeddings

# Generate focused analysis outputs
py -3 tools/export_project.py --stats
py -3 tools/export_project.py --architecture
py -3 tools/export_project.py --tree

# Restrict any export to Git working-tree changes or a text search
py -3 tools/export_project.py --changed --full
py -3 tools/export_project.py --search AudioEncoder --full
```

`--module embeddings` matches any file whose path contains `embeddings`, so a
directory such as `noisyne/audio/embeddings/` is exported by itself.

## Output

`--full` produces `tree.txt`, `requirements.txt`, `statistics.json`,
`architecture.json`, `api_manifest.json`, the `root.txt`/`scripts.txt`/`docs.txt`
groups, a file for each standard `noisyne` module, the explicit `brain`
compatibility report, and reports for unused modules, duplicate symbols, circular
imports, and the import graph. Every text file includes its generation time;
module files also contain file contents, a summary, and an end marker.

`tree.txt` now contains the full logical project structure, including empty
directories and files outside the content filters. It excludes only intentional
noise such as Git metadata, virtual environments, dependencies, generated output,
and paths listed in `.exportignore`.

Every run also writes `manifest.json`. It lists every generated file and its byte
size, and the command prints the same output directory plus a short artifact
list. Use this file as the definitive check that an export completed.

## Ignore rules

Create `.exportignore` in the project root. It accepts one directory or wildcard
per line, with comments beginning with `#`. Use a trailing slash for directories.
Copy the LM Studio rules from `.exportignore.example` when needed:

```gitignore
.lmstudio/
LM Studio/
*.gguf
*.safetensors
*.bin
```

Dependency folders (including `venv/`), Git metadata, build output, `exports/`,
and common LM Studio directories are skipped automatically. Use
`--max-file-size 500000` to keep a very large project export compact.
