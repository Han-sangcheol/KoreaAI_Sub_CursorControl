# -*- mode: python ; coding: utf-8 -*-
"""
[파일 기능]
- PyInstaller 빌드 정의 (Windows)
- 산출물: dist/cursor_auto_input/ 폴더 — 통째로 복사·압축하면 포터블로 사용 가능
- console=True: 실행 시 콘솔(CMD) 창 표시 (print/input 사용)
"""
# pyinstaller cursor_auto_input.spec

block_cipher = None

hiddenimports = [
    "pywinauto",
    "pywinauto.keyboard",
    "pyperclip",
    "win32api",
    "win32gui",
    "win32con",
    "win32clipboard",
    "win32process",
    "pythoncom",
    "pywintypes",
    "comtypes",
    "comtypes.client",
]

a = Analysis(
    ["cursor_auto_input.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="cursor_auto_input",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="cursor_auto_input",
)
