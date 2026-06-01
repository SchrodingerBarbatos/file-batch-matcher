# -*- coding: utf-8 -*-
"""主窗口布局 & 信号连接"""

import os
import re
import threading
import time
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QFileDialog, QMessageBox,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QGridLayout, QListView,
    QScrollArea, QStackedLayout,
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont, QIcon

from constants import (
    DEBOUNCE_MS, LOG_MAX_BLOCK_COUNT, DEFAULT_IMG_EXTENSIONS,
    WINDOW_MIN_W, WINDOW_MIN_H, WINDOW_MAX_W, WINDOW_MAX_H, WINDOW_SCREEN_RATIO,
    LEFT_RATIO, RIGHT_RATIO, LEFT_RATIO_NARROW, RIGHT_RATIO_NARROW, BREAKPOINT_WIDE,
    UI_GAP, UI_MARGIN,
    RADIUS_INPUT, RADIUS_CHECKBOX, H_INPUT, H_BUTTON, H_PRIMARY_BTN,
)
from services.icons import _write_temp_svg, _TEMP_ICON_PATHS
from core.engine import FileMatcherEngine
from ui.widgets import (
    DragLineEdit, RoundComboBox, AnimatedProgressBar,
    StepRow, CollapsibleSection, StatCard, CurrentFileBar,
    AdvancedOptionsCard, TabButton, OptionCard,
)
from ui.workers import WorkerThread
from ui.styles import get_theme_colors, build_stylesheet


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件批量匹配复制工具")
        self._colors = get_theme_colors()
        self._is_dark = self._colors.get('is_dark', False)

        # 动态计算窗口尺寸
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            target_w = int(available.width() * WINDOW_SCREEN_RATIO)
            target_h = int(available.height() * WINDOW_SCREEN_RATIO)
            window_w = min(max(target_w, WINDOW_MIN_W), WINDOW_MAX_W)
            window_h = min(max(target_h, WINDOW_MIN_H), WINDOW_MAX_H)
        else:
            window_w, window_h = 1200, 780
        self.resize(window_w, window_h)
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)

        self.stop_event = threading.Event()
        self.engine = FileMatcherEngine(
            log_callback=self._thread_safe_log,
            stop_event=self.stop_event,
        )
        self.worker = None
        self.unmatched_ids = []
        self.column_display_to_name = {}
        self._sum_ids = "0"
        self._sum_matched = "0"
        self._sum_files = "0"
        self._sum_time = ""

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_MS)
        self._debounce_timer.timeout.connect(self._do_load_columns)

        # 耗时计时器
        self._start_time = None
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

        # 扩展名复选框
        self._ext_checkboxes = {}

        self._setup_ui()

    # ---- UI 辅助方法 ----

    def _add_shadow(self, widget, blur=16, y=3):
        effect = QGraphicsDropShadowEffect(widget)
        effect.setBlurRadius(blur)
        effect.setOffset(0, y)
        effect.setColor(self._colors['shadow'])
        widget.setGraphicsEffect(effect)

    def _card_title(self, text, subtitle=""):
        """返回卡片标题区域：标题 + 可选副标题 + 细分割线。"""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        lbl = QLabel(text)
        lbl.setObjectName("cardTitle")
        layout.addWidget(lbl)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("cardSubtitle")
            layout.addWidget(sub)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {self._colors['border']}; max-height: 1px; border: none;")
        layout.addWidget(sep)
        return container

    def _section_separator(self):
        """返回一个浅灰色水平分隔线。"""
        line = QFrame()
        line.setObjectName("groupSeparator")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _adv_separator(self):
        """高级选项三栏之间的竖线分隔符。"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.NoFrame)
        line.setMinimumWidth(1)
        line.setMaximumWidth(1)
        line.setStyleSheet(
            f"background: {self._colors['border']}; min-width: 1px; max-width: 1px;"
        )
        return line

    def _setup_combo_view(self, combo):
        view = QListView()
        view.setObjectName("roundComboView")
        combo.setView(view)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(12)
        return combo

    def _group_header(self, text):
        """高级选项内的分组标题。"""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {self._colors['muted']}; "
            f"padding: 4px 0 2px 0; background: transparent;"
        )
        return lbl

    # ---- 主界面布局 ----

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ========== 全局 Header ==========
        header = QWidget()
        header.setFixedHeight(52)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(UI_MARGIN, 0, UI_MARGIN, 0)
        header_layout.setSpacing(10)
        title_icon = QLabel("📁")
        title_icon.setStyleSheet("font-size: 22px; background: transparent;")
        title_label = QLabel("文件批量匹配复制工具")
        title_label.setObjectName("appTitle")
        header_layout.addWidget(title_icon)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        root_layout.addWidget(header)

        # ========== Body：左右两栏 ==========
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(UI_MARGIN, 16, UI_MARGIN, UI_MARGIN)
        body_layout.setSpacing(UI_GAP)

        # ---- 左侧滚动区域 ----
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(UI_GAP)

        # ---- 右侧固定区域 ----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(UI_GAP)

        body_layout.addWidget(left_scroll, LEFT_RATIO)
        body_layout.addWidget(right_widget, RIGHT_RATIO)
        left_scroll.setWidget(left_widget)

        root_layout.addWidget(body, 1)

        # 存储引用用于响应式调整
        self._body_layout = body_layout
        self._left_scroll = left_scroll
        self._right_widget = right_widget

        # ========== 左侧：匹配配置卡片 ==========
        config_card = QFrame()
        config_card.setObjectName("CardFrame")
        config_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        config_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._add_shadow(config_card)
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(20, 18, 20, 16)
        config_layout.setSpacing(14)

        config_layout.addWidget(self._card_title("匹配配置", "请配置 Excel 与文件路径"))

        # Step 1: Excel 文件
        self.le_excel = DragLineEdit()
        self.le_excel.setPlaceholderText(r"D:\data\商品清单.xlsx")
        self.le_excel.setToolTip("选择包含编号列表的 Excel 文件（.xlsx 或 .xls）")
        self.le_excel.textChanged.connect(self._debounce_load_columns)
        btn_excel = QPushButton("浏览...")
        btn_excel.setFixedWidth(80)
        btn_excel.clicked.connect(self._browse_excel)
        self.step_excel = StepRow(1, "Excel 文件", self.le_excel, btn_excel, "请选择 Excel 文件")
        config_layout.addWidget(self.step_excel)

        # Step 2: 编号所在列
        self.cb_col = RoundComboBox()
        self._setup_combo_view(self.cb_col)
        self.cb_col.setToolTip("选择包含编号的列。支持列字母（如 A）或列名。")
        self.step_col = StepRow(2, "编号所在列", self.cb_col, status_text="选择 Excel 后自动加载列名")
        config_layout.addWidget(self.step_col)

        # Step 3: 源文件夹
        self.le_source = DragLineEdit()
        self.le_source.setPlaceholderText(r"D:\images\source")
        self.le_source.setToolTip("原始文件所在的文件夹")
        btn_source = QPushButton("浏览...")
        btn_source.setFixedWidth(80)
        btn_source.clicked.connect(lambda: self._browse_dir(self.le_source))
        self.step_source = StepRow(3, "源文件夹", self.le_source, btn_source)
        config_layout.addWidget(self.step_source)

        # Step 4: 目标文件夹
        self.le_output = DragLineEdit()
        self.le_output.setPlaceholderText(r"D:\images\output")
        self.le_output.setToolTip("匹配到的文件将复制/移动到此目录")
        btn_output = QPushButton("浏览...")
        btn_output.setFixedWidth(80)
        btn_output.clicked.connect(lambda: self._browse_dir(self.le_output))
        self.step_output = StepRow(4, "目标文件夹", self.le_output, btn_output, "匹配到的文件将保存到此目录")
        config_layout.addWidget(self.step_output)

        left_layout.addWidget(config_card)

        # ========== 左侧：操作按钮行 ==========
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.btn_start = QPushButton("  ▶ 开始")
        self.btn_start.setObjectName("startButton")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_process)
        btn_row.addWidget(self.btn_start, 7)

        self.btn_stop = QPushButton("  ■ 终止")
        self.btn_stop.setObjectName("stopButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_process)
        btn_row.addWidget(self.btn_stop, 3)

        left_layout.addLayout(btn_row)

        # ========== 左侧：高级选项卡片（Tab 布局） ==========
        self.adv_card = QFrame()
        self.adv_card.setObjectName("CardFrame")
        self.adv_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._add_shadow(self.adv_card)
        adv_layout = QVBoxLayout(self.adv_card)
        adv_layout.setContentsMargins(20, 18, 20, 16)
        adv_layout.setSpacing(12)

        adv_layout.addWidget(self._card_title("高级选项", "处理规则与图片限制"))

        # Tab 按钮行
        tab_row = QHBoxLayout()
        tab_row.setSpacing(0)
        self._tab_buttons = []
        tab_names = ["文件过滤", "文件处理", "图片处理"]
        for name in tab_names:
            btn = TabButton(name)
            btn.clicked.connect(lambda checked, n=name: self._switch_adv_tab(n))
            tab_row.addWidget(btn)
            self._tab_buttons.append(btn)
        tab_row.addStretch()
        adv_layout.addLayout(tab_row)

        # Tab 内容区（浅灰背景容器，样式由 QSS 统一管理）
        adv_content_frame = QFrame()
        adv_content_frame.setObjectName("advancedContentFrame")
        adv_content_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        adv_content_inner = QVBoxLayout(adv_content_frame)
        adv_content_inner.setContentsMargins(16, 16, 16, 16)
        adv_content_inner.setSpacing(0)

        self._adv_stack = QStackedLayout()
        self._adv_stack.setContentsMargins(0, 0, 0, 0)

        # -- 文件过滤 --
        page_filter = QWidget()
        pf_layout = QVBoxLayout(page_filter)
        pf_layout.setContentsMargins(0, 4, 0, 0)
        pf_layout.setSpacing(14)

        ext_grid = QGridLayout()
        ext_grid.setHorizontalSpacing(24)
        ext_grid.setVerticalSpacing(8)
        ext_grid.setContentsMargins(0, 0, 0, 0)
        common_exts = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.svg']
        for i, ext in enumerate(common_exts):
            cb = QCheckBox(ext.upper().lstrip('.'))
            cb.setChecked(
                ext.lower() in DEFAULT_IMG_EXTENSIONS
                or ext.lower().replace('.jpeg', '.jpg') in {e.replace('.jpeg', '.jpg') for e in DEFAULT_IMG_EXTENSIONS}
            )
            self._ext_checkboxes[ext] = cb
            ext_grid.addWidget(cb, i // 4, i % 4)
        pf_layout.addLayout(ext_grid)

        custom_label = QLabel("自定义扩展名")
        custom_label.setStyleSheet(
            f"font-size: 12px; color: {self._colors['muted']}; background: transparent;"
        )
        pf_layout.addWidget(custom_label)
        custom_desc = QLabel("支持输入 psd、ai、pdf 等，用逗号分隔")
        custom_desc.setStyleSheet(
            f"font-size: 11px; color: {self._colors['muted']}; background: transparent;"
        )
        pf_layout.addWidget(custom_desc)
        self._le_custom_ext = QLineEdit()
        self._le_custom_ext.setObjectName("advancedInput")
        self._le_custom_ext.setPlaceholderText("例如：psd, ai, pdf")
        self._le_custom_ext.setFixedHeight(H_INPUT)
        pf_layout.addWidget(self._le_custom_ext)
        pf_layout.addStretch()

        self._adv_stack.addWidget(page_filter)

        # -- 文件处理 --
        page_process = QWidget()
        pp_layout = QVBoxLayout(page_process)
        pp_layout.setContentsMargins(0, 4, 0, 0)
        pp_layout.setSpacing(14)

        self.chk_no_ext = QCheckBox("不限制扩展名")
        self.chk_no_ext.setToolTip("匹配所有文件，忽略扩展名过滤")
        self.chk_no_ext.toggled.connect(self._toggle_ext_checkboxes)

        self.chk_recursive = QCheckBox("递归搜索子文件夹")
        self.chk_recursive.setChecked(True)

        self.chk_overwrite = QCheckBox("目标存在时覆盖")

        self.chk_skip_exist = QCheckBox("跳过已存在文件")
        self.chk_skip_exist.setChecked(True)

        chk_grid = QGridLayout()
        chk_grid.setHorizontalSpacing(24)
        chk_grid.setVerticalSpacing(8)
        chk_grid.setContentsMargins(0, 0, 0, 0)
        chk_grid.addWidget(self.chk_no_ext, 0, 0)
        chk_grid.addWidget(self.chk_recursive, 0, 1)
        chk_grid.addWidget(self.chk_overwrite, 1, 0)
        chk_grid.addWidget(self.chk_skip_exist, 1, 1)
        pp_layout.addLayout(chk_grid)

        proc_label = QLabel("处理方式")
        proc_label.setStyleSheet(
            f"font-size: 12px; color: {self._colors['muted']}; background: transparent;"
        )
        pp_layout.addWidget(proc_label)
        self.cb_move = RoundComboBox()
        self.cb_move.setObjectName("advancedCombo")
        self._setup_combo_view(self.cb_move)
        self.cb_move.addItems(["复制（保留源文件）", "移动（剪切源文件）"])
        self.cb_move.setCurrentIndex(0)
        self.cb_move.setMaximumWidth(220)
        self.cb_move.setFixedHeight(H_INPUT)
        self.cb_move.setToolTip("复制更安全，移动更省空间")
        pp_layout.addWidget(self.cb_move)
        pp_layout.addStretch()

        self._adv_stack.addWidget(page_process)

        # -- 图片处理 --
        page_img = QWidget()
        pi_layout = QVBoxLayout(page_img)
        pi_layout.setContentsMargins(0, 4, 0, 0)
        pi_layout.setSpacing(14)

        self.chk_resize = QCheckBox("启用图片尺寸大小处理")
        self.chk_resize.setChecked(True)  # 默认启用
        self.chk_resize.toggled.connect(self._toggle_resize_fields)
        pi_layout.addWidget(self.chk_resize)

        # 两列表单布局：标签在上，控件在下
        img_form = QGridLayout()
        img_form.setHorizontalSpacing(24)
        img_form.setVerticalSpacing(12)
        img_form.setContentsMargins(0, 0, 0, 0)

        # ---- 第一行：最大宽度 / 最大高度 ----
        lbl_w = QLabel("最大宽度")
        lbl_w.setStyleSheet(f"font-size: 12px; color: {self._colors['muted']}; background: transparent;")
        img_form.addWidget(lbl_w, 0, 0)

        lbl_h = QLabel("最大高度")
        lbl_h.setStyleSheet(f"font-size: 12px; color: {self._colors['muted']}; background: transparent;")
        img_form.addWidget(lbl_h, 0, 1)

        w_row = QHBoxLayout()
        w_row.setSpacing(6)
        w_row.setContentsMargins(0, 0, 0, 0)
        self.le_width = QLineEdit("800")
        self.le_width.setObjectName("advancedInput")
        self.le_width.setPlaceholderText("800")
        self.le_width.setFixedWidth(160)
        self.le_width.setFixedHeight(H_INPUT)
        w_row.addWidget(self.le_width)
        lbl_px1 = QLabel("px")
        lbl_px1.setStyleSheet(f"color: {self._colors['muted']}; font-size: 12px; background: transparent;")
        w_row.addWidget(lbl_px1, 0, Qt.AlignmentFlag.AlignVCenter)
        w_row.addStretch()
        img_form.addLayout(w_row, 1, 0)

        h_row = QHBoxLayout()
        h_row.setSpacing(6)
        h_row.setContentsMargins(0, 0, 0, 0)
        self.le_height = QLineEdit("800")
        self.le_height.setObjectName("advancedInput")
        self.le_height.setPlaceholderText("800")
        self.le_height.setFixedWidth(160)
        self.le_height.setFixedHeight(H_INPUT)
        h_row.addWidget(self.le_height)
        lbl_px2 = QLabel("px")
        lbl_px2.setStyleSheet(f"color: {self._colors['muted']}; font-size: 12px; background: transparent;")
        h_row.addWidget(lbl_px2, 0, Qt.AlignmentFlag.AlignVCenter)
        h_row.addStretch()
        img_form.addLayout(h_row, 1, 1)

        # ---- 第二行：最大大小 / 目标格式 ----
        lbl_s = QLabel("最大大小")
        lbl_s.setStyleSheet(f"font-size: 12px; color: {self._colors['muted']}; background: transparent;")
        img_form.addWidget(lbl_s, 2, 0)

        lbl_f = QLabel("目标格式")
        lbl_f.setStyleSheet(f"font-size: 12px; color: {self._colors['muted']}; background: transparent;")
        img_form.addWidget(lbl_f, 2, 1)

        s_row = QHBoxLayout()
        s_row.setSpacing(6)
        s_row.setContentsMargins(0, 0, 0, 0)
        self.le_max_size = QLineEdit("5000")
        self.le_max_size.setObjectName("advancedInput")
        self.le_max_size.setPlaceholderText("5000")
        self.le_max_size.setFixedWidth(160)
        self.le_max_size.setFixedHeight(H_INPUT)
        s_row.addWidget(self.le_max_size)
        lbl_kb = QLabel("KB")
        lbl_kb.setStyleSheet(f"color: {self._colors['muted']}; font-size: 12px; background: transparent;")
        s_row.addWidget(lbl_kb, 0, Qt.AlignmentFlag.AlignVCenter)
        s_row.addStretch()
        img_form.addLayout(s_row, 3, 0)

        self.cb_format = RoundComboBox()
        self.cb_format.setObjectName("advancedCombo")
        self._setup_combo_view(self.cb_format)
        self.cb_format.addItems(["保持原格式", "JPEG", "PNG"])
        self.cb_format.setCurrentIndex(1)
        self.cb_format.setFixedWidth(160)
        self.cb_format.setFixedHeight(H_INPUT)
        img_form.addWidget(self.cb_format, 3, 1, Qt.AlignmentFlag.AlignVCenter)

        pi_layout.addLayout(img_form)
        pi_layout.addStretch()

        # 初始化禁用状态
        self._toggle_resize_fields(self.chk_resize.isChecked())

        self._adv_stack.addWidget(page_img)

        adv_stack_widget = QWidget()
        adv_stack_widget.setLayout(self._adv_stack)
        adv_content_inner.addWidget(adv_stack_widget)
        adv_layout.addWidget(adv_content_frame, 1)

        left_layout.addWidget(self.adv_card, 1)

        # 默认选中第一个 Tab
        self._switch_adv_tab("文件过滤")

        # ========== 右侧：运行状态卡片 ==========
        status_card = QFrame()
        status_card.setObjectName("CardFrame")
        status_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._add_shadow(status_card)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(20, 18, 20, 14)
        status_layout.setSpacing(10)

        status_layout.addWidget(self._card_title("运行状态"))

        # 进度条 + 百分比（同一行）
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        progress_row.addWidget(self.progress_bar, 1)
        self.lbl_percent = QLabel("0%")
        self.lbl_percent.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {self._colors['green']}; "
            f"background: transparent; min-width: 40px;"
        )
        self.lbl_percent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.lbl_percent)
        status_layout.addLayout(progress_row)

        # 状态信息行（当前状态 + 预计剩余 + 速度）
        info_row = QHBoxLayout()
        info_row.setSpacing(16)
        self.lbl_status_text = QLabel("准备就绪")
        self.lbl_status_text.setStyleSheet(
            f"font-size: 12px; color: {self._colors['muted']}; background: transparent;"
        )
        self.lbl_remaining = QLabel("预计剩余：--:--")
        self.lbl_remaining.setStyleSheet(
            f"font-size: 12px; color: {self._colors['muted']}; background: transparent;"
        )
        self.lbl_speed = QLabel("当前速度：--")
        self.lbl_speed.setStyleSheet(
            f"font-size: 12px; color: {self._colors['muted']}; background: transparent;"
        )
        info_row.addWidget(self.lbl_status_text)
        info_row.addWidget(self.lbl_remaining)
        info_row.addWidget(self.lbl_speed)
        info_row.addStretch()
        status_layout.addLayout(info_row)

        right_layout.addWidget(status_card)

        # ========== 右侧：统计卡片 ==========
        stats_row = QHBoxLayout()
        stats_row.setSpacing(UI_GAP)
        self.stat_matched = StatCard("已匹配", self._colors['blue'], "check")
        self.stat_copied = StatCard("已复制", self._colors['green'], "copy")
        self.stat_unmatched = StatCard("未匹配", self._colors['warning'], "warn")
        self.stat_failed = StatCard("失败", self._colors['red'], "cross")
        for card in (self.stat_matched, self.stat_copied, self.stat_unmatched, self.stat_failed):
            stats_row.addWidget(card)
        right_layout.addLayout(stats_row)

        # ========== 右侧：当前文件条 ==========
        self.current_file_bar = CurrentFileBar()
        right_layout.addWidget(self.current_file_bar)

        # ========== 右侧：运行日志卡片 ==========
        log_card = QFrame()
        log_card.setObjectName("CardFrame")
        log_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._add_shadow(log_card)
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 18, 20, 14)
        log_layout.setSpacing(10)

        # 日志标题行（标题 + 工具按钮）
        log_header = QHBoxLayout()
        log_header.setSpacing(6)
        log_title_lbl = QLabel("运行日志")
        log_title_lbl.setObjectName("cardTitle")
        self.btn_save_unmatched = QPushButton("保存未匹配编号")
        self.btn_save_unmatched.setObjectName("logToolButton")
        self.btn_save_unmatched.clicked.connect(self.save_unmatched)
        self.btn_clear_log = QPushButton("清空日志")
        self.btn_clear_log.setObjectName("logToolButton")
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_export_log = QPushButton("导出日志")
        self.btn_export_log.setObjectName("logToolButton")
        self.btn_export_log.clicked.connect(self.export_log)
        log_header.addWidget(log_title_lbl)
        log_header.addStretch()
        log_header.addWidget(self.btn_save_unmatched, 0)
        log_header.addWidget(self.btn_clear_log, 0)
        log_header.addWidget(self.btn_export_log)
        log_layout.addLayout(log_header)

        # 标题下方分割线
        log_sep = QFrame()
        log_sep.setFrameShape(QFrame.Shape.HLine)
        log_sep.setStyleSheet(f"background: {self._colors['border']}; max-height: 1px; border: none;")
        log_layout.addWidget(log_sep)

        # 日志内容区（含空状态）— 用圆角容器包裹
        self._log_content_frame = QFrame()
        self._log_content_frame.setObjectName("logContentFrame")
        self._log_content_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        log_content_layout = QVBoxLayout(self._log_content_frame)
        log_content_layout.setContentsMargins(0, 0, 0, 0)
        log_content_layout.setSpacing(0)

        # 空状态提示（位于日志区约 35% 高度处）
        log_content_layout.addStretch(35)
        self._log_empty_state = QLabel(
            "暂无日志\n开始匹配后将显示文件扫描、匹配结果和错误信息"
        )
        self._log_empty_state.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._log_empty_state.setStyleSheet(
            f"font-size: 13px; color: {self._colors['muted']}; background: transparent; "
            f"padding: 0px 20px 0px 20px;"
        )
        log_content_layout.addWidget(self._log_empty_state)
        log_content_layout.addStretch(65)

        # 日志文本区（初始隐藏）
        self.text_log = QTextEdit()
        self.text_log.setObjectName("logTextEdit")
        self.text_log.setReadOnly(True)
        self.text_log.document().setMaximumBlockCount(LOG_MAX_BLOCK_COUNT)
        self.text_log.setVisible(False)
        log_content_layout.addWidget(self.text_log)

        # 保存布局引用，以便切换时调整拉伸因子
        self._log_content_layout = log_content_layout

        log_layout.addWidget(self._log_content_frame, 1)

        right_layout.addWidget(log_card, 1)

        self._apply_app_style()

    # ---- 响应式断点 ----

    def resizeEvent(self, event):
        """窗口大小变化时调整布局比例。"""
        super().resizeEvent(event)
        w = event.size().width()
        if w >= BREAKPOINT_WIDE:
            left_r, right_r = LEFT_RATIO, RIGHT_RATIO
        else:
            left_r, right_r = LEFT_RATIO_NARROW, RIGHT_RATIO_NARROW
        self._body_layout.setStretch(0, left_r)
        self._body_layout.setStretch(1, right_r)

    # ---- 样式 ----

    def _apply_app_style(self):
        c = self._colors

        checkbox_checked_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">'
            f'<rect x="2" y="2" width="20" height="20" rx="{RADIUS_CHECKBOX}" ry="{RADIUS_CHECKBOX}" fill="{c["green"]}" />'
            f'<path d="M8 12 L11 15 L16 9" fill="none" stroke="#FFFFFF"'
            f' stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        checkbox_unchecked_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">'
            f'<rect x="2" y="2" width="20" height="20" rx="{RADIUS_CHECKBOX}" ry="{RADIUS_CHECKBOX}" '
            f'fill="{c["input"]}" stroke="{c["input_border"]}" stroke-width="2" />'
            f'</svg>'
        )
        cb_checked_ico = _write_temp_svg(checkbox_checked_svg, "cb_checked_ico_")
        cb_unchecked_ico = _write_temp_svg(checkbox_unchecked_svg, "cb_unchecked_ico_")
        checkbox_checked_css = (
            f"background-image: url({cb_checked_ico}); background-repeat: no-repeat; background-position: center;"
            if cb_checked_ico else f"background: {c['green']};"
        )
        checkbox_unchecked_css = (
            f"background-image: url({cb_unchecked_ico}); background-repeat: no-repeat; background-position: center;"
            if cb_unchecked_ico else f"background: {c['input']};"
        )

        arrow_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 8" width="12" height="8">'
            f'<path d="M1.5 1.5L6 6L10.5 1.5" fill="none" stroke="{c["muted"]}"'
            f' stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>'
        )
        arrow_ico = _write_temp_svg(arrow_svg, "cb_arrow_")

        self._play_ico_path = None
        self._play_ico_dis_path = None

        for le in (self.le_excel, self.le_source, self.le_output):
            le._accent_color = c['accent']
        self.setStyleSheet(build_stylesheet(c, checkbox_checked_css, checkbox_unchecked_css, arrow_ico))

    # ---- 控件状态切换 ----

    def _toggle_ext_checkboxes(self, checked):
        """不限制扩展名时禁用所有扩展名复选框。"""
        for cb in self._ext_checkboxes.values():
            cb.setEnabled(not checked)
        self._le_custom_ext.setEnabled(not checked)

    def _toggle_resize_fields(self, checked):
        self.le_width.setEnabled(checked)
        self.le_height.setEnabled(checked)
        self.le_max_size.setEnabled(checked)
        self.cb_format.setEnabled(checked)

    def _switch_adv_tab(self, name):
        tab_map = {"文件过滤": 0, "文件处理": 1, "图片处理": 2}
        idx = tab_map.get(name, 0)
        self._adv_stack.setCurrentIndex(idx)
        for btn in self._tab_buttons:
            btn.setChecked(btn.text().strip() == name)

    def _collect_extensions(self):
        """从扩展名复选框收集当前选中的扩展名集合。"""
        if self.chk_no_ext.isChecked():
            return None
        exts = set()
        for ext, cb in self._ext_checkboxes.items():
            if cb.isChecked():
                exts.add(ext.lower())
        custom = self._le_custom_ext.text().strip()
        if custom:
            for ext in custom.split():
                exts.add(ext.lower() if ext.startswith('.') else f'.{ext.lower()}')
        return exts if exts else None

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
            self.step_col.set_status("选择 Excel 后自动加载列名", "hint")
            self.step_excel.set_status("请选择 Excel 文件", "hint")
            return

        try:
            choices, display_to_name = self.engine.load_column_names(path)
            self.column_display_to_name = display_to_name
            self.cb_col.clear()
            if choices:
                self.cb_col.addItems(choices)
                self.step_col.set_status(f"共 {len(choices)} 列", "ok")
                self.step_excel.set_status(f"已读取 {len(choices)} 列", "ok")
            else:
                self.step_col.set_status("未检测到列", "error")
                self.step_excel.set_status("未检测到列", "error")
        except ImportError as e:
            if path.lower().endswith('.xls'):
                QMessageBox.critical(self, "缺少依赖", "读取 .xls 文件需要安装 xlrd：\npip install xlrd")
            else:
                QMessageBox.critical(self, "读取失败", str(e))
            self.step_excel.set_status("读取失败", "error")
        except Exception as e:
            self.step_col.set_status(f"读取失败: {e}", "error")
            self.step_excel.set_status("读取失败", "error")

    # ---- 日志 ----

    def _thread_safe_log(self, message):
        """线程安全的日志回调，通过 QTimer 在主线程中更新 UI。"""
        QTimer.singleShot(0, self, lambda: self.append_log(message))

    def _set_log_stretch_enabled(self, enabled):
        """启用或禁用空状态的拉伸因子。"""
        layout = self._log_content_layout
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.spacerItem():
                if enabled:
                    item.changeSize(0, 0, QSizePolicy.Policy.Expanding)
                else:
                    item.changeSize(0, 0)
        layout.invalidate()  # 强制重新布局

    def _show_log_content(self):
        """切换到日志内容模式（隐藏空状态）。"""
        if not self.text_log.isVisible():
            self._log_empty_state.setVisible(False)
            # 禁用空状态的拉伸因子，让日志内容占据全部空间
            self._set_log_stretch_enabled(False)
            self.text_log.setVisible(True)

    def _show_log_empty_state(self):
        """切换到空状态模式（隐藏日志内容）。"""
        self.text_log.setVisible(False)
        # 恢复空状态的拉伸因子
        self._log_empty_state.setVisible(True)
        self._set_log_stretch_enabled(True)

    def _get_log_dot_color(self, text):
        """根据日志类型返回圆点颜色。"""
        if "[错误]" in text or "异常" in text:
            return "#EF4444"
        elif "[跳过]" in text:
            return "#F59E0B"
        elif "[完成]" in text or "操作完成" in text:
            return "#22C55E"
        elif "[复制]" in text or "[移动]" in text:
            return "#3B82F6"
        elif "[图片处理]" in text or "[格式转换]" in text:
            return "#A855F7"
        else:
            return self._colors['muted']

    def append_log(self, text):
        """追加带时间戳和彩色圆点的日志。"""
        self._show_log_content()

        cursor = self.text_log.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        timestamp = datetime.now().strftime("%H:%M:%S")
        dot_color = self._get_log_dot_color(text)
        is_dark = self._is_dark

        # 写入彩色圆点
        dot_fmt = QTextCharFormat()
        dot_fmt.setForeground(QColor(dot_color))
        cursor.setCharFormat(dot_fmt)
        cursor.insertText("● ")

        # 写入时间戳
        ts_fmt = QTextCharFormat()
        ts_fmt.setForeground(QColor(self._colors['muted']))
        cursor.setCharFormat(ts_fmt)
        cursor.insertText(f"{timestamp} ")

        # 写入日志内容
        content_fmt = QTextCharFormat()
        if "[错误]" in text or "异常" in text:
            content_fmt.setForeground(QColor("#F87171" if is_dark else "#D32F2F"))
            content_fmt.setFontWeight(QFont.Weight.Bold)
        elif "[跳过]" in text:
            content_fmt.setForeground(QColor("#FBBF24" if is_dark else "#F57C00"))
        elif "[完成]" in text or "操作完成" in text:
            content_fmt.setForeground(QColor("#4ADE80" if is_dark else "#388E3C"))
            content_fmt.setFontWeight(QFont.Weight.Bold)
        elif "[复制]" in text or "[移动]" in text:
            content_fmt.setForeground(QColor("#60A5FA" if is_dark else "#1976D2"))
        elif "[图片处理]" in text or "[格式转换]" in text:
            content_fmt.setForeground(QColor("#C084FC" if is_dark else "#6A1B9A"))
        elif "[图片跳过]" in text or "[格式跳过]" in text:
            content_fmt.setForeground(QColor("#93C5FD" if is_dark else "#5C6BC0"))
        else:
            content_fmt.setForeground(QColor(self._colors['text']))

        cursor.setCharFormat(content_fmt)
        cursor.insertText(text + "\n")
        self.text_log.setTextCursor(cursor)
        self.text_log.ensureCursorVisible()

        # 更新统计
        self._update_stats_from_log(text)
        # 更新当前文件
        self._update_current_file(text)
        # 更新状态文本
        if text.strip():
            self.lbl_status_text.setText(' '.join(text.strip().split())[:80])

    def _update_summary(self):
        """刷新汇总栏文字。"""
        t = self._sum_time or "00:00"
        self.current_file_bar.set_summary(
            f"编号总数：{self._sum_ids}  已匹配：{self._sum_matched}  "
            f"文件总数：{self._sum_files}  耗时：{t}"
        )

    def _update_stats_from_log(self, text):
        """从日志文本解析统计数据并更新统计卡片。"""
        m = re.search(r'匹配到\s*(\d+)\s*个编号', text)
        if m:
            self.stat_matched.set_count(int(m.group(1)))
            self._sum_matched = m.group(1)

        m = re.search(r'参与编号\s*(\d+)', text)
        if m:
            self._sum_ids = m.group(1)

        m = re.search(r'匹配文件总数\s*(\d+)', text)
        if m:
            self._sum_files = m.group(1)

        m = re.search(r'未匹配\s*(\d+)\s*个编号', text)
        if m:
            self.stat_unmatched.set_count(int(m.group(1)))

        m = re.search(r'成功[:：]\s*(\d+)', text)
        if m:
            self.stat_copied.set_count(int(m.group(1)))

        m = re.search(r'错误\s*(\d+)', text)
        if m:
            self.stat_failed.set_count(int(m.group(1)))

        m = re.search(r'共读取到\s*(\d+)\s*个唯一编号', text)
        if m:
            self._sum_ids = m.group(1)

        self._update_summary()

    def _update_current_file(self, text):
        """从日志中提取当前处理的文件名。"""
        m = re.search(r'\[(复制|移动)\]\s*(.+)', text)
        if m:
            self.current_file_bar.set_file(m.group(2).strip())

    def _update_elapsed(self):
        """更新耗时显示。"""
        if self._start_time:
            elapsed = int(time.time() - self._start_time)
            mins, secs = divmod(elapsed, 60)
            hours, mins = divmod(mins, 60)
            if hours:
                self._sum_time = f"{hours:02d}:{mins:02d}:{secs:02d}"
            else:
                self._sum_time = f"{mins:02d}:{secs:02d}"
            self._update_summary()

    def _clear_log(self):
        self.text_log.clear()
        self._show_log_empty_state()
        self.progress_bar.setValue(0)
        self.lbl_percent.setText("0%")
        self.lbl_status_text.setText("准备就绪")
        self.lbl_remaining.setText("预计剩余：--:--")
        self.lbl_speed.setText("当前速度：--")
        self.stat_matched.set_count(0)
        self.stat_copied.set_count(0)
        self.stat_unmatched.set_count(0)
        self.stat_failed.set_count(0)
        self._sum_ids = "0"
        self._sum_matched = "0"
        self._sum_files = "0"
        self._sum_time = ""
        self.current_file_bar.reset()

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

        extensions = self._collect_extensions()

        self.text_log.clear()
        self.progress_bar.setValue(0)
        self.lbl_percent.setText("0%")
        self.lbl_status_text.setText("正在准备处理...")
        self.lbl_remaining.setText("预计剩余：计算中...")
        self.lbl_speed.setText("当前速度：--")
        self.stat_matched.set_count(0)
        self.stat_copied.set_count(0)
        self.stat_unmatched.set_count(0)
        self.stat_failed.set_count(0)
        self._sum_ids = "0"
        self._sum_matched = "0"
        self._sum_files = "0"
        self._sum_time = ""
        self.current_file_bar.reset()
        self.unmatched_ids = []
        self.stop_event.clear()

        # 启动耗时计时器
        self._start_time = time.time()
        self._elapsed_timer.start()

        # 禁用控件
        self._set_controls_enabled(False)
        self.btn_start.setEnabled(False)
        self.btn_start.setText("  处理中...")
        self.btn_stop.setEnabled(True)
        self.progress_bar.start_animation()

        try:
            max_width = int(self.le_width.text() or 800)
            max_height = int(self.le_height.text() or 800)
            max_size_kb = int(self.le_max_size.text() or 5000)
            max_size = max_size_kb * 1024  # KB 转 bytes
        except ValueError:
            QMessageBox.warning(self, "输入错误", "宽度、高度和文件大小必须是整数。")
            self._restore_controls_after_error()
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
            'enable_convert': self.cb_format.currentIndex() > 0,
            'target_format': self.cb_format.currentText(),
            'display_to_name': self.column_display_to_name,
        }

        self.worker = WorkerThread(self.engine, kwargs)
        self.worker.finished_signal.connect(self._process_finished)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.start()

    def _restore_controls_after_error(self):
        """输入校验失败时恢复控件状态。"""
        self._elapsed_timer.stop()
        self._start_time = None
        self._set_controls_enabled(True)
        self.btn_start.setEnabled(True)
        self.btn_start.setText("  ▶ 开始")
        self.btn_stop.setEnabled(False)
        self.progress_bar.stop_animation()

    def stop_process(self):
        if self.worker and self.worker.isRunning():
            self.stop_event.set()
            self.append_log("收到终止请求，正在安全停止...")
            self.btn_stop.setEnabled(False)

    def _set_controls_enabled(self, enabled):
        widgets = [
            self.le_excel, self.cb_col, self.le_source, self.le_output,
            self.cb_move, self.chk_no_ext, self.chk_recursive,
            self.chk_overwrite, self.chk_resize,
            self.le_width, self.le_height, self.le_max_size, self.cb_format,
            self.chk_skip_exist,
        ]
        # 扩展名复选框
        for cb in self._ext_checkboxes.values():
            widgets.append(cb)
        widgets.append(self._le_custom_ext)

        for w in widgets:
            w.setEnabled(enabled)
        if enabled:
            self._toggle_resize_fields(self.chk_resize.isChecked())
            self._toggle_ext_checkboxes(self.chk_no_ext.isChecked())

    def _update_progress(self, percent):
        """更新进度条和百分比标签。"""
        self.progress_bar.setValue(percent)
        self.lbl_percent.setText(f"{percent}%")

    def _process_finished(self):
        self._elapsed_timer.stop()
        self.progress_bar.stop_animation()
        self._set_controls_enabled(True)
        self.btn_start.setEnabled(True)
        self.btn_start.setText("  ▶ 开始")
        self.btn_stop.setEnabled(False)

        # 从工作线程获取未匹配编号列表
        if self.worker and self.worker.result:
            _, _, _, self.unmatched_ids = self.worker.result

        completed = not self.stop_event.is_set()
        if completed:
            self.progress_bar.setValue(100)
            self.lbl_percent.setText("100%")
            self.lbl_status_text.setText("处理完成")
            self.lbl_remaining.setText("预计剩余：已完成")
            self.lbl_speed.setText("当前速度：--")
            QApplication.alert(self, 0)
        else:
            self.lbl_status_text.setText("任务已停止")
            self.lbl_remaining.setText("预计剩余：已停止")
            self.lbl_speed.setText("当前速度：--")

    # ---- 导出日志 ----

    def export_log(self):
        """导出日志内容到文件。"""
        if not self.text_log.toPlainText().strip():
            QMessageBox.information(self, "提示", "日志为空，无需导出。")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "运行日志.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.text_log.toPlainText())
            QMessageBox.information(self, "成功", f"日志已导出到:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {e}")

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
        if self._elapsed_timer.isActive():
            self._elapsed_timer.stop()

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
            else:
                event.ignore()
                return

        for p in _TEMP_ICON_PATHS:
            try:
                os.remove(p)
            except OSError:
                pass
        _TEMP_ICON_PATHS.clear()
        event.accept()
