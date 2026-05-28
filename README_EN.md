# File Batch Matcher

A PySide6-based desktop application for batch matching and copying files based on ID lists from Excel spreadsheets. Particularly useful for scenarios requiring bulk file processing based on numeric identifiers.

## Features

- **Excel Integration**: Read ID columns from Excel files, supporting `.xlsx` and `.xls` formats
- **Smart File Matching**: Match files in source directory based on ID prefixes
- **Batch Copy**: One-click copy matched files to specified target directory
- **Image Processing**: Support image resizing, format conversion (WebP, AVIF, and other modern formats)
- **Recursive Search**: Option to recursively search subdirectories
- **Real-time Logging**: Display detailed matching and copying progress
- **Dark/Light Theme**: Automatically adapts to system theme

## Tech Stack

- **Python 3.13+**
- **PySide6**: Qt for Python, building cross-platform GUI
- **pandas**: Excel file reading and data processing
- **Pillow**: Image processing and format conversion

## Installation

### Run from Source

1. Clone the repository:
```bash
git clone https://github.com/SchrodingerBarbatos/file-batch-matcher.git
cd file-batch-matcher
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

### Use Packaged Version

Download the latest `.exe` file from the [Releases](https://github.com/SchrodingerBarbatos/file-batch-matcher/releases) page and double-click to run.

## Usage

1. **Select Excel File**: Click the browse button to select an Excel file containing the ID list
2. **Select ID Column**: Choose the column containing IDs from the dropdown menu
3. **Set Source Directory**: Select the source folder containing files to match
4. **Set Target Directory**: Select the target folder for copied files
5. **Configure Options**:
   - File extension filter (e.g., `.jpg .png .webp`)
   - Whether to recursively search subdirectories
   - Image processing options (resize, format conversion, etc.)
6. **Start Matching**: Click the "Start" button to execute batch matching and copying

## Project Structure

```
file-batch-matcher/
├── main.py              # Application entry point
├── constants.py         # Global configuration constants
├── core/
│   └── engine.py        # Core business logic (Excel reading, file matching, image processing)
├── ui/
│   ├── main_window.py   # Main window layout and signal connections
│   ├── widgets.py       # Custom UI components
│   ├── workers.py       # Background worker threads
│   └── styles.py        # Themes and styles
├── services/
│   └── icons.py         # Icon resource management
└── requirements.txt     # Dependencies list
```

## Build Executable

Package with PyInstaller:
```bash
pyinstaller 文件批量匹配复制工具.spec
```

Or use auto-detection:
```bash
pyinstaller --onefile --windowed --name "FileBatchMatcher" main.py
```

## License

MIT License

## Contributing

Issues and Pull Requests are welcome!
