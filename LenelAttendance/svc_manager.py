"""
Service management helpers for the Settings GUI.
Uses sc.exe (Windows built-in) — no pywin32 dependency needed here.
"""
import subprocess
import sys
import os
import ctypes
from pathlib import Path

SVC_NAME = "LenelAttendanceSvc"


# ── Internal helpers ───────────────────────────────────────────────────────────

def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _svc_exe() -> str | None:
    """Path to LenelAttendanceSvc.exe when frozen; None in dev mode."""
    if getattr(sys, 'frozen', False):
        p = Path(sys.executable).parent / "LenelAttendanceSvc.exe"
        return str(p) if p.exists() else None
    return None


def _run(*args, timeout=15):
    r = subprocess.run(
        list(args), capture_output=True, text=True, timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return r.returncode == 0, (r.stdout + r.stderr).strip()


# ── Status queries (no admin required) ────────────────────────────────────────

def get_status() -> str:
    """Returns 'running', 'stopped', or 'not_installed'."""
    ok, out = _run('sc', 'query', SVC_NAME)
    if not ok:
        return 'not_installed'
    if 'RUNNING' in out:
        return 'running'
    if 'STOPPED' in out or 'PAUSED' in out:
        return 'stopped'
    return 'not_installed'


def is_installed() -> bool:
    return get_status() != 'not_installed'


def is_running() -> bool:
    return get_status() == 'running'


# ── Service lifecycle (admin required for install/uninstall) ───────────────────

def install():
    """Install the Windows service. Requires admin rights."""
    if not _is_admin():
        return False, (
            "Administrator rights required.\n\n"
            "Close this app, right-click the exe and choose "
            "'Run as administrator', then try again."
        )
    migrate_to_machine_dpapi()
    exe = _svc_exe()
    if exe:
        return _run(exe, 'install')
    # Dev mode: use python svc.py
    svc_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'svc.py')
    return _run(sys.executable, svc_script, 'install')


def uninstall():
    """Uninstall the Windows service. Requires admin rights."""
    if not _is_admin():
        return False, (
            "Administrator rights required.\n\n"
            "Close this app, right-click the exe and choose "
            "'Run as administrator', then try again."
        )
    stop()   # stop first if running
    exe = _svc_exe()
    if exe:
        return _run(exe, 'remove')
    svc_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'svc.py')
    return _run(sys.executable, svc_script, 'remove')


def start():
    """Start the service (no admin needed if service allows it)."""
    return _run('sc', 'start', SVC_NAME)


def stop():
    """Stop the service."""
    return _run('sc', 'stop', SVC_NAME)


# ── DPAPI credential migration ─────────────────────────────────────────────────

def migrate_to_machine_dpapi():
    """
    Re-encrypt DB and SMTP passwords with machine-level DPAPI so the service
    (LocalSystem account) can decrypt them.

    Must be called from the GUI process (user context) — it reads the current
    user-level DPAPI blobs and writes them back with the machine-level flag.
    Silent no-op if values are already machine-level or empty.
    """
    try:
        import config
        migrated = []
        for key in list(config._ENCRYPTED_KEYS):
            val = config.get_setting(key, '')
            if val:
                config.set_setting(key, val)   # read user-level → write machine-level
                migrated.append(key)
        if migrated:
            config.log_activity(
                f"Credentials re-encrypted for service access: {', '.join(migrated)}",
                "INFO"
            )
    except Exception as exc:
        try:
            import config as _c
            _c.log_activity(f"DPAPI migration warning: {exc}", "ERROR")
        except Exception:
            pass
