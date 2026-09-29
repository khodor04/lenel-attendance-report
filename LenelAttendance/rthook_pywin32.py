"""
Runtime hook — runs before svc.py starts.
Adds the frozen-exe extraction directory to Windows' DLL search path so that
pywintypes313.dll (bundled alongside the EXE) is found when win32api.pyd,
win32service.pyd, servicemanager.pyd etc. try to load it.
"""
import sys
import os

if hasattr(sys, '_MEIPASS'):
    try:
        os.add_dll_directory(sys._MEIPASS)
    except Exception:
        pass
