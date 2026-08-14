# -*- mode: python ; coding: utf-8 -*-
# PyInstaller macOS 打包配置 — 文件批量匹配复制工具
# 产出 dist/文件批量匹配复制工具.app（onedir + windowed）

import os

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='文件批量匹配复制工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    name='文件批量匹配复制工具',
)

_icon = 'app.icns' if os.path.exists('app.icns') else None
app = BUNDLE(
    coll,
    name='文件批量匹配复制工具.app',
    icon=_icon,
    bundle_identifier='com.imagecopy.matcher',
)
