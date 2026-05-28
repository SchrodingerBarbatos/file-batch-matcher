# -*- coding: utf-8 -*-
"""QSS 样式 & 颜色常量"""

import sys

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from constants import (
    darken_color as _darken,
    RADIUS_CARD, RADIUS_INPUT, RADIUS_BUTTON, RADIUS_PRIMARY, RADIUS_SMALL,
    RADIUS_TAB, RADIUS_CHECKBOX,
    H_INPUT, H_BUTTON, H_PRIMARY_BTN,
)


def get_theme_colors():
    """根据系统调色板生成浅色/暗色可读配色。"""
    app = QApplication.instance()
    is_dark = False
    if app:
        is_dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    if sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            ) as key:
                is_dark = winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
        except Exception:
            pass
    if is_dark:
        return {
            'is_dark': True,
            'window': '#111827',
            'card': '#1F2937',
            'card2': '#263244',
            'border': '#374151',
            'text': '#F3F4F6',
            'muted': '#9CA3AF',
            'input': '#111827',
            'input_border': '#4B5563',
            'accent': '#22C55E',
            'accent_hover': '#16A34A',
            'green': '#22C55E',
            'green_hover': '#16A34A',
            'red': '#F87171',
            'red_hover': '#EF4444',
            'blue': '#60A5FA',
            'warning': '#FBBF24',
            'log': '#0B1220',
            'help': '#152219',
            'tip': '#2A2112',
            'tip_text': '#FBBF24',
            'tip_border': '#D97706',
            'disabled_card': '#161E2A',
            'disabled_border': '#374151',
            'shadow': QColor(0, 0, 0, 45),
            'stat_card_bg': '#1F2937',
        }
    return {
        'is_dark': False,
        'window': '#F6F8FB',
        'card': '#FFFFFF',
        'card2': '#F8FAFD',
        'border': '#E5E7EB',
        'text': '#111827',
        'muted': '#6B7280',
        'input': '#FFFFFF',
        'input_border': '#D1D5DB',
        'accent': '#16A34A',
        'accent_hover': '#15803D',
        'green': '#16A34A',
        'green_hover': '#15803D',
        'red': '#EF4444',
        'red_hover': '#DC2626',
        'blue': '#2563EB',
        'warning': '#F59E0B',
        'log': '#FFFFFF',
        'help': '#F4FBF5',
        'tip': '#FFF8E8',
        'tip_text': '#B45309',
        'tip_border': '#F5C16C',
        'disabled_card': '#F0F3F8',
        'disabled_border': '#D6DCE7',
        'shadow': QColor(15, 23, 42, int(255 * 0.06)),
        'stat_card_bg': '#FFFFFF',
    }


