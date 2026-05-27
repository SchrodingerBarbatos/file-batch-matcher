# UI排版改进实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构UI布局，采用经典左右分栏设计，解决布局拥挤和比例不协调问题

**Architecture:** 将现有上下布局改为左右分栏布局，左侧为可滚动的设置区域（40%宽度），右侧为固定的操作和日志区域（60%宽度）。使用QScrollArea实现左侧滚动，保持现有功能不变。

**Tech Stack:** PySide6 (Qt 6.11.0), Python 3.13.13, QSS样式

---

## 文件结构

### 需要修改的文件
- `ui/main_window.py` - 主窗口布局重构（主要修改）
- `ui/styles.py` - 样式调整（间距、比例）
- `ui/widgets.py` - 可能需要添加滚动支持

### 需要创建的文件
- 无（所有修改都在现有文件中）

### 参考文件
- `docs/superpowers/specs/2026-05-27-ui-layout-redesign-design.md` - 设计规范
- `constants.py` - 常量定义
- `ui/workers.py` - 工作线程（不需要修改）

---

## 实施任务

### Task 1: 分析现有布局结构

**Files:**
- Read: `ui/main_window.py`
- Read: `ui/styles.py`
- Read: `ui/widgets.py`

- [ ] **Step 1: 阅读现有布局代码**

阅读 `ui/main_window.py` 中的 `_setup_ui` 方法，了解当前布局结构：
- 上部：路径设置（左侧）+ 匹配选项（右侧）
- 中部：图片处理选项
- 下部：操作按钮+进度+统计（左侧）+ 日志（右侧）

- [ ] **Step 2: 分析样式定义**

阅读 `ui/styles.py`，了解当前样式定义：
- 颜色方案
- 间距规范
- 控件样式

- [ ] **Step 3: 记录需要保留的功能**

记录所有现有功能，确保重构后不会丢失：
- 路径设置（Excel文件、编号列、源文件夹、目标文件夹）
- 匹配选项（扩展名、处理方式、复选框）
- 图片处理（尺寸、格式转换）
- 操作按钮（开始、终止）
- 进度显示（进度条、统计信息）
- 日志显示

---

### Task 2: 创建左侧滚动区域框架

**Files:**
- Modify: `ui/main_window.py:84-100`

- [ ] **Step 1: 导入QScrollArea**

在 `ui/main_window.py` 的导入部分添加 QScrollArea：

```python
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QTextEdit, QFileDialog, QMessageBox,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QGridLayout, QListView,
    QScrollArea,  # 添加这一行
)
```

- [ ] **Step 2: 修改主窗口尺寸**

修改窗口默认尺寸为 1000x750：

```python
def __init__(self):
    super().__init__()
    self.setWindowTitle("文件批量匹配复制工具")
    self.resize(1000, 750)  # 修改为 1000x750
    # ... 其余代码
```

- [ ] **Step 3: 创建左右分栏布局**

修改 `_setup_ui` 方法，创建左右分栏布局：

```python
def _setup_ui(self):
    central_widget = QWidget()
    self.setCentralWidget(central_widget)
    ui_gap = 16  # 修改为 16px
    main_layout = QHBoxLayout(central_widget)  # 改为水平布局
    main_layout.setContentsMargins(ui_gap, ui_gap, ui_gap, ui_gap)
    main_layout.setSpacing(ui_gap)

    # 左侧滚动区域
    left_scroll = QScrollArea()
    left_scroll.setWidgetResizable(True)
    left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    left_scroll.setMinimumWidth(350)

    # 左侧内容容器
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(ui_gap)

    # 右侧固定区域
    right_widget = QWidget()
    right_layout = QVBoxLayout(right_widget)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(ui_gap)

    # 将左右区域添加到主布局
    main_layout.addWidget(left_scroll, 40)  # 40% 比例
    main_layout.addWidget(right_widget, 60)  # 60% 比例

    # 设置左侧滚动区域的内容
    left_scroll.setWidget(left_widget)

    # TODO: 后续任务将填充左右区域的内容
```

