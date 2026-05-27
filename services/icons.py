# -*- coding: utf-8 -*-
"""SVG 图标生成和临时文件管理"""

import os
import tempfile
import atexit

from constants import darken_color

_TEMP_ICON_PATHS = []


def _write_temp_svg(svg_content, prefix):
    """将 SVG 内容写入临时文件，返回 QSS 可用的文件路径。"""
    try:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".svg", prefix=prefix)
        f.write(svg_content.encode("utf-8"))
        f.close()
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
