"""One-off generator for the GitHub social preview (1280x640 PNG).

Renders the vector brand mark + wordmark via PySide6/QtSvg so the output
is crisp. Not part of the app; safe to delete after the PNG is produced.
"""
import sys

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

W, H = 1280, 640

# Logo: 300x300 rounded square at (120,170); play triangle scaled x9.375.
SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"
     viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="#0f172a"/>
  <rect x="120" y="170" width="300" height="300" rx="75" fill="#3b82f6"/>
  <polygon points="241.9,254.4 241.9,385.6 345,320" fill="#ffffff"/>
  <text x="500" y="300" fill="#f8fafc"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="92" font-weight="700">YT-DLP Studio</text>
  <text x="503" y="360" fill="#94a3b8"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="38">A user-friendly GUI for yt-dlp</text>
  <text x="503" y="430" fill="#3b82f6"
        font-family="Segoe UI, Arial, sans-serif"
        font-size="30" font-weight="600">part of NXTools</text>
</svg>"""

app = QGuiApplication(sys.argv)
renderer = QSvgRenderer(QByteArray(SVG.encode("utf-8")))
image = QImage(W, H, QImage.Format_RGB32)
image.fill(0xFF0F172A)
painter = QPainter(image)
renderer.render(painter)
painter.end()

out = "social-preview.png"
if not image.save(out, "PNG"):
    raise SystemExit("failed to write " + out)
print("wrote", out, image.width(), "x", image.height())
