# -*- coding: utf-8 -*-
"""全局常量"""

# ---- 文件/格式 ----
DEFAULT_IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.svg', '.avif'}


def darken_color(hex_color, factor=0.85):
    """将十六进制颜色按给定因子暗化。"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(ch * 2 for ch in hex_color)
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor))
    return f'#{r:02x}{g:02x}{b:02x}'

# ---- UI 时序 (ms) ----
DEBOUNCE_MS = 200
SHIMMER_INTERVAL_MS = 40

# ---- 流光动画参数 ----
SHIMMER_STEP = 0.02
SHIMMER_BAND_WIDTH = 80

# ---- 日志 ----
LOG_MAX_BLOCK_COUNT = 2000
