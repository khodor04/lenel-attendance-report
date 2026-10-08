# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

import glob as _glob, os as _os
_sys32 = r'C:\Windows\System32'
_vc_dlls = ['vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_threads.dll',
            'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
            'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll']

datas = [('icon.ico', '.')]
binaries = [(_os.path.join(_sys32, dll), '.') for dll in _vc_dlls
            if _os.path.exists(_os.path.join(_sys32, dll))]
hiddenimports = ['pyodbc', 'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw']
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['LenelAttendance.pyw'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='LenelAttendance',
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
    icon=['icon.ico'],
)
