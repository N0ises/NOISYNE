"""Central Qt stylesheet generation and application."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from .tokens import DEFAULT_TOKENS, DesignTokens


def build_stylesheet(tokens: DesignTokens = DEFAULT_TOKENS) -> str:
    c = tokens.colors
    s = tokens.spacing
    r = tokens.radius
    t = tokens.typography
    control = tokens.controls
    interaction = tokens.interaction
    return f"""
QWidget {{
    background-color: {c.background};
    color: {c.text_primary};
    font-family: \"{t.family}\";
    font-size: {t.body_size}px;
    selection-background-color: {c.selection};
}}
QMainWindow, QDialog {{ background-color: {c.background}; }}
QLabel {{ background: transparent; }}
QLabel[textRole="pageTitle"] {{
    color: {c.text_primary}; font-size: {t.page_title_size}px; font-weight: {t.strong_weight};
}}
QLabel[textRole="title"] {{
    color: {c.text_primary}; font-size: {t.title_size}px; font-weight: {t.strong_weight};
}}
QLabel[textRole="secondary"] {{ color: {c.text_secondary}; }}
QLabel[textRole="muted"], QLabel[textRole="caption"] {{
    color: {c.text_muted}; font-size: {t.caption_size}px;
}}
QLabel[textRole="metric"] {{
    color: {c.text_primary}; font-size: {t.metric_size}px; font-weight: {t.strong_weight};
}}
QFrame[component="card"], QFrame[component="panel"], QFrame[component="resultSection"] {{
    background-color: {c.surface}; border: {interaction.border_width}px solid {c.border};
    border-radius: {r.large}px;
}}
QFrame[component="panel"] {{ background-color: {c.surface_raised}; }}
QPushButton {{
    min-height: {control.standard_height}px; padding: 0 {s.lg}px;
    border: {interaction.border_width}px solid {c.border}; border-radius: {r.medium}px;
    background-color: {c.surface_raised}; color: {c.text_primary};
    font-weight: {t.medium_weight};
}}
QPushButton:hover {{ background-color: {c.surface_overlay}; border-color: {c.text_muted}; }}
QPushButton:pressed {{ background-color: {c.surface}; }}
QPushButton:focus {{ border: {interaction.focus_width}px solid {c.focus}; }}
QPushButton:disabled {{ background-color: {c.disabled_surface}; color: {c.disabled_text}; }}
QPushButton[variant="primary"] {{
    background-color: {c.accent}; color: {c.accent_text}; border-color: {c.accent};
}}
QPushButton[variant="primary"]:hover {{ background-color: {c.accent_hover}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {c.accent_pressed}; }}
QPushButton[variant="danger"] {{
    background-color: {c.error_surface}; color: {c.error}; border-color: {c.error};
}}
QPushButton[variant="icon"] {{
    min-width: {control.standard_height}px; max-width: {control.standard_height}px; padding: 0;
}}
QLineEdit, QComboBox {{
    min-height: {control.standard_height}px; padding: 0 {s.md}px;
    background-color: {c.surface}; color: {c.text_primary};
    border: {interaction.border_width}px solid {c.border}; border-radius: {r.medium}px;
}}
QLineEdit:hover, QComboBox:hover {{ border-color: {c.text_muted}; }}
QLineEdit:focus, QComboBox:focus {{ border: {interaction.focus_width}px solid {c.focus}; }}
QLineEdit:disabled, QComboBox:disabled {{
    background-color: {c.disabled_surface}; color: {c.disabled_text};
}}
QComboBox::drop-down {{ border: 0; width: {control.standard_height}px; }}
QCheckBox {{ spacing: {s.sm}px; background: transparent; min-height: {control.minimum_touch_target}px; }}
QCheckBox:focus {{ color: {c.focus}; }}
QCheckBox::indicator {{
    width: {tokens.icons.medium}px; height: {tokens.icons.medium}px;
    border: {interaction.border_width}px solid {c.border}; border-radius: {r.small}px;
    background-color: {c.surface};
}}
QCheckBox::indicator:checked {{ background-color: {c.accent}; border-color: {c.accent}; }}
QCheckBox::indicator:disabled {{ background-color: {c.disabled_surface}; border-color: {c.divider}; }}
QCheckBox[controlRole="toggle"]::indicator {{ width: {control.standard_height}px; border-radius: {r.pill}px; }}
QTabWidget::pane {{ border: {interaction.border_width}px solid {c.border}; border-radius: {r.medium}px; }}
QTabBar::tab {{
    background-color: {c.surface}; color: {c.text_secondary}; padding: {s.sm}px {s.lg}px;
    border-bottom: {interaction.focus_width}px solid transparent;
}}
QTabBar::tab:selected {{ color: {c.text_primary}; border-bottom-color: {c.accent}; }}
QTableView {{
    background-color: {c.surface}; alternate-background-color: {c.surface_raised};
    border: {interaction.border_width}px solid {c.border}; border-radius: {r.medium}px;
    gridline-color: {c.divider};
}}
QHeaderView::section {{
    background-color: {c.surface_raised}; color: {c.text_secondary}; padding: {s.sm}px;
    border: 0; border-bottom: {interaction.border_width}px solid {c.border};
}}
QProgressBar {{
    min-height: {s.sm}px; max-height: {s.sm}px; background-color: {c.disabled_surface};
    border: 0; border-radius: {r.small}px; text-align: center;
}}
QProgressBar::chunk {{ background-color: {c.accent}; border-radius: {r.small}px; }}
QLabel[status="idle"], QLabel[status="cancelled"], QLabel[status="unavailable"] {{
    color: {c.text_secondary}; background-color: {c.disabled_surface};
}}
QLabel[status="loading"], QLabel[status="running"], QLabel[status="info"] {{
    color: {c.info}; background-color: {c.info_surface};
}}
QLabel[status="ready"], QLabel[status="success"] {{
    color: {c.success}; background-color: {c.success_surface};
}}
QLabel[status="warning"] {{ color: {c.warning}; background-color: {c.warning_surface}; }}
QLabel[status="error"] {{ color: {c.error}; background-color: {c.error_surface}; }}
QLabel[status="disabled"] {{ color: {c.disabled_text}; background-color: {c.disabled_surface}; }}
QLabel[component="statusBadge"] {{
    padding: {s.xs}px {s.sm}px; border-radius: {r.pill}px; font-weight: {t.medium_weight};
}}
QFrame[semantic="info"] {{ border-left: {interaction.focus_width}px solid {c.info}; }}
QFrame[semantic="warning"] {{ border-left: {interaction.focus_width}px solid {c.warning}; }}
QFrame[semantic="error"] {{ border-left: {interaction.focus_width}px solid {c.error}; }}
QListWidget {{ background-color: {c.surface}; border: 0; padding: {s.sm}px; outline: 0; }}
QListWidget::item {{ padding: {s.md}px; border-radius: {r.medium}px; color: {c.text_secondary}; }}
QListWidget::item:hover {{ background-color: {c.surface_raised}; color: {c.text_primary}; }}
QListWidget::item:selected {{ background-color: {c.selection}; color: {c.text_primary}; }}
QListWidget:focus {{ border: {interaction.focus_width}px solid {c.focus}; }}
QStatusBar {{ background-color: {c.surface}; color: {c.text_secondary}; }}
QToolTip {{
    background-color: {c.surface_overlay}; color: {c.text_primary};
    border: {interaction.border_width}px solid {c.border};
}}
"""


def apply_theme(application: QApplication, tokens: DesignTokens = DEFAULT_TOKENS) -> None:
    application.setStyleSheet(build_stylesheet(tokens))
