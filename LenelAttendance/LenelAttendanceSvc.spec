# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import glob
from PyInstaller.utils.hooks import collect_all

datas = [('icon.ico', '.')]
binaries = []
hiddenimports = [
    'pyodbc',
    'win32serviceutil',
    'win32service',
    'win32event',
    'win32api',
    'win32con',
    'win32timezone',
    'servicemanager',
    'pywintypes',
]

tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Collect pywin32 binaries.
# pywin32 uses a .pth file to add win32/ and win32/lib/ to sys.path, so
# PyInstaller finds win32serviceutil.py etc. automatically via the regular
# import machinery. We only need to ensure the DLLs are bundled.
import importlib.util
_pywt = importlib.util.find_spec('pywintypes')
if _pywt and _pywt.origin:
    # pywintypes313.dll lives in pywin32_system32/ — bundle it to top-level
    _sys32 = os.path.dirname(_pywt.origin)
    for _f in glob.glob(os.path.join(_sys32, '*.dll')):
        binaries.append((_f, '.'))

a = Analysis(
    ['svc.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthook_pywin32.py'],
    excludes=['tkinter', 'pystray'],
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
    name='LenelAttendanceSvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
