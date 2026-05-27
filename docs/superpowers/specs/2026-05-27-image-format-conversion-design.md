# 图片格式转换功能设计

## 概述

为文件批量匹配复制工具添加图片格式转换功能，支持将非标准图片格式（WebP、AVIF、BMP、GIF、TIFF）自动转换为 JPEG 或 PNG。

## 需求

### 支持的输入格式
- 标准格式：JPG、JPEG、PNG
- 非标准格式：BMP、GIF、TIFF、WebP、AVIF

### 转换规则
- **标准格式保持不变**：JPEG 和 PNG 文件保持原格式，不会互相转换
- **非标准格式转换**：WebP、AVIF、BMP、GIF、TIFF 根据用户选择转换为 JPEG 或 PNG
- **真实格式检测**：使用 PIL 的 `img.format` 获取真实格式，避免伪装成 jpg/jpeg/png 的其他格式

### 用户选择
- 界面上新增「启用格式转换」复选框
- 下拉框选择目标格式（JPEG / PNG），默认 JPEG

## 架构设计

### 实现位置
在 `process_thread` 方法中，复制/移动文件后调用新的 `convert_image_format` 函数。

执行顺序：
1. 复制/移动文件
2. 格式转换（如果启用）
3. 尺寸/大小处理（如果启用）

### 新增函数

#### `convert_image_format(self, image_path, target_format)`
- **输入**：图片路径、目标格式（'JPEG' 或 'PNG'）
- **输出**：转换后的文件路径（如果转换了），或原路径（如果未转换）
- **逻辑**：
  1. 使用 `Image.open()` 打开图片
  2. 读取 `img.format` 获取真实格式
  3. 如果是标准格式（JPEG/PNG），直接返回原路径
  4. 如果是非标准格式，根据目标格式转换并保存为新文件
  5. 删除原文件，返回新路径

### UI 变更

在「图片处理」区域（`img_frame`）新增：
- 第 2 行：复选框「启用格式转换」+ 下拉框（JPEG/PNG）

### 代码修改点

1. **新增变量**：
   - `self.enable_convert_var`：是否启用格式转换
   - `self.target_format_var`：目标格式（'JPEG' 或 'PNG'）

2. **修改 `setup_ui`**：在 `img_frame` 中添加格式转换控件

3. **新增 `convert_image_format` 方法**：实现格式转换逻辑

4. **修改 `process_thread`**：在复制/移动后调用格式转换

## 错误处理

- 转换失败时记录日志，不影响后续文件处理
- 临时文件写入成功后再替换原文件，避免 0KB 问题
- AVIF 格式可能需要额外依赖（如 pillow-avif-plugin），在缺少时给出提示

## 测试场景

1. WebP 文件转 JPEG
2. AVIF 文件转 PNG
3. BMP/GIF/TIFF 文件转换
4. JPEG/PNG 文件保持不变
5. 伪装成 JPEG 的 WebP 文件（真实格式检测）
