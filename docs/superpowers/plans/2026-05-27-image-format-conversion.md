# 图片格式转换功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为文件批量匹配复制工具添加图片格式转换功能，支持将非标准图片格式自动转换为 JPEG 或 PNG。

**Architecture:** 在现有的 `process_thread` 流程中，复制/移动文件后调用新的 `convert_image_format` 函数。使用 PIL 的 `img.format` 检测真实格式，避免伪装扩展名。UI 上新增格式转换选项。

**Tech Stack:** Python, Tkinter, PIL/Pillow

---

## 文件结构

- **修改**: `D:\图片匹配复制\file_matcher_final_force_800.py`
  - 添加格式转换变量（约第 50 行）
  - 添加格式转换 UI 控件（约第 130 行）
  - 添加 `convert_image_format` 方法（约第 600 行）
  - 修改 `process_thread` 调用格式转换（约第 490 行）

---

### Task 1: 添加格式转换变量

**Files:**
- Modify: `D:\图片匹配复制\file_matcher_final_force_800.py:47-51`

- [ ] **Step 1: 添加格式转换变量**

在 `__init__` 方法中，图片处理变量后面添加格式转换变量：

```python
# 图片处理
self.enable_resize_var = tk.BooleanVar(value=False)
self.max_width_var = tk.StringVar(value="800")
self.max_height_var = tk.StringVar(value="800")
self.max_size_var = tk.StringVar(value="5000000")

# 格式转换
self.enable_convert_var = tk.BooleanVar(value=False)
self.target_format_var = tk.StringVar(value="JPEG")
```

- [ ] **Step 2: 验证变量添加成功**

运行程序确认无语法错误：
```bash
cd "D:\图片匹配复制" && python -c "import file_matcher_final_force_800; print('OK')"
```

---

### Task 2: 添加格式转换 UI 控件

**Files:**
- Modify: `D:\图片匹配复制\file_matcher_final_force_800.py:113-130`

- [ ] **Step 1: 添加格式转换 UI**

在 `img_frame` 中，在尺寸处理控件后面添加格式转换控件：

```python
img_frame = ttk.LabelFrame(option_frame, text="图片处理", padding="5")
img_frame.pack(fill=tk.X, pady=5)

ttk.Checkbutton(
    img_frame,
    text="启用图片尺寸/大小处理",
    variable=self.enable_resize_var
).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2, columnspan=6)

ttk.Label(img_frame, text="宽:").grid(row=1, column=0, padx=5)
ttk.Entry(img_frame, textvariable=self.max_width_var, width=8).grid(row=1, column=1)

ttk.Label(img_frame, text="高:").grid(row=1, column=2, padx=5)
ttk.Entry(img_frame, textvariable=self.max_height_var, width=8).grid(row=1, column=3)

ttk.Label(img_frame, text="最大大小(bytes):").grid(row=1, column=4, padx=5)
ttk.Entry(img_frame, textvariable=self.max_size_var, width=12).grid(row=1, column=5)

# 格式转换
ttk.Checkbutton(
    img_frame,
    text="启用格式转换",
    variable=self.enable_convert_var
).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2, columnspan=2)

ttk.Label(img_frame, text="目标格式:").grid(row=2, column=2, padx=5)
format_combo = ttk.Combobox(img_frame, textvariable=self.target_format_var, values=["JPEG", "PNG"], width=8, state="readonly")
format_combo.grid(row=2, column=3, padx=5)
format_combo.current(0)
```

- [ ] **Step 2: 验证 UI 显示正确**

运行程序，确认格式转换控件显示正常：
```bash
cd "D:\图片匹配复制" && python file_matcher_final_force_800.py
```

---

### Task 3: 实现 convert_image_format 方法

**Files:**
- Modify: `D:\图片匹配复制\file_matcher_final_force_800.py` (在 `process_image` 方法后面添加)

- [ ] **Step 1: 添加 convert_image_format 方法**

在 `process_image` 方法后面添加新方法：

```python
def convert_image_format(self, image_path, target_format):
    """
    转换图片格式：
    1. 使用 img.format 获取真实格式，避免伪装扩展名
    2. JPEG/PNG 保持不变
    3. 其他格式转换为目标格式
    """
    tmp_path = None
    try:
        with Image.open(image_path) as img:
            real_format = img.format  # 获取真实格式

            # 标准格式不转换
            if real_format in ['JPEG', 'PNG']:
                self.log(f"[格式跳过] 已是标准格式: {os.path.basename(image_path)} ({real_format})")
                return image_path

            # 非标准格式转换
            ext = os.path.splitext(image_path)[1].lower()
            base_name = os.path.splitext(image_path)[0]

            if target_format == 'JPEG':
                new_ext = '.jpg'
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
            else:  # PNG
                new_ext = '.png'

            new_path = base_name + new_ext
            tmp_path = new_path + ".tmp" + new_ext

            if target_format == 'JPEG':
                img.save(tmp_path, quality=95, optimize=True)
            else:
                img.save(tmp_path, optimize=True)

            if os.path.getsize(tmp_path) > 0:
                os.replace(tmp_path, new_path)
                # 删除原文件（如果扩展名不同）
                if image_path != new_path and os.path.exists(image_path):
                    os.remove(image_path)
                self.log(f"[格式转换] {os.path.basename(image_path)} ({real_format}) -> {os.path.basename(new_path)}")
                return new_path
            else:
                raise RuntimeError("转换后文件大小为 0")

    except Exception as e:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        self.log(f"[错误] 格式转换失败 {os.path.basename(image_path)}: {e}")
        return image_path
```

