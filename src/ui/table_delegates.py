"""
Item delegates for the Queue and History tables.

``StatusDelegate`` draws the status cell: a slim progress bar with the
percent for a running download, or a status mark and text in the status
color. The colors come from the active theme at paint time, so a theme
switch needs no refresh. A status always has a mark and text, never color
alone.

``LinkAwareDelegate`` draws a cell that holds a link instead of a title
left to right, with the ellipsis in the middle, so the start and the end of
the link stay readable in both layout directions.
"""

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from .display_format import percent_text, status_color, theme_colors

# Item data roles
STATUS_KIND_ROLE = Qt.UserRole + 1  # "running", "done", "failed", "waiting", "cancelled"
PROGRESS_ROLE = Qt.UserRole + 2  # float percent for a running download, else None
IS_LINK_ROLE = Qt.UserRole + 3  # True when the cell shows a link, not a title

# Mark drawn before the status text
STATUS_MARKS = {
    "running": "▸",  # small right-pointing triangle
    "done": "✓",  # check mark
    "failed": "✕",  # multiplication x
    "waiting": "○",  # white circle
    "cancelled": "⊘",  # circled division slash
}

_BAR_HEIGHT = 8
_BAR_WIDTH = 120


class StatusDelegate(QStyledItemDelegate):
    """Status mark and text, or a progress bar for a running download."""

    def sizeHint(self, option: QStyleOptionViewItem, index):  # noqa: N802 - Qt override
        """Room for the mark, the text and the side padding (or the bar and percent)."""
        hint = super().sizeHint(option, index)
        metrics = option.fontMetrics
        text = index.data(Qt.DisplayRole) or ""
        mark = STATUS_MARKS.get(index.data(STATUS_KIND_ROLE) or "waiting", "")
        width = metrics.horizontalAdvance(f"{mark} {text}") + 16 + 8
        if index.data(PROGRESS_ROLE) is not None:
            width = max(width, _BAR_WIDTH + 6 + metrics.horizontalAdvance("100%") + 24)
        hint.setWidth(max(hint.width(), width))
        return hint

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""
        style = opt.widget.style() if opt.widget else None
        if style is not None:
            # Background, selection and focus, without the text
            style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        kind = index.data(STATUS_KIND_ROLE) or "waiting"
        progress = index.data(PROGRESS_ROLE)
        rect = option.rect.adjusted(8, 0, -8, 0)
        rtl = option.direction == Qt.RightToLeft
        selected = bool(option.state & QStyle.State_Selected)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        # Base text direction of the cell, so the mark stays at the start in Hebrew
        painter.setLayoutDirection(option.direction)
        if progress is not None:
            self._paint_progress(painter, rect, float(progress), rtl, selected, option)
        else:
            mark = STATUS_MARKS.get(kind, "")
            label = f"{mark} {text}" if mark else text
            color = option.palette.color(QPalette.HighlightedText) if selected else QColor(status_color(kind))
            painter.setPen(color)
            align = QStyle.visualAlignment(option.direction, Qt.AlignLeft | Qt.AlignVCenter)
            elided = option.fontMetrics.elidedText(label, Qt.ElideRight, rect.width())
            painter.drawText(rect, int(align), elided)
        painter.restore()

    @staticmethod
    def _paint_progress(painter: QPainter, rect: QRect, percent: float, rtl: bool, selected: bool, option) -> None:
        colors = theme_colors()
        text = percent_text(percent)
        text_width = option.fontMetrics.horizontalAdvance("100%") + 8
        bar_width = max(24, min(_BAR_WIDTH, rect.width() - text_width))
        top = rect.center().y() - _BAR_HEIGHT // 2 + 1
        if rtl:
            bar = QRectF(rect.right() - bar_width, top, bar_width, _BAR_HEIGHT)
            text_rect = QRect(rect.left(), rect.top(), rect.width() - bar_width - 6, rect.height())
            text_align = Qt.AlignRight | Qt.AlignVCenter
        else:
            bar = QRectF(rect.left(), top, bar_width, _BAR_HEIGHT)
            text_rect = QRect(rect.left() + bar_width + 6, rect.top(), rect.width() - bar_width - 6, rect.height())
            text_align = Qt.AlignLeft | Qt.AlignVCenter

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(colors["bg_tertiary"] if not selected else colors["bg_primary"]))
        painter.drawRoundedRect(bar, 4, 4)
        fill = bar_width * max(0.0, min(percent, 100.0)) / 100.0
        if fill > 0:
            chunk = (
                QRectF(bar.right() - fill, bar.top(), fill, bar.height())
                if rtl
                else QRectF(bar.left(), bar.top(), fill, bar.height())
            )
            painter.setBrush(QColor(status_color("running") if not selected else colors["text_primary"]))
            painter.drawRoundedRect(chunk, 4, 4)

        painter.setPen(option.palette.color(QPalette.HighlightedText) if selected else QColor(colors["text_primary"]))
        painter.drawText(text_rect, int(text_align), text)


class LinkAwareDelegate(QStyledItemDelegate):
    """Draws link cells left to right with the ellipsis in the middle."""

    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:  # noqa: N802 - Qt override
        super().initStyleOption(option, index)
        if index.data(IS_LINK_ROLE):
            option.textElideMode = Qt.ElideMiddle
            option.direction = Qt.LeftToRight
            option.displayAlignment = Qt.AlignLeft | Qt.AlignVCenter
