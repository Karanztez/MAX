# -*- mode: python ; coding: utf-8 -*-

import os
import sys

_runtime = sys.base_prefix
_dlls = os.path.join(_runtime, 'DLLs')
_tcl = os.path.join(_runtime, 'tcl')


a = Analysis(
    ['main.py'],
    pathex=['.', 'src'],
    binaries=[
        (os.path.join(_dlls, '_tkinter.pyd'), '.'),
        (os.path.join(_dlls, 'tcl86t.dll'), '.'),
        (os.path.join(_dlls, 'tk86t.dll'), '.'),
    ],
    datas=[
        (os.path.join(_tcl, 'tcl8.6'), '_tcl_data'),
        (os.path.join(_tcl, 'tk8.6'), '_tk_data'),
        (os.path.abspath('skills'), 'skills'),
        (os.path.abspath('src/assets'), os.path.join('src', 'assets')),
        (os.path.abspath('icon.ico'), '.'),
    ],
    hiddenimports=['tkinter', '_tkinter', 'PIL', 'PIL._imagingtk', 'PIL.ImageTk',
                   'PIL.ImageGrab', 'PIL.ImageDraw', 'pystray', 'pystray._win32',
                   'mcp_manager', 'src', 'src.core', 'src.core.ai_client',
                   'src.core.mcp_manager', 'src.core.provider_profiles',
                   'src.core.settings_store', 'src.core.skill_manager', 'src.core.updater',
                   'src.ui', 'src.ui.themes', 'src.ui.clipboard',
                   'src.ui.widgets', 'src.ui.dialogs', 'src.ui.dialogs.update_dialog', 'src.ui.capture',
                   'src.ui.chat_tab', 'src.ui.main_window'],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['hooks/pyi_rth_tkinter_manual.py'],
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
    name='MaxPlusAI',
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
    icon='icon.ico',
)