- [ ] **Step 4: 验证布局框架**

运行程序，检查是否显示空白的左右分栏布局：

```bash
python main.py
```

预期结果：窗口显示左右两个空白区域，左侧可以滚动

- [ ] **Step 5: 提交布局框架**

```bash
git add ui/main_window.py
git commit -m "refactor: 创建左右分栏布局框架"
```

---

### Task 3: 迁移路径设置到左侧滚动区域

**Files:**
- Modify: `ui/main_window.py:100-166`

- [ ] **Step 1: 创建路径设置卡片**

在左侧布局中添加路径设置卡片：

```python
# 在 _setup_ui 方法中，left_layout 添加内容

# 路径与文件设置卡片
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

# 将路径设置卡片添加到左侧布局
left_layout.addWidget(path_group)
```

- [ ] **Step 2: 验证路径设置显示**

运行程序，检查路径设置是否正确显示在左侧：

```bash
python main.py
```

预期结果：左侧显示路径设置卡片，包含Excel文件、编号列、源文件夹、目标文件夹

- [ ] **Step 3: 提交路径设置迁移**

```bash
git add ui/main_window.py
git commit -m "refactor: 迁移路径设置到左侧滚动区域"
```

---

### Task 4: 迁移匹配选项到左侧滚动区域

**Files:**
- Modify: `ui/main_window.py:168-214`

- [ ] **Step 1: 创建匹配选项卡片**

在左侧布局中添加匹配选项卡片：

```python
# 在路径设置卡片之后添加

# 匹配选项卡片
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

# 将匹配选项卡片添加到左侧布局
left_layout.addWidget(opt_group)
```

- [ ] **Step 2: 验证匹配选项显示**

运行程序，检查匹配选项是否正确显示在左侧：

```bash
python main.py
```

预期结果：左侧显示匹配选项卡片，包含扩展名、处理方式、复选框

- [ ] **Step 3: 提交匹配选项迁移**

```bash
git add ui/main_window.py
git commit -m "refactor: 迁移匹配选项到左侧滚动区域"
```

---

### Task 5: 迁移图片处理到左侧滚动区域

**Files:**
- Modify: `ui/main_window.py:217-267`

- [ ] **Step 1: 创建图片处理卡片**

在左侧布局中添加图片处理卡片：

```python
# 在匹配选项卡片之后添加

# 图片处理卡片
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

# 将图片处理卡片添加到左侧布局
left_layout.addWidget(img_group)

# 添加弹性空间，将卡片推到顶部
left_layout.addStretch()
```

- [ ] **Step 2: 验证图片处理显示**

运行程序，检查图片处理是否正确显示在左侧：

```bash
python main.py
```

预期结果：左侧显示图片处理卡片，包含尺寸处理和格式转换选项

- [ ] **Step 3: 提交图片处理迁移**

```bash
git add ui/main_window.py
git commit -m "refactor: 迁移图片处理到左侧滚动区域"
```

---

### Task 6: 创建右侧操作区域

**Files:**
- Modify: `ui/main_window.py:269-344`

- [ ] **Step 1: 创建操作按钮区**

在右侧布局中添加操作按钮：

```python
# 在 _setup_ui 方法中，right_layout 添加内容

# 操作按钮区（扁平化）
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

# 辅助按钮区（扁平化）
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
```

- [ ] **Step 2: 创建日志区域**

在右侧布局中添加日志卡片：

```python
# 在辅助按钮区之后添加

# 日志卡片
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

# 将日志卡片添加到右侧布局
right_layout.addWidget(log_group, 1)  # 日志区域占据剩余空间
```

- [ ] **Step 3: 验证右侧区域显示**

运行程序，检查右侧操作区域是否正确显示：

```bash
python main.py
```

预期结果：右侧显示操作按钮、进度条、统计信息、辅助按钮、日志区域

- [ ] **Step 4: 提交右侧区域创建**

```bash
git add ui/main_window.py
git commit -m "refactor: 创建右侧操作和日志区域"
```

