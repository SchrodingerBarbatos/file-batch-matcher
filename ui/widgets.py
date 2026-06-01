# -*- coding: utf-8 -*-
"""自定义 Qt 控件"""

import os
from PySide6.QtWidgets import (
    QLineEdit, QComboBox, QProgressBar, QListView, QSizePolicy,
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QAbstractItemView, QStyledItemDelegate, QStyle,
)
from PySide6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve, QSize, QModelIndex
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QFont

from constants import SHIMMER_INTERVAL_MS, SHIMMER_STEP, SHIMMER_BAND_WIDTH, RADIUS_SMALL, RADIUS_INPUT, RADIUS_PRIMARY, RADIUS_TAB


class DragLineEdit(QLineEdit):
    """支持拖拽文件/文件夹路径到输入框。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._accent_color = '#60A5FA'
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                f"background: palette(base); border: 2px solid {DragLineEdit._accent_color}; "
                f"border-radius: {RADIUS_INPUT}px; padding: 0px 9px;"
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
                    container.setWindowFlags(
                        Qt.WindowType.Popup
                        | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint
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
        clip_path.addRoundedRect(QRectF(self.rect()), RADIUS_SMALL, RADIUS_SMALL)
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


class StepRow(QWidget):
    """步骤式配置行：编号圆圈 + 标签 + 输入控件 + 浏览按钮，状态提示在下方。"""

    def __init__(self, number, label_text, input_widget, browse_button=None,
                 status_text="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(2)

        # 主行：编号 + 标签 + 输入 + 浏览
        row = QHBoxLayout()
        row.setSpacing(10)

        self.number_label = QLabel(str(number))
        self.number_label.setObjectName("stepNumber")
        self.number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.number_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.field_label = QLabel(label_text)
        self.field_label.setObjectName("fieldLabel")
        row.addWidget(self.field_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.input_widget = input_widget
        input_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(input_widget, 1, Qt.AlignmentFlag.AlignVCenter)

        if browse_button:
            browse_button.setFixedWidth(80)
            row.addWidget(browse_button, 0, Qt.AlignmentFlag.AlignVCenter)

        outer.addLayout(row)

        # 状态提示（下一行，缩进对齐输入框）
        self.status_label = QLabel(status_text)
        self.status_label.setObjectName("statusHint")
        self.status_label.setWordWrap(True)
        hint_row = QHBoxLayout()
        hint_row.setContentsMargins(34, 0, 0, 0)
        hint_row.addWidget(self.status_label)
        outer.addLayout(hint_row)

    def set_status(self, text, status_type="hint"):
        """设置状态提示。status_type: 'ok', 'warn', 'error', 'hint'"""
        self.status_label.setText(text)
        self.status_label.setObjectName(f"status{status_type.capitalize()}")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)


class CollapsibleSection(QWidget):
    """可折叠/展开的区域容器。"""

    def __init__(self, title="高级选项", parent=None):
        super().__init__(parent)
        self._expanded = False
        self._animation = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 可点击的标题栏
        self._header_btn = QPushButton(f"  {title}")
        self._header_btn.setObjectName("collapseHeader")
        self._header_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header_btn.clicked.connect(self.toggle)
        main_layout.addWidget(self._header_btn)

        # 内容容器
        self._content = QWidget()
        self._content.setMaximumHeight(0)
        self._content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.content_layout = QVBoxLayout(self._content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(10)
        main_layout.addWidget(self._content)

        self._update_arrow()

    def _update_arrow(self):
        arrow = "▼" if self._expanded else "▶"
        title = self._header_btn.text().lstrip("▼▶ ").strip()
        self._header_btn.setText(f" {arrow} {title}")

    def toggle(self):
        self._expanded = not self._expanded
        self._update_arrow()

        target = self._content.sizeHint().height() + 16 if self._expanded else 0
        if self._animation and self._animation.state() == QPropertyAnimation.State.Running:
            self._animation.stop()

        self._animation = QPropertyAnimation(self._content, b"maximumHeight")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.setStartValue(self._content.maximumHeight())
        self._animation.setEndValue(target)
        self._animation.start()

    def expand(self):
        if not self._expanded:
            self.toggle()

    def collapse(self):
        if self._expanded:
            self.toggle()


class AdvancedOptionsCard(QFrame):
    """高级选项卡片：默认展开，静态标题 + 分隔线 + 三列内容区。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFrame")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(14)

        # 标题区域
        title = QLabel("高级选项")
        title.setObjectName("cardTitle")
        main_layout.addWidget(title)

        subtitle = QLabel("文件过滤 · 文件处理 · 图片处理")
        subtitle.setObjectName("cardSubtitle")
        main_layout.addWidget(subtitle)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("advCardSeparator")
        main_layout.addWidget(sep)

        # 三列内容容器（由外部填充）
        self.three_col_layout = QHBoxLayout()
        self.three_col_layout.setSpacing(0)
        self.three_col_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(self.three_col_layout)


class StatCard(QFrame):
    """统计数字卡片：左侧彩色竖条 + 数字 + 说明文字。"""

    def __init__(self, label, color, icon_type="circle", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 14, 10)
        layout.setSpacing(12)

        # 左侧彩色竖条
        bar = QFrame()
        bar.setFixedWidth(4)
        bar.setStyleSheet(
            f"background: {color}; border: none; border-radius: 2px;"
        )
        layout.addWidget(bar)

        # 右侧内容：数字 + 说明
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {color}; background: transparent;"
        )
        text_col.addWidget(self.count_label)

        self.desc_label = QLabel(label)
        self.desc_label.setObjectName("hintLabel")
        text_col.addWidget(self.desc_label)

        layout.addLayout(text_col)

    def set_count(self, value):
        self.count_label.setText(str(value))


