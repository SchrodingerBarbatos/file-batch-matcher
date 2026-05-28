# -*- coding: utf-8 -*-
"""全局常量"""

# ---- 文件/格式 ----
DEFAULT_IMG_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.svg', '.avif'}


def darken_color(hex_color, factor=0.85):
    """将十六进制颜色按给定因子暗化，支持 8 位带 alpha 的颜色。"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(ch * 2 for ch in hex_color)
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r, g, b = max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor))
    result = f'#{r:02x}{g:02x}{b:02x}'
    if len(hex_color) == 8:
        result += hex_color[6:8]
    return result

# ---- 窗口尺寸（动态计算，以下为边界值） ----
WINDOW_MIN_W = 960
WINDOW_MIN_H = 640
WINDOW_MAX_W = 1440
WINDOW_MAX_H = 920
WINDOW_SCREEN_RATIO = 0.88

# ---- 布局比例 ----
LEFT_RATIO = 48
RIGHT_RATIO = 52
LEFT_RATIO_NARROW = 46
RIGHT_RATIO_NARROW = 54
BREAKPOINT_WIDE = 1280
UI_GAP = 16
UI_MARGIN = 20

# ---- 圆角系统 ----
RADIUS_CARD = 12
RADIUS_INPUT = 8
RADIUS_BUTTON = 8
RADIUS_PRIMARY = 10
RADIUS_SMALL = 6
RADIUS_TAB = 8
RADIUS_CHECKBOX = 5

# ---- 控件高度（紧凑档） ----
H_INPUT = 38
H_BUTTON = 36
H_PRIMARY_BTN = 44

# ---- UI 时序 (ms) ----
DEBOUNCE_MS = 200
SHIMMER_INTERVAL_MS = 40

# ---- 流光动画参数 ----
SHIMMER_STEP = 0.02
SHIMMER_BAND_WIDTH = 80

# ---- 日志 ----
LOG_MAX_BLOCK_COUNT = 2000