---

### Task 7: 应用样式和设置按钮图标

**Files:**
- Modify: `ui/main_window.py:346-414`

- [ ] **Step 1: 调用样式应用方法**

在 `_setup_ui` 方法末尾添加样式应用：

```python
# 在 right_layout 添加完所有内容后

self._apply_app_style()

# 设置按钮图标
if hasattr(self, '_play_ico_path') and self._play_ico_path:
    self.btn_start.setIcon(QIcon(self._play_ico_path))
    self.btn_start.setIconSize(QSize(20, 20))
if hasattr(self, '_stop_ico_dis_path') and self._stop_ico_dis_path:
    self.btn_stop.setIcon(QIcon(self._stop_ico_dis_path))
    self.btn_stop.setIconSize(QSize(18, 18))
```

- [ ] **Step 2: 验证样式应用**

运行程序，检查样式是否正确应用：

```bash
python main.py
```

预期结果：所有控件样式正确，按钮图标显示正常

- [ ] **Step 3: 提交样式应用**

```bash
git add ui/main_window.py
git commit -m "refactor: 应用样式和设置按钮图标"
```

---

### Task 8: 优化间距和比例

**Files:**
- Modify: `ui/styles.py`

- [ ] **Step 1: 调整全局间距**

修改 `ui/styles.py` 中的样式，调整间距：

```python
# 在 build_stylesheet 函数中，调整卡片样式

QFrame#CardFrame {{
    background: {c['card']};
    border: 1px solid {c['border']};
    border-radius: 10px;  # 增加圆角
}}
```

- [ ] **Step 2: 调整按钮样式**

调整按钮样式，使其更符合设计规范：

```python
# 在 build_stylesheet 函数中，调整按钮样式

QPushButton {{
    background: {c['card2']};
    color: {c['text']};
    border: 2px solid {c['border']};
    border-radius: 8px;  # 增加圆角
    min-height: 36px;  # 增加高度
    max-height: 36px;
    padding: 0px 12px;
}}
```

- [ ] **Step 3: 验证样式调整**

运行程序，检查样式调整效果：

```bash
python main.py
```

预期结果：间距更协调，比例更合理

- [ ] **Step 4: 提交样式优化**

```bash
git add ui/styles.py
git commit -m "refactor: 优化间距和比例样式"
```

---

### Task 9: 测试和验证

**Files:**
- Test: `ui/main_window.py`

- [ ] **Step 1: 测试窗口缩放**

测试窗口在不同尺寸下的表现：

1. 启动程序
2. 调整窗口大小到最小尺寸（800x600）
3. 调整窗口大小到较大尺寸（1200x800）
4. 检查左右区域是否按比例调整

预期结果：窗口缩放时，左右区域按比例调整，无布局错乱

- [ ] **Step 2: 测试滚动功能**

测试左侧滚动区域：

1. 启动程序
2. 调整窗口到较小高度
3. 滚动左侧区域
4. 检查所有设置项是否可见

预期结果：左侧区域可以滚动，所有设置项可见

- [ ] **Step 3: 测试功能完整性**

测试所有功能是否正常：

1. 选择Excel文件
2. 选择编号列
3. 选择源文件夹和目标文件夹
4. 设置匹配选项
5. 设置图片处理选项
6. 点击开始按钮

预期结果：所有功能正常工作，无异常

- [ ] **Step 4: 提交最终版本**

```bash
git add -A
git commit -m "refactor: 完成UI排版改进，采用经典左右分栏布局"
```

---

## 验收检查

### 功能验收
- [ ] 所有原有功能正常工作
- [ ] 新布局符合设计规范
- [ ] 交互体验流畅

### 视觉验收
- [ ] 布局比例协调（40%左侧，60%右侧）
- [ ] 间距一致（16px全局间距）
- [ ] 颜色方案统一

### 性能验收
- [ ] 窗口启动时间≤1秒
- [ ] 滚动流畅
- [ ] 内存占用合理

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-05-27-ui-layout-redesign.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**