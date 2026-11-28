"""Draw the small PNG icons the Qt style sheet uses (src/resources/icons/theme/).

Qt style sheets cannot draw arrows or check marks themselves, so the theme
points ``image: url(...)`` at these files. Run this script again after a
change to the colors in ``src/ui/theme.py``:

    QT_QPA_PLATFORM=offscreen python scripts/generate_theme_icons.py

Every icon is written at 1x and 2x (``name@2x.png``) for high-DPI screens.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen  # noqa: E402

from src.ui.theme import ICON_DIR, ModernTheme  # noqa: E402


def _draw(name: str, size: int, color: str, shape: str) -> None:
    for scale, suffix in ((1, ""), (2, "@2x")):
        px = size * scale
        image = QImage(px, px, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidthF(1.6 * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        s = float(px)
        if shape == "down":
            path.moveTo(QPointF(s * 0.2, s * 0.35))
            path.lineTo(QPointF(s * 0.5, s * 0.65))
            path.lineTo(QPointF(s * 0.8, s * 0.35))
        elif shape == "up":
            path.moveTo(QPointF(s * 0.2, s * 0.65))
            path.lineTo(QPointF(s * 0.5, s * 0.35))
            path.lineTo(QPointF(s * 0.8, s * 0.65))
        elif shape == "check":
            pen.setWidthF(1.8 * scale)
            painter.setPen(pen)
            path.moveTo(QPointF(s * 0.2, s * 0.52))
            path.lineTo(QPointF(s * 0.42, s * 0.74))
            path.lineTo(QPointF(s * 0.8, s * 0.3))
        painter.drawPath(path)
        painter.end()
        image.save(str(ICON_DIR / f"{name}{suffix}.png"))


def main() -> None:
    QGuiApplication(sys.argv)
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for theme, colors in ModernTheme.COLORS.items():
        for state, token in (("", "text_secondary"), ("-disabled", "text_disabled")):
            _draw(f"chevron-down-{theme}{state}", 10, colors[token], "down")
            _draw(f"chevron-up-{theme}{state}", 10, colors[token], "up")
        _draw(f"check-{theme}", 14, colors["text_on_accent"], "check")
    print(f"Icons written to {ICON_DIR}")


if __name__ == "__main__":
    main()
