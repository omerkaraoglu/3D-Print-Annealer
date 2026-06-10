from pathlib import Path

COLORS = {
    "bg_dark":    "#1a1a2e",
    "bg_medium":  "#16213e",
    "bg_light":   "#1e293b",
    "fg":         "#cdd6f4",
    "fg_dim":     "#94a3b8",
    "border":     "#334155",
    "accent":     "#89b4fa",
    "red":        "#f38ba8",
    "green":      "#a6e3a1",
    "yellow":     "#f9e2af",
    "cyan":       "#89dceb",
    "orange":     "#fab387",
    "pink":       "#f5c2e7",
    "mauve":      "#cba6f7",
}

# Qt's QSS `url()` does not accept data URIs; it wants a filesystem
# (or qrc:) path. We resolve the bundled SVG to its absolute path at
# import time and inject it into the stylesheet. Forward slashes work
# on Windows in QSS too.
_RESOURCES = Path(__file__).parent / "resources"
_DOWN_ARROW_PATH = (_RESOURCES / "down_arrow.svg").as_posix()

DARK_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["fg"]};
}}

QWidget {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["fg"]};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}}

QTabWidget::pane {{
    border: 1px solid {COLORS["border"]};
    background-color: {COLORS["bg_medium"]};
    border-radius: 4px;
}}

QTabWidget::tab-bar {{
    left: 4px;
}}

QTabBar::tab {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["fg_dim"]};
    border: 1px solid {COLORS["border"]};
    border-bottom: none;
    padding: 6px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 80px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS["bg_medium"]};
    color: {COLORS["fg"]};
    border-bottom: 2px solid {COLORS["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["fg"]};
}}

QPlainTextEdit {{
    background-color: {COLORS["bg_medium"]};
    color: {COLORS["fg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 10pt;
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["bg_dark"]};
}}

QLineEdit {{
    background-color: {COLORS["bg_medium"]};
    color: {COLORS["fg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["bg_dark"]};
}}

QLineEdit:focus {{
    border: 1px solid {COLORS["accent"]};
}}

QLineEdit:disabled {{
    color: {COLORS["fg_dim"]};
    background-color: {COLORS["bg_dark"]};
}}

QPushButton {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["fg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 5px 14px;
    min-width: 60px;
}}

QPushButton:hover {{
    background-color: {COLORS["accent"]};
    color: {COLORS["bg_dark"]};
    border-color: {COLORS["accent"]};
}}

QPushButton:pressed {{
    background-color: #6a9de0;
    color: {COLORS["bg_dark"]};
}}

QPushButton:disabled {{
    background-color: {COLORS["bg_dark"]};
    color: {COLORS["fg_dim"]};
    border-color: {COLORS["border"]};
}}

QComboBox {{
    background-color: {COLORS["bg_medium"]};
    color: {COLORS["fg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 120px;
}}

QComboBox:focus {{
    border: 1px solid {COLORS["accent"]};
}}

QComboBox:disabled {{
    color: {COLORS["fg_dim"]};
    background-color: {COLORS["bg_dark"]};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: 1px solid {COLORS["border"]};
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}

QComboBox::down-arrow {{
    image: url({_DOWN_ARROW_PATH});
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_medium"]};
    color: {COLORS["fg"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["accent"]};
    selection-color: {COLORS["bg_dark"]};
    outline: none;
}}

QLabel {{
    color: {COLORS["fg"]};
    background-color: transparent;
}}

QSplitter::handle {{
    background-color: {COLORS["border"]};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS["accent"]};
}}

QScrollBar:vertical {{
    background-color: {COLORS["bg_dark"]};
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS["border"]};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS["fg_dim"]};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {COLORS["bg_dark"]};
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS["border"]};
    min-width: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS["fg_dim"]};
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
}}

QToolTip {{
    background-color: {COLORS["bg_light"]};
    color: {COLORS["fg"]};
    border: 1px solid {COLORS["accent"]};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""


def apply_mpl_theme(fig, axes):
    bg_dark = COLORS["bg_dark"]
    bg_medium = COLORS["bg_medium"]
    fg = COLORS["fg"]
    fg_dim = COLORS["fg_dim"]
    border = COLORS["border"]

    fig.patch.set_facecolor(bg_dark)

    for ax in axes:
        ax.set_facecolor(bg_medium)

        ax.tick_params(colors=fg_dim, which="both")
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        ax.title.set_color(fg)

        for spine in ax.spines.values():
            spine.set_edgecolor(border)

        ax.grid(True, color=border, linestyle="--", linewidth=0.5, alpha=0.7)
        ax.set_axisbelow(True)
