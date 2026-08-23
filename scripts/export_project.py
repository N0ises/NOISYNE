from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OUTPUT = ROOT / "project_export.txt"

INCLUDE_EXTENSIONS = {
    ".py",
    ".md",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
}

IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "build",
    "dist",
}

IGNORE_FILES = {
    "project_export.txt",
}


def separator(title: str) -> str:
    return "\n" + "=" * 100 + "\n" + title + "\n" + "=" * 100 + "\n\n"


def write_tree(output):

    output.write(separator("PROJECT TREE"))

    for path in sorted(ROOT.rglob("*")):

        if any(part in IGNORE_DIRS for part in path.parts):
            continue

        relative = path.relative_to(ROOT)

        if path.is_dir():
            output.write(f"[DIR ] {relative}\n")
        else:
            output.write(f"[FILE] {relative}\n")


def write_file(path: Path, output):

    output.write(separator(str(path.relative_to(ROOT))))

    try:

        output.write(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

    except (OSError, UnicodeError) as ex:

        output.write(f"<< ERROR READING FILE >>\n{ex}")

    output.write("\n")


def write_sources(output):

    output.write(separator("SOURCE FILES"))

    files = []

    for path in ROOT.rglob("*"):

        if any(part in IGNORE_DIRS for part in path.parts):
            continue

        if not path.is_file():
            continue

        if path.name in IGNORE_FILES:
            continue

        if path.suffix.lower() not in INCLUDE_EXTENSIONS:
            continue

        files.append(path)

    files.sort()

    for file in files:

        write_file(file, output)


def main():

    with OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as output:

        output.write("PHASENOX PROJECT EXPORT\n")

        output.write("Architecture Review Package\n\n")

        write_tree(output)

        write_sources(output)

    print()

    print("=" * 80)

    print("PROJECT EXPORT CREATED")

    print(OUTPUT)

    print("=" * 80)


if __name__ == "__main__":
    main()
