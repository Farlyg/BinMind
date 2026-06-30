# -*- mode: python ; coding: utf-8 -*-
# Build a single-file BinMind.exe:  pyinstaller --noconfirm --clean BinMind.spec
from PyInstaller.utils.hooks import collect_submodules

datas = [
    ("binmind/templates", "binmind/templates"),
    ("binmind/static", "binmind/static"),
]

hiddenimports = collect_submodules("webview") + [
    "binmind",
    "binmind.server",
    "binmind.assistant",
    "binmind.config",
    "binmind.paths",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BinMind",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="BinMind.ico",
)
