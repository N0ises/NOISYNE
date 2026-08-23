from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from phasenox.resources.branding import (
    APP_ICON,
    ASCII_NAME,
    BRAND_ASSETS,
    DISPLAY_NAME,
    MONOCHROME_MARK,
    PRIMARY_LOGO,
    SPLASH,
    WORDMARK,
    WORDMARK_RHYTHM,
    BrandAssetName,
    get_brand_asset,
    materialize_brand_asset,
    read_brand_asset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_brand_metadata() -> None:
    assert DISPLAY_NAME == "PHASENØX"
    assert ASCII_NAME == "PHASENOX"
    assert WORDMARK_RHYTHM == "PHASE   NØX"
    assert PRIMARY_LOGO is BrandAssetName.PRIMARY_LOGO_DARK
    assert WORDMARK is BrandAssetName.WORDMARK_DARK
    assert APP_ICON is BrandAssetName.APP_ICON_256
    assert MONOCHROME_MARK is BrandAssetName.MONOCHROME_MARK
    assert SPLASH is BrandAssetName.SPLASH


def test_required_assets_exist_and_are_non_empty() -> None:
    assert set(BRAND_ASSETS) == set(BrandAssetName)

    for name, asset in BRAND_ASSETS.items():
        assert asset.name is name
        assert asset.resource().is_file()
        assert asset.width > 0
        assert asset.height > 0
        assert asset.media_type in {"image/png", "image/svg+xml"}
        assert asset.read_bytes()


def test_packaged_assets_are_exact_approved_source_copies() -> None:
    for asset in BRAND_ASSETS.values():
        source = PROJECT_ROOT / asset.source_path
        assert source.is_file()
        assert asset.read_bytes() == source.read_bytes()


def test_resource_access_does_not_depend_on_cwd(tmp_path: Path, monkeypatch) -> None:
    expected = read_brand_asset(PRIMARY_LOGO)
    monkeypatch.chdir(tmp_path)

    assert read_brand_asset("primary_logo_dark") == expected
    with materialize_brand_asset(APP_ICON) as path:
        assert path.is_file()
        assert path.read_bytes() == read_brand_asset(APP_ICON)


def test_unknown_asset_name_fails_clearly() -> None:
    with pytest.raises(KeyError, match="Unknown PHASENOX brand asset"):
        get_brand_asset("not_an_asset")


def test_branding_layer_imports_without_qt_or_heavy_runtime() -> None:
    code = (
        "import sys; "
        "from phasenox.resources.branding import DISPLAY_NAME, read_brand_asset; "
        "from phasenox.resources.branding import PRIMARY_LOGO; "
        "print(DISPLAY_NAME); print(len(read_brand_asset(PRIMARY_LOGO)) > 0); "
        "print(any(name == 'PySide6' or name.startswith('PySide6.') for name in sys.modules))"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT.parent,
        env=env,
    )

    assert result.stdout.splitlines() == ["PHASENØX", "True", "False"]
