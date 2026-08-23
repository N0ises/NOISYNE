from __future__ import annotations

from pathlib import Path

import pytest

from phasenox.ui.adapters.v2 import V2ApplicationAdapter
from phasenox.ui.contracts import ReportDescriptor, ReportExportCommand


def _descriptor(path: Path, *, kind="analysis", format="json") -> ReportDescriptor:
    return ReportDescriptor(
        kind=kind,
        format=format,
        path=path,
        display_label=path.name,
        source_path=Path("mix.wav"),
    )


def test_json_preview_is_safe_pretty_utf8_with_real_filesystem_metadata(
    product_metadata, tmp_path
) -> None:
    path = tmp_path / "analysis.json"
    path.write_text('{"summary":"Café","score":91}', encoding="utf-8")

    preview = V2ApplicationAdapter(metadata=product_metadata).load_report(_descriptor(path))

    assert preview.content == '{\n  "summary": "Café",\n  "score": 91\n}'
    assert preview.size_bytes == len(path.read_bytes())
    assert preview.filesystem_modified_at.tzinfo is not None
    assert preview.warnings == ()


def test_invalid_json_shows_original_text_with_truthful_warning(product_metadata, tmp_path) -> None:
    path = tmp_path / "analysis.json"
    path.write_text("{invalid", encoding="utf-8")

    preview = V2ApplicationAdapter(metadata=product_metadata).load_report(_descriptor(path))

    assert preview.content == "{invalid"
    assert preview.warnings == ("JSON formatting failed; showing the original UTF-8 text.",)


def test_reference_markdown_preview_is_plain_text(product_metadata, tmp_path) -> None:
    path = tmp_path / "reference_report.md"
    path.write_text("# Reference\n\nNo HTML execution.", encoding="utf-8")
    descriptor = _descriptor(path, kind="reference_comparison", format="markdown")

    preview = V2ApplicationAdapter(metadata=product_metadata).load_report(descriptor)

    assert preview.content == "# Reference\n\nNo HTML execution."


def test_missing_unsupported_and_large_reports_are_handled(product_metadata, tmp_path) -> None:
    adapter = V2ApplicationAdapter(metadata=product_metadata)
    with pytest.raises(FileNotFoundError):
        adapter.load_report(_descriptor(tmp_path / "missing.json"))
    with pytest.raises(ValueError):
        adapter.load_report(_descriptor(tmp_path / "fake.pdf", format="pdf"))

    large = tmp_path / "large.json"
    large.write_bytes(b" " * (adapter._MAX_REPORT_PREVIEW_BYTES + 1))
    preview = adapter.load_report(_descriptor(large))
    assert preview.content is None
    assert "exceeds 2 MiB" in preview.unavailable_reason


def test_export_copies_exact_bytes_and_preserves_descriptor_truth(
    product_metadata, tmp_path
) -> None:
    source = tmp_path / "analysis.json"
    source.write_bytes(b'{"exact":true}\r\n')
    destination = tmp_path / "copied.json"
    descriptor = _descriptor(source)

    result = V2ApplicationAdapter(metadata=product_metadata).export_report(
        ReportExportCommand(descriptor, destination)
    )

    assert destination.read_bytes() == source.read_bytes()
    assert result.exported.path == destination
    assert result.exported.format == "json"
    assert result.exported.source_path == Path("mix.wav")


def test_export_rejects_wrong_extension_and_unconfirmed_overwrite(
    product_metadata, tmp_path
) -> None:
    source = tmp_path / "analysis.json"
    source.write_text("{}", encoding="utf-8")
    descriptor = _descriptor(source)
    adapter = V2ApplicationAdapter(metadata=product_metadata)

    with pytest.raises(ValueError):
        adapter.export_report(ReportExportCommand(descriptor, tmp_path / "copy.md"))

    destination = tmp_path / "copy.json"
    destination.write_text("original", encoding="utf-8")
    with pytest.raises(FileExistsError):
        adapter.export_report(ReportExportCommand(descriptor, destination))
    assert destination.read_text(encoding="utf-8") == "original"

    adapter.export_report(ReportExportCommand(descriptor, destination, overwrite=True))
    assert destination.read_text(encoding="utf-8") == "{}"
