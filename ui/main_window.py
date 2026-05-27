# -*- coding: utf-8 -*-
"""主窗口布局 & 信号连接"""

import os
import sys
import re
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QFileDialog, QMessageBox,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QGridLayout, QListView,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont, QIcon

from constants import DEBOUNCE_MS, LOG_MAX_BLOCK_COUNT, DEFAULT_IMG_EXTENSIONS
from services.icons import _write_temp_svg, _TEMP_ICON_PATHS
from core.engine import FileMatcherEngine
from ui.widgets import DragLineEdit, RoundComboBox, AnimatedProgressBar
from ui.workers import WorkerThread
from ui.styles import get_theme_colors, build_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件批量匹配复制工具")
        self.resize(1000, 750)
        self._colors = get_theme_colors()

        self.stop_event = threading.Event()
        self.engine = FileMatcherEngine(
            log_callback=self._thread_safe_log,
            stop_event=self.stop_event,
        )
        self.worker = None
        self.unmatched_ids = []
        self.column_display_to_name = {}

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._do_load_columns)

        self._setup_ui()

    # ---- UI 辅助方法 ----

    def _add_shadow(self, widget, blur=14, y=3):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y)
        effect.setColor(self._colors['shadow'])
        widget.setGraphicsEffect(effect)

    def _section_title(self, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _hint_label(self, text):
        label = QLabel(text)
        label.setObjectName("hintLabel")
        label.setWordWrap(True)
        return label

    def _field_label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _setup_combo_view(self, combo):
        view = QListView()
        view.setObjectName("roundComboView")
        combo.setView(view)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(12)
        return combo

    # ---- 主界面布局 ----

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        ui_gap = 16
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(ui_gap, ui_gap, ui_gap, ui_gap)
        main_layout.setSpacing(ui_gap)

        # ---- 左侧滚动区域 ----
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(350)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(ui_gap)

        # ---- 右侧固定区域 ----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(ui_gap)

        # 将左右区域添加到主布局
        main_layout.addWidget(left_scroll, 40)
        main_layout.addWidget(right_widget, 60)

        # 设置左侧滚动区域的内容
        left_scroll.setWidget(left_widget)

        # ========== 左侧：路径与文件设置 ==========
        path_group = QFrame()
        path_group.setObjectName("CardFrame")
        path_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        path_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._add_shadow(path_group)
        path_layout = QGridLayout(path_group)
        path_layout.setHorizontalSpacing(10)
        path_layout.setVerticalSpacing(10)
        path_layout.setContentsMargins(14, 12, 14, 12)
        path_layout.setColumnMinimumWidth(0, 76)
        path_layout.setColumnMinimumWidth(1, 240)
        path_layout.setColumnMinimumWidth(2, 80)
        path_layout.setColumnStretch(1, 1)
        path_layout.addWidget(
            self._section_title("路径与文件设置"),
            0, 0, 1, 3, Qt.AlignmentFlag.AlignTop,
        )

        # Excel 文件
        self.le_excel = DragLineEdit()
        self.le_excel.setMinimumWidth(240)
        self.le_excel.setPlaceholderText(r"D:\data\商品清单.xlsx")
        self.le_excel.setToolTip("选择包含编号列表的 Excel 文件（.xlsx 或 .xls）")
        self.le_excel.textChanged.connect(self._debounce_load_columns)
        btn_excel = QPushButton("浏览...")
        btn_excel.setFixedWidth(80)
        btn_excel.clicked.connect(self._browse_excel)
        path_layout.addWidget(self._field_label("Excel 文件"), 1, 0, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(self.le_excel, 1, 1, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(btn_excel, 1, 2, Qt.AlignmentFlag.AlignVCenter)

        # 编号所在列
        self.cb_col = RoundComboBox()
        self._setup_combo_view(self.cb_col)
        self.cb_col.setToolTip("选择包含编号的列。支持列字母（如 A）或列名。")
        self.lbl_col_hint = QLabel("选择 Excel 后自动加载列名")
        self.lbl_col_hint.setStyleSheet(f"color: {self._colors['muted']}; font-style: italic;")
        path_layout.addWidget(self._field_label("编号所在列"), 2, 0, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(self.cb_col, 2, 1, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(self.lbl_col_hint, 2, 2, Qt.AlignmentFlag.AlignVCenter)

        # 源文件夹
        self.le_source = DragLineEdit()
        self.le_source.setMinimumWidth(240)
        self.le_source.setPlaceholderText(r"D:\images\source")
        self.le_source.setToolTip("原始文件所在的文件夹")
        btn_source = QPushButton("浏览...")
        btn_source.setFixedWidth(80)
        btn_source.clicked.connect(lambda: self._browse_dir(self.le_source))
        path_layout.addWidget(self._field_label("源文件夹"), 3, 0, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(self.le_source, 3, 1, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(btn_source, 3, 2, Qt.AlignmentFlag.AlignVCenter)

        # 目标文件夹
        self.le_output = DragLineEdit()
        self.le_output.setMinimumWidth(240)
        self.le_output.setPlaceholderText(r"D:\images\output")
        self.le_output.setToolTip("匹配到的文件将复制/移动到此目录")
        btn_output = QPushButton("浏览...")
        btn_output.setFixedWidth(80)
        btn_output.clicked.connect(lambda: self._browse_dir(self.le_output))
        path_layout.addWidget(self._field_label("目标文件夹"), 4, 0, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(self.le_output, 4, 1, Qt.AlignmentFlag.AlignVCenter)
        path_layout.addWidget(btn_output, 4, 2, Qt.AlignmentFlag.AlignVCenter)

        path_hint = self._hint_label("Excel 中编号按字符串读取，自动去重；支持 .xlsx 和 .xls 格式")
        path_hint.setContentsMargins(0, 2, 0, 0)
        path_layout.addWidget(path_hint, 5, 1, 1, 2, Qt.AlignmentFlag.AlignTop)
        left_layout.addWidget(path_group)

        # ========== 左侧：匹配选项 ==========
        opt_group = QFrame()
        opt_group.setObjectName("CardFrame")
        opt_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        opt_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._add_shadow(opt_group)
        opt_layout = QGridLayout(opt_group)
        opt_layout.setHorizontalSpacing(10)
        opt_layout.setVerticalSpacing(12)
        opt_layout.setContentsMargins(14, 14, 14, 14)
        opt_layout.setColumnMinimumWidth(0, 100)
        opt_layout.setColumnStretch(1, 1)
        opt_layout.addWidget(
            self._section_title("匹配选项"),
            0, 0, 1, 2, Qt.AlignmentFlag.AlignTop,
        )

        # 扩展名
        opt_layout.addWidget(self._field_label("允许的扩展名"), 1, 0)
        self.le_ext = QLineEdit()
        self.le_ext.setText(" ".join(sorted(DEFAULT_IMG_EXTENSIONS)))
        self.le_ext.setToolTip("空格分隔，如 .jpg .png")
        opt_layout.addWidget(self.le_ext, 1, 1)

        # 文件处理方式
        opt_layout.addWidget(self._field_label("文件处理方式"), 2, 0)
        self.cb_move = RoundComboBox()
        self._setup_combo_view(self.cb_move)
        self.cb_move.addItems(["复制（保留源文件）", "移动（剪切源文件）"])
        self.cb_move.setCurrentIndex(0)
        self.cb_move.setToolTip("复制更安全，移动更省空间")
        opt_layout.addWidget(self.cb_move, 2, 1)

        # 复选框选项
        self.chk_no_ext = QCheckBox("不限制扩展名")
        self.chk_no_ext.setToolTip("匹配所有文件，忽略扩展名过滤")
        self.chk_no_ext.toggled.connect(self._toggle_ext_entry)
        opt_layout.addWidget(self.chk_no_ext, 3, 0, 1, 2)

        self.chk_recursive = QCheckBox("递归搜索子文件夹")
        opt_layout.addWidget(self.chk_recursive, 4, 0, 1, 2)

        self.chk_overwrite = QCheckBox("目标存在时覆盖")
        opt_layout.addWidget(self.chk_overwrite, 5, 0, 1, 2)

        left_layout.addWidget(opt_group)

        # ========== 左侧：图片处理选项 ==========
        img_group = QFrame()
        img_group.setObjectName("CardFrame")
        img_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._add_shadow(img_group, blur=12, y=2)
        img_layout = QGridLayout(img_group)
        img_layout.setHorizontalSpacing(10)
        img_layout.setVerticalSpacing(10)
        img_layout.setContentsMargins(14, 12, 14, 12)
        img_layout.setColumnMinimumWidth(0, 100)
        img_layout.setColumnStretch(1, 1)
        img_layout.addWidget(
            self._section_title("图片处理"),
            0, 0, 1, 6, Qt.AlignmentFlag.AlignTop,
        )

        self.chk_resize = QCheckBox("启用图片尺寸/大小处理")
        self.chk_resize.toggled.connect(self._toggle_resize_fields)
        img_layout.addWidget(self.chk_resize, 1, 0, 1, 6)

        img_layout.addWidget(self._field_label("宽"), 2, 0, Qt.AlignmentFlag.AlignVCenter)
        self.le_width = QLineEdit("800")
        self.le_width.setMaximumWidth(80)
        img_layout.addWidget(self.le_width, 2, 1, Qt.AlignmentFlag.AlignVCenter)

        img_layout.addWidget(self._field_label("高"), 2, 2, Qt.AlignmentFlag.AlignVCenter)
        self.le_height = QLineEdit("800")
        self.le_height.setMaximumWidth(80)
        img_layout.addWidget(self.le_height, 2, 3, Qt.AlignmentFlag.AlignVCenter)

        img_layout.addWidget(self._field_label("最大大小(bytes)"), 2, 4, Qt.AlignmentFlag.AlignVCenter)
        self.le_max_size = QLineEdit("5000000")
        self.le_max_size.setMaximumWidth(120)
        img_layout.addWidget(self.le_max_size, 2, 5, Qt.AlignmentFlag.AlignVCenter)

        self.chk_convert = QCheckBox("启用格式转换")
        self.chk_convert.toggled.connect(self._toggle_convert_fields)
        img_layout.addWidget(self.chk_convert, 3, 0, 1, 2)

        img_layout.addWidget(self._field_label("目标格式"), 3, 2, Qt.AlignmentFlag.AlignVCenter)
        self.cb_format = RoundComboBox()
        self._setup_combo_view(self.cb_format)
        self.cb_format.addItems(["JPEG", "PNG"])
        self.cb_format.setMaximumWidth(100)
        img_layout.addWidget(self.cb_format, 3, 3, Qt.AlignmentFlag.AlignVCenter)

        # 初始禁用图片处理字段
        self._toggle_resize_fields(False)
        self._toggle_convert_fields(False)

        left_layout.addWidget(img_group)

        # 左侧底部弹性空间
        left_layout.addStretch()

        # ========== 右侧：操作按钮 + 进度 + 统计 ==========
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self.btn_start = QPushButton("开始匹配并复制")
        self.btn_start.setObjectName("startButton")
        self.btn_start.clicked.connect(self.start_process)
        self.btn_stop = QPushButton("终止")
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_process)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        right_layout.addLayout(btn_row)

        # 进度条
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        right_layout.addWidget(self.progress_bar)

        # 统计信息
        stats_layout = QHBoxLayout()
        self.lbl_progress_detail = QLabel("准备就绪")
        self.lbl_progress_detail.setStyleSheet(f"color: {self._colors['muted']};")
        self.lbl_success = QLabel("成功: 0")
        self.lbl_success.setStyleSheet(f"color: {self._colors['muted']};")
        self.lbl_failed = QLabel("失败: 0")
        self.lbl_failed.setStyleSheet(f"color: {self._colors['muted']};")
        self.lbl_skipped = QLabel("跳过: 0")
        self.lbl_skipped.setStyleSheet(f"color: {self._colors['muted']};")
        stats_layout.addWidget(self.lbl_progress_detail, 3)
        stats_layout.addWidget(self.lbl_success)
        stats_layout.addWidget(self.lbl_failed)
        stats_layout.addWidget(self.lbl_skipped)
        right_layout.addLayout(stats_layout)

        # 底部操作按钮
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        self.btn_save_unmatched = QPushButton("保存未匹配编号")
        self.btn_save_unmatched.setObjectName("logToolButton")
        self.btn_save_unmatched.clicked.connect(self.save_unmatched)
        self.btn_clear_log = QPushButton("清空日志")
        self.btn_clear_log.setObjectName("logToolButton")
        self.btn_clear_log.clicked.connect(self._clear_log)
        bottom_row.addWidget(self.btn_save_unmatched)
        bottom_row.addWidget(self.btn_clear_log)
        bottom_row.addStretch()
        right_layout.addLayout(bottom_row)

        # ========== 右侧：日志 ==========
        log_group = QFrame()
        log_group.setObjectName("CardFrame")
        log_group.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._add_shadow(log_group)
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(12)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.addWidget(self._section_title("运行日志"))
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setMinimumHeight(200)
        self.text_log.document().setMaximumBlockCount(LOG_MAX_BLOCK_COUNT)
        log_layout.addWidget(self.text_log, 1)

        right_layout.addWidget(log_group, 1)

        self._apply_app_style()

        # 设置按钮图标
        if hasattr(self, '_play_ico_path') and self._play_ico_path:
            self.btn_start.setIcon(QIcon(self._play_ico_path))
            self.btn_start.setIconSize(QSize(20, 20))
        if hasattr(self, '_stop_ico_dis_path') and self._stop_ico_dis_path:
            self.btn_stop.setIcon(QIcon(self._stop_ico_dis_path))
            self.btn_stop.setIconSize(QSize(18, 18))

    # ---- 样式 ----

    def _apply_app_style(self):
        c = self._colors

        checkbox_checked_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">'
            f'<rect x="2" y="2" width="20" height="20" rx="6" ry="6" fill="{c["green"]}" />'
            f'<path d="M8 12 L11 15 L16 9" fill="none" stroke="#FFFFFF"'
            f' stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        checkbox_unchecked_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">'
            f'<rect x="2" y="2" width="20" height="20" rx="6" ry="6" '
            f'fill="{c["input"]}" stroke="{c["input_border"]}" stroke-width="2" />'
            f'</svg>'
        )
        cb_checked_ico = _write_temp_svg(checkbox_checked_svg, "cb_checked_ico_")
        cb_unchecked_ico = _write_temp_svg(checkbox_unchecked_svg, "cb_unchecked_ico_")
        checkbox_checked_css = f"image: url({cb_checked_ico});" if cb_checked_ico else f"background: {c['green']};"
        checkbox_unchecked_css = f"image: url({cb_unchecked_ico});" if cb_unchecked_ico else f"background: {c['input']};"

        arrow_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 8" width="12" height="8">'
            f'<path d="M1.5 1.5L6 6L10.5 1.5" fill="none" stroke="{c["muted"]}"'
            f' stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        arrow_ico = _write_temp_svg(arrow_svg, "cb_arrow_")

        play_ico = _write_temp_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">'
            f'<polygon points="8,5 19,12 8,19" fill="white"/></svg>',
            "btn_play_"
        )
        play_ico_dis = _write_temp_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">'
            f'<polygon points="8,5 19,12 8,19" fill="{c["muted"]}"/></svg>',
            "btn_play_dis_"
        )
        stop_ico = _write_temp_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18">'
            '<rect x="6" y="6" width="12" height="12" rx="2" fill="white"/></svg>',
            "btn_stop_"
        )
        stop_ico_dis = _write_temp_svg(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18">'
            f'<rect x="6" y="6" width="12" height="12" rx="2" fill="{c["muted"]}"/></svg>',
            "btn_stop_dis_"
        )

        self._play_ico_path = play_ico
        self._stop_ico_path = stop_ico
        self._play_ico_dis_path = play_ico_dis
        self._stop_ico_dis_path = stop_ico_dis

        DragLineEdit._accent_color = c['accent']
        self.setStyleSheet(build_stylesheet(c, checkbox_checked_css, checkbox_unchecked_css, arrow_ico))

    # ---- 控件状态切换 ----

    def _toggle_ext_entry(self, checked):
        self.le_ext.setEnabled(not checked)

    def _toggle_resize_fields(self, checked):
        self.le_width.setEnabled(checked)
        self.le_height.setEnabled(checked)
        self.le_max_size.setEnabled(checked)

    def _toggle_convert_fields(self, checked):
        self.cb_format.setEnabled(checked)

    # ---- 浏览对话框 ----

    def _browse_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Excel 文件", "",
            "Excel 文件 (*.xlsx *.xls);;所有文件 (*.*)"
        )
        if path:
            self.le_excel.setText(os.path.normpath(path))

    def _browse_dir(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            line_edit.setText(os.path.normpath(path))

    # ---- Excel 列加载 ----

    def _debounce_load_columns(self):
        self._debounce_timer.start()

    def _do_load_columns(self):
        path = self.le_excel.text().strip()
        if not path or not os.path.exists(path):
            self.cb_col.clear()
            self.lbl_col_hint.setText("选择 Excel 后自动加载列名")
            self.lbl_col_hint.setStyleSheet(f"color: {self._colors['muted']}; font-style: italic;")
            return

        try:
            choices, display_to_name = self.engine.load_column_names(path)
            self.column_display_to_name = display_to_name
            self.cb_col.clear()
            if choices:
                self.cb_col.addItems(choices)
                self.lbl_col_hint.setText(f"共 {len(choices)} 列")
                self.lbl_col_hint.setStyleSheet(f"color: {self._colors['green']}; font-weight: bold;")
            else:
                self.lbl_col_hint.setText("未检测到列")
                self.lbl_col_hint.setStyleSheet(f"color: {self._colors['red']};")
        except ImportError as e:
            if path.lower().endswith('.xls'):
                QMessageBox.critical(self, "缺少依赖", "读取 .xls 文件需要安装 xlrd：\npip install xlrd")
            else:
                QMessageBox.critical(self, "读取失败", str(e))
        except Exception as e:
            self.lbl_col_hint.setText(f"读取失败: {e}")
            self.lbl_col_hint.setStyleSheet(f"color: {self._colors['red']}; font-weight: bold;")

    # ---- 日志 ----

    def _thread_safe_log(self, message):
        """线程安全的日志回调，通过 QTimer 在主线程中更新 UI。"""
        QTimer.singleShot(0, lambda: self.append_log(message))

    def append_log(self, text):
        """追加彩色日志并更新统计。"""
        cursor = self.text_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        is_dark = self._colors['window'] == '#111827'
        if "[错误]" in text or "异常" in text:
            fmt.setForeground(QColor("#F87171" if is_dark else "#D32F2F"))
            fmt.setFontWeight(QFont.Weight.Bold)
        elif "[跳过]" in text:
            fmt.setForeground(QColor("#FBBF24" if is_dark else "#F57C00"))
        elif "[完成]" in text or "操作完成" in text:
            fmt.setForeground(QColor("#4ADE80" if is_dark else "#388E3C"))
            fmt.setFontWeight(QFont.Weight.Bold)
        elif "[复制]" in text or "[移动]" in text:
            fmt.setForeground(QColor("#60A5FA" if is_dark else "#1976D2"))
        elif "[图片处理]" in text or "[格式转换]" in text:
            fmt.setForeground(QColor("#C084FC" if is_dark else "#6A1B9A"))
        elif "[图片跳过]" in text or "[格式跳过]" in text:
            fmt.setForeground(QColor("#93C5FD" if is_dark else "#5C6BC0"))
        else:
            fmt.setForeground(QColor(self._colors['text']))

        cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        self.text_log.setTextCursor(cursor)
        self.text_log.ensureCursorVisible()

        # 更新统计
        self._update_stats_from_log(text)
        if text.strip():
            self.lbl_progress_detail.setText(' '.join(text.strip().split()))

    def _update_stats_from_log(self, text):
        m = re.search(r'成功[:：]\s*(\d+)', text)
        if m:
            self.lbl_success.setText(f"成功: {m.group(1)}")
        m = re.search(r'失败[:：]?\s*(\d+)', text)
        if m:
            self.lbl_failed.setText(f"失败: {m.group(1)}")
        m = re.search(r'跳过[:：]\s*(\d+)', text)
        if m:
            self.lbl_skipped.setText(f"跳过: {m.group(1)}")

    def _clear_log(self):
        self.text_log.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress_detail.setText("日志已清空")
        self.lbl_success.setText("成功: 0")
        self.lbl_failed.setText("失败: 0")
        self.lbl_skipped.setText("跳过: 0")

    # ---- 主处理流程 ----

    def start_process(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "任务正在运行中")
            return

        excel = self.le_excel.text().strip()
        column = self.cb_col.currentText().strip()
        src = self.le_source.text().strip()
        dst = self.le_output.text().strip()

        if not excel:
            QMessageBox.warning(self, "警告", "请选择 Excel 文件")
            return
        if not column:
            QMessageBox.warning(self, "警告", "请输入或选择列标识")
            return
        if not src:
            QMessageBox.warning(self, "警告", "请选择源文件夹")
            return
        if not dst:
            QMessageBox.warning(self, "警告", "请选择目标文件夹")
            return
        if not os.path.isdir(src):
            QMessageBox.warning(self, "警告", "源文件夹不存在")
            return

        extensions = FileMatcherEngine.build_extensions(
            self.le_ext.text(),
            self.chk_no_ext.isChecked(),
        )

        self.text_log.clear()
        self.progress_bar.setValue(0)
        self.lbl_progress_detail.setText("正在准备处理...")
        self.lbl_success.setText("成功: 0")
        self.lbl_failed.setText("失败: 0")
        self.lbl_skipped.setText("跳过: 0")
        self.unmatched_ids = []
        self.stop_event.clear()

        # 禁用控件
        self._set_controls_enabled(False)
        self.btn_start.setEnabled(False)
        self.btn_start.setIcon(QIcon(self._play_ico_dis_path) if self._play_ico_dis_path else QIcon())
        self.btn_start.setIconSize(QSize(20, 20))
        self.btn_stop.setEnabled(True)
        self.btn_stop.setIcon(QIcon(self._stop_ico_path) if self._stop_ico_path else QIcon())
        self.btn_stop.setIconSize(QSize(18, 18))
        self.progress_bar.start_animation()

        try:
            max_width = int(self.le_width.text() or 800)
            max_height = int(self.le_height.text() or 800)
            max_size = int(self.le_max_size.text() or 5000000)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "宽度、高度和文件大小必须是整数。")
            self._set_controls_enabled(True)
            self.btn_start.setEnabled(True)
            self.progress_bar.stop_animation()
            return

        kwargs = {
            'excel_path': excel,
            'column': column,
            'src_dir': src,
            'dst_dir': dst,
            'extensions': extensions,
            'recursive': self.chk_recursive.isChecked(),
            'move_mode': self.cb_move.currentIndex() == 1,
            'overwrite': self.chk_overwrite.isChecked(),
            'enable_resize': self.chk_resize.isChecked(),
            'max_width': max_width,
            'max_height': max_height,
            'max_size': max_size,
            'enable_convert': self.chk_convert.isChecked(),
            'target_format': self.cb_format.currentText(),
            'display_to_name': self.column_display_to_name,
        }

        self.worker = WorkerThread(self.engine, kwargs)
        self.worker.finished_signal.connect(self._process_finished)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def stop_process(self):
        if self.worker and self.worker.isRunning():
            self.stop_event.set()
            self.append_log("收到终止请求，正在安全停止...")
            self.btn_stop.setEnabled(False)

    def _set_controls_enabled(self, enabled):
        widgets = [
            self.le_excel, self.cb_col, self.le_source, self.le_output,
            self.le_ext, self.cb_move, self.chk_no_ext, self.chk_recursive,
            self.chk_overwrite, self.chk_resize, self.chk_convert,
            self.le_width, self.le_height, self.le_max_size, self.cb_format,
        ]
        for w in widgets:
            w.setEnabled(enabled)

    def _process_finished(self):
        self.progress_bar.stop_animation()
        self._set_controls_enabled(True)
        self.btn_start.setEnabled(True)
        self.btn_start.setIcon(QIcon(self._play_ico_path) if self._play_ico_path else QIcon())
        self.btn_start.setIconSize(QSize(20, 20))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setIcon(QIcon(self._stop_ico_dis_path) if self._stop_ico_dis_path else QIcon())
        self.btn_stop.setIconSize(QSize(18, 18))

        # 从工作线程获取未匹配编号列表
        if self.worker and self.worker.result:
            _, _, _, self.unmatched_ids = self.worker.result

        completed = not self.stop_event.is_set()
        if completed:
            self.progress_bar.setValue(100)
            self.lbl_progress_detail.setText("处理完成")
            QApplication.alert(self, 0)
        else:
            self.progress_bar.setFormat("已停止 %p%")
            self.lbl_progress_detail.setText("任务已停止")

    # ---- 保存未匹配编号 ----

    def save_unmatched(self):
        if not self.unmatched_ids:
            QMessageBox.information(self, "提示", "没有未匹配的编号可保存。")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存未匹配编号", "未匹配编号.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for num in self.unmatched_ids:
                    f.write(num + '\n')
            self.append_log(f"未匹配编号已保存到: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    # ---- 窗口关闭 ----

    def closeEvent(self, event):
        for p in _TEMP_ICON_PATHS:
            try:
                os.remove(p)
            except OSError:
                pass
        _TEMP_ICON_PATHS.clear()

        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, '确认退出',
                '当前有任务正在处理中，确定要退出吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_event.set()
                self.worker.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