- [ ] **Step 2: 验证方法语法正确**

运行程序确认无语法错误：
```bash
cd "D:\图片匹配复制" && python -c "import file_matcher_final_force_800; print('OK')"
```

---

### Task 4: 修改 process_thread 调用格式转换

**Files:**
- Modify: `D:\图片匹配复制\file_matcher_final_force_800.py:482-498`

- [ ] **Step 1: 修改 process_thread 中的文件处理逻辑**

在复制/移动文件后，图片处理前添加格式转换调用：

```python
try:
    if move_mode:
        shutil.move(src_path, dst_path)
        self.log(f"[移动] {filename}")
    else:
        shutil.copy2(src_path, dst_path)
        self.log(f"[复制] {filename}")

    # 格式转换（如果启用）
    if self.enable_convert_var.get():
        ext = os.path.splitext(dst_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.avif']:
            dst_path = self.convert_image_format(dst_path, self.target_format_var.get())

    # 图片尺寸/大小处理（如果启用）
    if self.enable_resize_var.get():
        ext = os.path.splitext(dst_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            self.process_image(dst_path)

    success += 1
except Exception as e:
    self.log(f"[错误] 处理 {filename} 失败: {e}")
    errors += 1
```

- [ ] **Step 2: 验证修改正确**

运行程序确认无语法错误：
```bash
cd "D:\图片匹配复制" && python -c "import file_matcher_final_force_800; print('OK')"
```

---

### Task 5: 测试完整功能

- [ ] **Step 1: 准备测试文件**

创建测试目录和测试图片：
```bash
mkdir -p "D:\图片匹配复制\test_input"
mkdir -p "D:\图片匹配复制\test_output"
```

使用 Python 创建测试图片：
```python
from PIL import Image
import os

test_dir = r"D:\图片匹配复制\test_input"

# 创建 WebP 测试图片
img = Image.new('RGB', (100, 100), color='red')
img.save(os.path.join(test_dir, "test_webp.webp"), 'WEBP')

# 创建 BMP 测试图片
img.save(os.path.join(test_dir, "test_bmp.bmp"), 'BMP')

# 创建伪装成 JPEG 的 WebP（扩展名是 .jpg 但实际是 WebP）
img.save(os.path.join(test_dir, "fake_jpg.jpg"), 'WEBP')

print("测试图片创建完成")
```

- [ ] **Step 2: 运行程序测试**

1. 启动程序：`python file_matcher_final_force_800.py`
2. 配置：
   - Excel 文件：选择一个包含编号的 Excel
   - 源文件夹：`D:\图片匹配复制\test_input`
   - 目标文件夹：`D:\图片匹配复制\test_output`
3. 勾选「启用格式转换」
4. 选择目标格式为「JPEG」
5. 点击「开始匹配并复制」

- [ ] **Step 3: 验证转换结果**

检查目标文件夹：
- `test_webp.webp` 应转换为 `test_webp.jpg`
- `test_bmp.bmp` 应转换为 `test_bmp.jpg`
- `fake_jpg.jpg` 应检测为 WebP 并转换为 `fake_jpg.jpg`（真实格式检测）

- [ ] **Step 4: 测试 PNG 目标格式**

1. 清空目标文件夹
2. 选择目标格式为「PNG」
3. 重新运行
4. 验证所有非标准格式都转换为 .png

---

### Task 6: 清理测试文件

- [ ] **Step 1: 删除测试目录**

```bash
rm -rf "D:\图片匹配复制\test_input"
rm -rf "D:\图片匹配复制\test_output"
```

---

## 验证清单

- [ ] 格式转换变量正确添加
- [ ] UI 控件正常显示
- [ ] `convert_image_format` 方法语法正确
- [ ] `process_thread` 正确调用格式转换
- [ ] WebP/BMP/GIF/TIFF/AVIF 能正确转换为 JPEG
- [ ] WebP/BMP/GIF/TIFF/AVIF 能正确转换为 PNG
- [ ] JPEG/PNG 文件保持不变
- [ ] 伪装扩展名的文件能被正确检测
- [ ] 转换失败时不影响后续文件处理
