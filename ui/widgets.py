# -*- coding: utf-8 -*-
"""自定义 Qt 控件"""

import os
from PySide6.QtWidgets import QLineEdit, QComboBox, QProgressBar, QListView, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath

from constants import SHIMMER_INTERVAL_MS, SHIMMER_STEP, SHIMMER_BAND_WIDTH


class DragLineEdit(QLineEdit):
    """支持拖拽文件/文件夹路径到输入框。"""
    _accent_color = '#60A5FA'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                f"background: palette(base); border: 2px solid {DragLineEdit._accent_color}; "
                "border-radius: 6px; padding: 0px 9px;"
            )
        else:
            super().dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.setText(os.path.normpath(path))
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class RoundComboBox(QComboBox):
    """支持圆角透明弹窗背景的下拉框。"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_chrome_applied = False

    def showPopup(self):
        if not self._popup_chrome_applied:
            view = self.view()
            if view:
                container = view.parentWidget()
                if container:
                    container.setObjectName("comboPopupContainer")
                    container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                    container.setWindowFlags(
                        Qt.WindowType.Popup
                        | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint
                    )
                    container.setStyleSheet(
                        "#comboPopupContainer { background: transparent; border: none; }"
                    )
            self._popup_chrome_applied = True
        super().showPopup()


class AnimatedProgressBar(QProgressBar):
    """带流光效果的进度条。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._shimmer_x = -1.0
        self._timer = QTimer(self)
        self._timer.setInterval(SHIMMER_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._shimmer_x += SHIMMER_STEP
        if self._shimmer_x > 2.0:
            self._shimmer_x = -0.5
        self.update()

    def start_animation(self):
        self._shimmer_x = -0.5
        self._timer.start()

    def stop_animation(self):
        self._timer.stop()
        self._shimmer_x = -1.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.maximum() == self.minimum() or self._shimmer_x < -0.5:
            return
        val = (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum())
        if val <= 0:
            return
        fill_w = int(self.width() * val)
        if fill_w <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(self.rect()), 8, 8)
        painter.setClipPath(clip_path)
        painter.setClipRect(0, 0, fill_w, self.height(), Qt.ClipOperation.IntersectClip)

        band_w = SHIMMER_BAND_WIDTH
        sx = fill_w * self._shimmer_x - band_w / 2
        grad = QLinearGradient(sx, 0, sx + band_w, 0)
        grad.setColorAt(0, QColor(255, 255, 255, 0))
        grad.setColorAt(0.5, QColor(255, 255, 255, 40))
        grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.fillRect(QRectF(sx, 0, band_w, self.height()), grad)
        painter.end()
