from __future__ import annotations

from dataclasses import replace

from phasenox.ui.design_system.theme import apply_theme, build_stylesheet
from phasenox.ui.design_system.tokens import DEFAULT_TOKENS


def test_tokens_cover_required_design_roles() -> None:
    tokens = DEFAULT_TOKENS

    assert tokens.colors.background
    assert tokens.colors.surface_raised
    assert tokens.colors.text_primary
    assert tokens.colors.border
    assert tokens.colors.border_strong
    assert tokens.colors.accent_hover
    assert tokens.colors.accent_pressed
    assert tokens.colors.focus
    assert tokens.colors.disabled_text
    assert tokens.colors.success
    assert tokens.colors.warning
    assert tokens.colors.error
    assert tokens.colors.info
    assert tokens.colors.unavailable
    assert tokens.colors.unknown
    assert tokens.colors.running
    assert tokens.colors.degraded
    assert tokens.colors.intelligence
    assert tokens.spacing.xxs < tokens.spacing.sm < tokens.spacing.xl
    assert tokens.typography.caption_size < tokens.typography.page_title_size
    assert "Geist" in tokens.typography.family
    assert "Segoe UI" in tokens.typography.family
    assert "Consolas" in tokens.typography.mono_family
    assert tokens.radius.small < tokens.radius.large
    assert tokens.controls.compact_height < tokens.controls.large_height
    assert tokens.icons.small < tokens.icons.large


def test_stylesheet_is_generated_from_replaceable_tokens(qapp) -> None:
    replacement = "#010203"
    tokens = replace(DEFAULT_TOKENS, colors=replace(DEFAULT_TOKENS.colors, accent=replacement))

    stylesheet = build_stylesheet(tokens)
    apply_theme(qapp, tokens)

    assert replacement in stylesheet
    assert qapp.styleSheet() == stylesheet
    assert 'QPushButton[variant="primary"]' in stylesheet
    assert ":focus" in stylesheet
    assert ":disabled" in stylesheet
    apply_theme(qapp, DEFAULT_TOKENS)


def test_neutral_text_and_semantic_pairs_have_readable_contrast() -> None:
    colors = DEFAULT_TOKENS.colors
    pairs = (
        (colors.text_primary, colors.background),
        (colors.text_secondary, colors.surface),
        (colors.success, colors.success_surface),
        (colors.warning, colors.warning_surface),
        (colors.error, colors.error_surface),
        (colors.info, colors.info_surface),
    )

    assert all(_contrast_ratio(foreground, background) >= 4.5 for foreground, background in pairs)


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

