#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件批量匹配复制工具 - 入口文件"""

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def resource_path(relative_path: str) -> str:
    """兼容源码运行和 PyInstaller 打包后的资源路径"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def setup_windows_app_id():
    """设置 Windows 任务栏 AppUserModelID，确保任务栏图标正确显示"""
    if sys.platform == "win32":
        try:
            import ctypes
            myappid = "com.imagecopy.matcher.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"SetCurrentProcessExplicitAppUserModelID failed: {e}")


if __name__ == "__main__":
    # 必须在 QApplication 创建之前设置
    setup_windows_app_id()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # 加载图标
    icon_path = resource_path("app.ico")
    app_icon = QIcon(icon_path)

    if os.path.exists(icon_path) and not app_icon.isNull():
        app.setWindowIcon(app_icon)
    else:
        print(f"图标加载失败或不存在: {icon_path}")

    window = MainWindow()

    # 同时设置窗口图标
    if os.path.exists(icon_path) and not app_icon.isNull():
        window.setWindowIcon(app_icon)

    window.show()
    sys.exit(app.exec())
