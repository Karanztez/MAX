# -*- mode: python ; coding: utf-8 -*-

import os
import sys

_runtime = sys.base_prefix
_dlls = os.path.join(_runtime, 'DLLs')
_tcl = os.path.join(_runtime, 'tcl')

extra_binaries = []
for f in ['_tkinter.pyd', 'tcl86t.dll', 'tk86t.dll']:
    p = os.path.join(_dlls, f)
    if os.path.exists(p):
        extra_binaries.append((p, '.'))

extra_datas = []
if os.path.exists(os.path.abspath('skills')):
    extra_datas.append((os.path.abspath('skills'), 'skills'))
if os.path.exists(os.path.abspath('icon.ico')):
    extra_datas.append((os.path.abspath('icon.ico'), '.'))
if os.path.exists(os.path.abspath('src/assets')):
    extra_datas.append((os.path.abspath('src/assets'), os.path.join('src', 'assets')))

for t in ['tcl8.6', 'tk8.6']:
    p = os.path.join(_tcl, t)
    if os.path.exists(p):
        target = '_tcl_data' if t.startswith('tcl') else '_tk_data'
        extra_datas.append((p, target))

a = Analysis(
    ['main.py'],
    pathex=['.', 'src'],
    binaries=extra_binaries,
    datas=extra_datas,
    hiddenimports=[
        'tkinter', '_tkinter', 'PIL', 'PIL._imagingtk', 'PIL.ImageTk',
        'PIL.ImageGrab', 'PIL.ImageDraw', 'pystray', 'pystray._win32',
        'mcp_manager', 'src', 'src.cli', 'src.core', 'src.core.ai_client',
        'src.core.mcp_manager', 'src.core.provider_profiles',
        'src.core.settings_store', 'src.core.skill_manager', 'src.core.updater',
        'src.ui', 'src.ui.themes', 'src.ui.clipboard',
        'src.ui.widgets', 'src.ui.dialogs', 'src.ui.dialogs.update_dialog',
        'src.ui.dialogs.health_dialog', 'src.ui.dialogs.crop_dialog',
        'src.ui.dialogs.mcp_dialog', 'src.ui.dialogs.settings_dialog',
        'src.ui.capture', 'src.ui.chat_tab', 'src.ui.main_window'
    ],
    hookspath=['hooks'] if os.path.exists('hooks') else [],
    hooksconfig={},
    runtime_hooks=['hooks/pyi_rth_tkinter_manual.py'] if os.path.exists('hooks/pyi_rth_tkinter_manual.py') else [],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MAX',
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
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
