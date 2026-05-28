# -*- coding: utf-8 -*-
"""SVG 图标生成和临时文件管理"""

import os
import tempfile
import atexit

from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QSize

from constants import darken_color

_TEMP_ICON_PATHS = []


def _write_temp_svg(svg_content, prefix):
    """将 SVG 渲染为 PNG 并写入临时文件，返回 QSS 可用的文件路径。"""
    try:
        renderer = QSvgRenderer(bytearray(svg_content, encoding="utf-8"))
        if not renderer.isValid():
            return ""
        size = renderer.defaultSize()
        if size.isEmpty():
            size = QSize(20, 20)
        image = QImage(size, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix=prefix)
        f.close()
        image.save(f.name, "PNG")
        _TEMP_ICON_PATHS.append(f.name)
        return f.name.replace("\\", "/")
    except Exception:
        return ""


def _cleanup_temp_icons():
    for p in _TEMP_ICON_PATHS:
        try:
            os.remove(p)
        except OSError:
            pass
    _TEMP_ICON_PATHS.clear()


atexit.register(_cleanup_temp_icons)