class CurrentFileBar(QFrame):
    """当前文件 + 底部汇总信息合一栏。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("currentFileBar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 14px; background: transparent;")
        layout.addWidget(icon_label)

        self.file_label = QLabel("当前文件：—")
        self.file_label.setObjectName("hintLabel")
        self.file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.file_label, 1)

        self.summary_label = QLabel("编号总数：0  已匹配：0  文件总数：0  耗时：00:00")
        self.summary_label.setObjectName("hintLabel")
        layout.addWidget(self.summary_label, 0)

    def set_file(self, name):
        self.file_label.setText(f"当前文件：{name}")

    def set_summary(self, text):
        self.summary_label.setText(text)

    def reset(self):
        self.file_label.setText("当前文件：—")
        self.summary_label.setText("编号总数：0  已匹配：0  文件总数：0  耗时：00:00")


class TabButton(QPushButton):
    """自定义 Tab 按钮，pill 风格，支持选中/未选中状态。"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("TabButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)


class OptionCard(QFrame):
    """高级选项内的小卡片容器：白色背景、圆角、阴影、标题。"""

    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("OptionCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        lbl = QLabel(title)
        lbl.setObjectName("optionCardTitle")
        layout.addWidget(lbl)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("optionCardSubtitle")
            layout.addWidget(sub)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.content_layout)


class LogListWidget(QListWidget):
    """日志列表控件：支持彩色图标、时间戳、空状态提示。"""

    EMPTY_TITLE = "暂无日志"
    EMPTY_DESC = "开始匹配后将显示文件扫描、匹配结果和错误信息"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogListWidget")
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setUniformItemSizes(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._line_height = 30
        self.setItemDelegate(_LogItemDelegate(self))

    def add_log_entry(self, icon_char, icon_color, timestamp, text, text_color=None):
        """添加一条日志条目。"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.DisplayRole, text)
        item.setData(Qt.ItemDataRole.UserRole, icon_char)
        item.setData(Qt.ItemDataRole.UserRole + 1, icon_color)
        item.setData(Qt.ItemDataRole.UserRole + 2, timestamp)
        if text_color:
            item.setData(Qt.ItemDataRole.UserRole + 3, text_color)
        item.setSizeHint(QSize(0, self._line_height))
        self.addItem(item)
        self.scrollToBottom()

    def paintEvent(self, event):
        if self.count() == 0:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            is_dark = False
            if app:
                is_dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128

            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            title_font = QFont("Microsoft YaHei", 14)
            title_font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(title_font)
            painter.setPen(QColor("#9CA3AF" if not is_dark else "#6B7280"))
            fm = painter.fontMetrics()
            title_y = int(self.viewport().height() * 0.35) - fm.height()
            painter.drawText(
                self.viewport().rect(),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self.EMPTY_TITLE,
                QRectF(0, title_y, self.viewport().width(), fm.height()).toRect()
            )
            desc_font = QFont("Microsoft YaHei", 12)
            painter.setFont(desc_font)
            painter.setPen(QColor("#9CA3AF" if not is_dark else "#6B7280"))
            fm2 = painter.fontMetrics()
            desc_y = title_y + fm.height() + 8
            painter.drawText(
                QRectF(20, desc_y, self.viewport().width() - 40, fm2.height() * 2),
                Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                self.EMPTY_DESC,
            )
            painter.end()
        else:
            super().paintEvent(event)


class _LogItemDelegate(QStyledItemDelegate):
    """日志条目自定义渲染：彩色圆点 + 时间戳 + 内容。"""

    def paint(self, painter, option, index):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        icon_char = index.data(Qt.ItemDataRole.UserRole) or "●"
        icon_color = index.data(Qt.ItemDataRole.UserRole + 1) or "#9CA3AF"
        timestamp = index.data(Qt.ItemDataRole.UserRole + 2) or ""
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        text_color = index.data(Qt.ItemDataRole.UserRole + 3)

        rect = option.rect
        y_center = rect.y() + rect.height() // 2

        # 背景（hover/选中）
        if option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor(0, 0, 0, 8))

        # 彩色圆点
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(icon_color))
        dot_r = 4
        dot_x = rect.x() + 14
        painter.drawEllipse(QRectF(dot_x - dot_r, y_center - dot_r, dot_r * 2, dot_r * 2))

        # 时间戳
        ts_font = QFont("Consolas", 11)
        painter.setFont(ts_font)
        painter.setPen(QColor("#9CA3AF"))
        ts_x = dot_x + dot_r + 10
        ts_rect = QRectF(ts_x, rect.y(), 70, rect.height())
        painter.drawText(ts_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, timestamp)

        # 内容
        content_font = QFont("Microsoft YaHei", 12)
        painter.setFont(content_font)
        if text_color:
            painter.setPen(QColor(text_color))
        else:
            painter.setPen(QColor("#111827"))
        content_x = ts_x + 74
        content_rect = QRectF(content_x, rect.y(), rect.width() - content_x - 10, rect.height())
        painter.drawText(content_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

    def sizeHint(self, option, index):
        return QSize(0, 30)
