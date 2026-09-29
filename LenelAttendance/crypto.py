"""
Windows DPAPI wrapper for encrypting sensitive settings at rest.

Encrypted values are stored as  dpapi:<base64>  so we can detect legacy
plain-text values and upgrade them transparently on first write.

If decryption fails (wrong machine / wrong Windows user), returns '' rather
than crashing — the user will simply need to re-enter the credential.
"""

import sys
import ctypes
import base64

_MARKER = 'dpapi:'

if sys.platform == 'win32':
    _crypt32  = ctypes.WinDLL('Crypt32.dll')
    _kernel32 = ctypes.WinDLL('Kernel32.dll')
    _kernel32.LocalFree.restype  = ctypes.c_void_p
    _kernel32.LocalFree.argtypes = [ctypes.c_void_p]

    class _BLOB(ctypes.Structure):
        _fields_ = [('cbData', ctypes.c_ulong),
                    ('pbData', ctypes.POINTER(ctypes.c_ubyte))]

    # CRYPTPROTECT_LOCAL_MACHINE: any account on this machine can decrypt,
    # including the LocalSystem service account.  Still machine-bound — moving
    # the DB to another machine requires re-entering credentials.
    _MACHINE_FLAG = 0x4

    def encrypt(plaintext: str) -> str:
        """Encrypt a string with machine-level DPAPI. Returns 'dpapi:<base64>'."""
        if not plaintext:
            return ''
        data = plaintext.encode('utf-8')
        buf  = (ctypes.c_ubyte * len(data))(*data)
        inp  = _BLOB(len(data), buf)
        out  = _BLOB()
        if _crypt32.CryptProtectData(
                ctypes.byref(inp), None, None, None, None, _MACHINE_FLAG,
                ctypes.byref(out)):
            raw = bytes(
                ctypes.cast(out.pbData,
                            ctypes.POINTER(ctypes.c_ubyte * out.cbData)).contents)
            _kernel32.LocalFree(out.pbData)
            return _MARKER + base64.b64encode(raw).decode()
        return plaintext   # DPAPI unavailable — store plain as fallback

    def decrypt(value: str) -> str:
        """Decrypt a DPAPI value. Plain-text legacy values pass through."""
        if not value:
            return ''
        if not value.startswith(_MARKER):
            return value   # legacy plain-text — return as-is until next save
        data = base64.b64decode(value[len(_MARKER):])
        buf  = (ctypes.c_ubyte * len(data))(*data)
        inp  = _BLOB(len(data), buf)
        out  = _BLOB()
        if _crypt32.CryptUnprotectData(
                ctypes.byref(inp), None, None, None, None, 0,
                ctypes.byref(out)):
            raw = bytes(
                ctypes.cast(out.pbData,
                            ctypes.POINTER(ctypes.c_ubyte * out.cbData)).contents)
            _kernel32.LocalFree(out.pbData)
            return raw.decode('utf-8')
        return ''   # wrong machine or user — force re-entry

else:
    # Non-Windows (development only) — no-op passthrough
    def encrypt(plaintext: str) -> str:
        return plaintext

    def decrypt(value: str) -> str:
        return value if not value.startswith(_MARKER) else ''
