# 文件批量匹配复制工具

一个基于 PySide6 的桌面应用程序，用于根据 Excel 中的 ID 列表批量匹配并复制文件。特别适用于需要根据编号批量处理图片等文件的场景。

## 功能特性

- **Excel 集成**：读取 Excel 文件中的 ID 列，支持 `.xlsx` 和 `.xls` 格式
- **智能文件匹配**：根据 ID 前缀匹配源目录中的文件
- **批量复制**：一键将匹配的文件复制到指定目标目录
- **图片处理**：支持图片尺寸调整、格式转换（WebP、AVIF 等现代格式）
- **递归搜索**：可选择是否递归搜索子目录
- **实时日志**：显示详细的匹配和复制进度
- **深色/浅色主题**：自动适应系统主题

## 技术栈

- **Python 3.13+**
- **PySide6**：Qt for Python，构建跨平台 GUI
- **pandas**：Excel 文件读取和数据处理
- **Pillow**：图片处理和格式转换

## 安装

### 从源码运行

1. 克隆仓库：
```bash
git clone https://github.com/SchrodingerBarbatos/file-batch-matcher.git
cd file-batch-matcher
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 运行程序：
```bash
python main.py
```

### 使用打包版本

从 [Releases](https://github.com/SchrodingerBarbatos/file-batch-matcher/releases) 页面下载最新的 `.exe` 文件，双击即可运行。

## 使用方法

1. **选择 Excel 文件**：点击浏览按钮选择包含 ID 列表的 Excel 文件
2. **选择 ID 列**：从下拉菜单中选择包含 ID 的列
3. **设置源目录**：选择需要匹配文件的源文件夹
4. **设置目标目录**：选择复制文件的目标文件夹
5. **配置选项**：
   - 文件扩展名过滤（如 `.jpg .png .webp`）
   - 是否递归搜索子目录
   - 图片处理选项（调整尺寸、格式转换等）
6. **开始匹配**：点击"开始"按钮执行批量匹配和复制

## 项目结构

```
file-batch-matcher/
├── main.py              # 应用入口
├── constants.py         # 全局常量配置
├── core/
│   └── engine.py        # 核心业务逻辑（Excel读取、文件匹配、图片处理）
├── ui/
│   ├── main_window.py   # 主窗口布局和信号连接
│   ├── widgets.py       # 自定义UI组件
│   ├── workers.py       # 后台工作线程
│   └── styles.py        # 主题和样式
├── services/
│   └── icons.py         # 图标资源管理
└── requirements.txt     # 依赖列表
```

## 构建可执行文件

使用 PyInstaller 打包：
```bash
pyinstaller 文件批量匹配复制工具.spec
```

或使用自动检测：
```bash
pyinstaller --onefile --windowed --name "文件批量匹配复制工具" main.py
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