def build_stylesheet(c, checkbox_checked_css, checkbox_unchecked_css, arrow_ico):
    """根据主题颜色和图标路径生成完整 QSS 样式表。"""
    R = {
        'card': RADIUS_CARD,
        'input': RADIUS_INPUT,
        'btn': RADIUS_BUTTON,
        'primary': RADIUS_PRIMARY,
        'sm': RADIUS_SMALL,
        'tab': RADIUS_TAB,
        'cb': RADIUS_CHECKBOX,
    }
    return f"""
        QMainWindow, QWidget {{
            background: {c['window']};
            color: {c['text']};
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        }}
        QFrame#CardFrame {{
            background: {c['card']};
            border: none;
            border-radius: {R['card']}px;
        }}
        QLabel {{
            color: {c['text']};
            background: transparent;
        }}
        QLabel:disabled {{
            color: {c['muted']};
        }}
        QToolTip {{
            background: {c['card']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: {R['sm']}px;
            padding: 4px 8px;
        }}
        QLabel#appTitle {{
            font-size: 20px;
            font-weight: 700;
            color: {c['text']};
            background: transparent;
        }}
        QLabel#cardTitle {{
            font-size: 16px;
            font-weight: 700;
            color: {c['text']};
            background: transparent;
            padding: 0;
        }}
        QLabel#cardSubtitle {{
            font-size: 12px;
            color: {c['muted']};
            background: transparent;
            padding: 0;
        }}
        QLabel#hintLabel {{
            color: {c['muted']};
            font-size: 11px;
        }}
        QLabel#fieldLabel {{
            font-size: 13px;
            font-weight: 600;
            min-width: 70px;
        }}
        QLabel#stepNumber {{
            background: {c['green']};
            color: white;
            font-size: 13px;
            font-weight: 700;
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
            border-radius: 12px;
            qproperty-alignment: AlignCenter;
        }}
        QLabel#statusOk {{
            color: {c['green']};
            font-size: 11px;
            background: transparent;
        }}
        QLabel#statusWarn {{
            color: {c['warning']};
            font-size: 11px;
            background: transparent;
        }}
        QLabel#statusError {{
            color: {c['red']};
            font-size: 11px;
            background: transparent;
        }}
        QLabel#statusHint {{
            color: {c['muted']};
            font-size: 11px;
            background: transparent;
        }}
        QLineEdit {{
            background: #FFFFFF;
            color: {c['text']};
            border: 1px solid #D1D5DB;
            border-radius: {R['input']}px;
            min-height: {H_INPUT}px;
            max-height: {H_INPUT}px;
            padding: 0px 12px;
            font-size: 13px;
        }}
        QComboBox {{
            background: #FFFFFF;
            color: {c['text']};
            border: 1px solid #D1D5DB;
            border-radius: {R['input']}px;
            min-height: {H_INPUT}px;
            max-height: {H_INPUT}px;
            padding: 0px 25px 0px 12px;
            font-size: 13px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border-color: #22C55E;
            border-width: 2px;
            padding: 0px 11px;
            background: #FFFFFF;
        }}
        QLineEdit:hover, QComboBox:hover {{
            border-color: {c['accent']};
        }}
        QLineEdit:disabled, QComboBox:disabled {{
            color: #9CA3AF;
            background: #F3F4F6;
            border-color: #E5E7EB;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            right: 10px;
            width: 14px;
            border: none;
            background: transparent;
        }}
        QComboBox::down-arrow {{
            image: url({arrow_ico});
            width: 10px;
            height: 7px;
        }}
        QListView#roundComboView {{
            background: {c['input']};
            color: {c['text']};
            border: 1px solid {c['input_border']};
            border-radius: {R['input']}px;
            outline: none;
            padding: 4px;
        }}
        QListView#roundComboView::item {{
            min-height: 26px;
            margin: 2px 4px;
            padding: 2px 8px;
            border-radius: {R['sm']}px;
        }}
        QListView#roundComboView::item:selected {{
            background: {c['accent']};
            color: #FFFFFF;
        }}
        QPushButton {{
            background: {c['card2']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: {R['btn']}px;
            min-height: {H_BUTTON}px;
            max-height: {H_BUTTON}px;
            padding: 0px 14px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            border-color: {c['accent']};
            background: {c['input']};
        }}
        QPushButton:pressed {{
            background: {c['border']};
            border-color: {c['muted']};
        }}
        QPushButton:disabled {{
            color: {c['muted']};
            background: {c['card2']};
            border-color: {c['border']};
        }}
        QPushButton#startButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['green']}, stop:1 {_darken(c['green'], 0.88)});
            border-color: {c['green_hover']};
            color: white;
            font-size: 16px;
            font-weight: 700;
            min-height: {H_PRIMARY_BTN}px;
            max-height: {H_PRIMARY_BTN}px;
            border-radius: {R['primary']}px;
            padding: 0px 20px;
        }}
        QPushButton#startButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {_darken(c['green'], 0.92)}, stop:1 {_darken(c['green'], 0.82)});
        }}
        QPushButton#startButton:pressed {{
            background: {_darken(c['green_hover'], 0.8)};
        }}
        QPushButton#startButton:disabled {{
            background: {c['card2']};
            border-color: {c['border']};
            color: {c['muted']};
        }}
        QPushButton#stopButton {{
            background: transparent;
            border: 1px solid {c['border']};
            color: {c['muted']};
            font-size: 13px;
            font-weight: 600;
            min-height: {H_PRIMARY_BTN}px;
            max-height: {H_PRIMARY_BTN}px;
            border-radius: {R['primary']}px;
            padding: 0px 14px;
        }}
        QPushButton#stopButton:hover {{
            background: {c['card2']};
            border-color: {c['red']};
            color: {c['red']};
        }}
        QPushButton#stopButton:disabled {{
            background: transparent;
            border-color: {c['border']};
            color: {c['muted']};
        }}
        QPushButton#logToolButton {{
            min-height: 28px;
            max-height: 28px;
            padding: 0px 10px;
            font-size: 11px;
            border-radius: 7px;
            border: 1px solid #D1D5DB;
            background: #FFFFFF;
            color: #6B7280;
        }}
        QPushButton#logToolButton:hover {{
            border: 1px solid #22C55E;
            background: #F0FDF4;
            color: #16A34A;
        }}
        QPushButton#logToolButton:pressed {{
            background: #DCFCE7;
        }}
        QPushButton#TabButton {{
            background: transparent;
            border: none;
            color: {c['muted']};
            font-size: 13px;
            font-weight: 600;
            min-height: 36px;
            max-height: 36px;
            padding: 0px 18px;
            border-radius: {R['tab']}px;
        }}
        QPushButton#TabButton:hover {{
            color: {c['text']};
            background: {c['card2']};
        }}
        QPushButton#TabButton:checked {{
            color: #16A34A;
            background: #EAF8EF;
            font-weight: 600;
        }}
        QPushButton#collapseHeader {{
            background: transparent;
            border: none;
            color: {c['text']};
            font-size: 13px;
            font-weight: 600;
            min-height: 36px;
            max-height: 36px;
            padding: 0px 4px;
            text-align: left;
        }}
        QPushButton#collapseHeader:hover {{
            color: {c['accent']};
            background: transparent;
            border: none;
        }}
        QTextEdit {{
            background: {c['log']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: {R['card']}px;
            padding: 10px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 12px;
            line-height: 1.5;
        }}
        QProgressBar {{
            background: {c['border']};
            color: {c['text']};
            border: none;
            border-radius: {R['sm']}px;
            min-height: 8px;
            max-height: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['green']}, stop:1 {_darken(c['green'], 0.85)});
            border-radius: {R['sm']}px;
        }}
        QCheckBox {{
            color: {c['text']};
            background: transparent;
            spacing: 8px;
            min-height: 28px;
            max-height: 28px;
            font-size: 13px;
        }}
        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border: none;
            border-radius: {R['cb']}px;
        }}
        QCheckBox::indicator:unchecked {{
            {checkbox_unchecked_css}
        }}
        QCheckBox::indicator:checked {{
            {checkbox_checked_css}
        }}
        QLineEdit#advancedInput {{
            background-color: #FFFFFF;
            border: 1px solid #94A3B8;
            border-radius: {R['input']}px;
            min-height: 36px;
            max-height: 36px;
            padding: 0px 12px;
            color: #111827;
            font-size: 13px;
        }}
        QLineEdit#advancedInput:hover {{
            border: 1px solid #64748B;
        }}
        QLineEdit#advancedInput:focus {{
            border: 2px solid #22C55E;
            padding: 0px 11px;
            background-color: #FFFFFF;
        }}
        QLineEdit#advancedInput:disabled {{
            background-color: #F3F4F6;
            border: 1px solid #D1D5DB;
            color: #9CA3AF;
        }}
        QComboBox#advancedCombo {{
            background-color: #FFFFFF;
            border: 1px solid #94A3B8;
            border-radius: {R['input']}px;
            min-height: 36px;
            max-height: 36px;
            padding-left: 12px;
            padding-right: 28px;
            color: #111827;
            font-size: 13px;
        }}
        QComboBox#advancedCombo:hover {{
            border: 1px solid #64748B;
        }}
        QComboBox#advancedCombo:focus {{
            border: 2px solid #22C55E;
            padding-left: 11px;
            background-color: #FFFFFF;
        }}
        QComboBox#advancedCombo:disabled {{
            background-color: #F3F4F6;
            border: 1px solid #D1D5DB;
            color: #9CA3AF;
        }}
        QComboBox#advancedCombo::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            right: 8px;
            width: 24px;
            border: none;
            background: transparent;
        }}
        QComboBox#advancedCombo::down-arrow {{
            image: url({arrow_ico});
            width: 10px;
            height: 7px;
        }}
        QFrame#advancedContentFrame {{
            background: #FAFBFC;
            border: none;
            border-radius: 12px;
        }}
        QFrame#logContentFrame {{
            background: #F6F8FB;
            border: none;
            border-radius: 10px;
        }}
        QTextEdit#logTextEdit {{
            background: transparent;
            border: none;
            border-radius: 10px;
            padding: 10px;
            font-family: Consolas, "Courier New", monospace;
            font-size: 12px;
            line-height: 1.5;
            color: {c['text']};
        }}
        QFrame#StatCard {{
            background: {c['stat_card_bg']};
            border: 1px solid {c['border']};
            border-radius: {R['card']}px;
        }}
        QFrame#currentFileBar {{
            background: {c['card2']};
            border: none;
            border-radius: {R['input']}px;
            min-height: 34px;
            max-height: 34px;
        }}
        QFrame#groupSeparator {{
            background: transparent;
            border: none;
        }}
        QFrame#advSep {{
            background: {c['border']};
            min-width: 1px;
            max-width: 1px;
        }}
        QFrame#advCardSeparator {{
            background: {c['border']};
            max-height: 1px;
            border: none;
        }}
        QFrame#OptionCard {{
            background: transparent;
            border: none;
            border-radius: {R['primary']}px;
        }}
        QLabel#optionCardTitle {{
            font-size: 14px;
            font-weight: 700;
            color: {c['text']};
            background: transparent;
            padding: 0;
        }}
        QLabel#optionCardSubtitle {{
            font-size: 12px;
            color: {c['muted']};
            background: transparent;
            padding: 0;
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 4px 2px 4px 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['input_border']};
            border-radius: {R['sm']}px;
            min-height: 28px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c['muted']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 2px 4px 2px 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c['input_border']};
            border-radius: {R['sm']}px;
            min-width: 28px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c['muted']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """
