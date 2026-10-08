import tkinter as tk
from tkinter import ttk
import sys
import os
import threading
import ctypes

# Python 3.13 regression: Variable made unhashable, breaking widget cleanup
tk.Variable.__hash__ = id

# Ensure working directory = app directory so lenel_app.db resolves correctly,
# whether launched by the user, Task Scheduler, or as a frozen exe.
if getattr(sys, 'frozen', False):
    _APP_DIR = os.path.dirname(sys.executable)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(_APP_DIR)
sys.path.insert(0, _APP_DIR)

import config
import scheduler
from tabs.dashboard import DashboardTab
from tabs.generate import GenerateTab
from tabs.profiles import ProfilesTab
from tabs.settings import SettingsTab
from tabs.logs import LogsTab

try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_AVAILABLE = True
except ImportError:
    _TRAY_AVAILABLE = False

APP_NAME = "Lenel Attendance Report Manager"
VERSION  = "2.0"

NAV_ITEMS = [
    ("Dashboard",      "dashboard"),
    ("Generate Report","generate"),
    ("Report Profiles","profiles"),
    ("Settings",       "settings"),
    ("Activity Log",   "logs"),
]

NAV_BG      = "#1F3864"
NAV_FG      = "#FFFFFF"
NAV_HOVER   = "#2E5090"
NAV_ACTIVE  = "#3A6BC4"
CONTENT_BG  = "#F5F7FA"


def _make_tray_image():
    size = 64
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size - 1, size - 1], fill=(31, 56, 100, 255))
    # Letter L drawn with rectangles (no font dependency)
    draw.rectangle([18, 14, 27, 50], fill='white')  # vertical bar
    draw.rectangle([18, 41, 46, 50], fill='white')  # horizontal bar
    return img


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=NAV_BG)

        self._tray = None

        config.initialize_db()
        self._setup_style()
        self._set_window_icon()
        self._build_ui()
        self._start_scheduler()
        self._setup_tray()
        self._show_tab("dashboard")

    # ── Window icon ───────────────────────────────────────────────────────────
    def _set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller extracts bundled data files to sys._MEIPASS
                ico = os.path.join(sys._MEIPASS, 'icon.ico')
            else:
                ico = os.path.join(_APP_DIR, 'icon.ico')
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:
            pass   # non-critical

    # ── System tray ───────────────────────────────────────────────────────────
    def _setup_tray(self):
        if not _TRAY_AVAILABLE:
            return
        try:
            img  = _make_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem('Open Lenel Attendance', self._tray_open, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Exit', self._tray_exit),
            )
            self._tray = pystray.Icon('LenelAttendance', img, APP_NAME, menu)
            threading.Thread(target=self._tray.run, daemon=True).start()
        except Exception as e:
            self._tray = None
            print(f"Tray unavailable: {e}")

    def _tray_open(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def _tray_exit(self, icon=None, item=None):
        if self._tray:
            self._tray.stop()
        scheduler.stop()
        self.after(0, self.destroy)

    # ── Styles ────────────────────────────────────────────────────────────────
    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('vista')
        except Exception:
            pass

        style.configure('TFrame',        background=CONTENT_BG)
        style.configure('TLabel',        background=CONTENT_BG, font=('Segoe UI', 10))
        style.configure('TButton',       font=('Segoe UI', 9), padding=6)
        style.configure('Accent.TButton',font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure('TEntry',        font=('Segoe UI', 10), padding=4)
        style.configure('TCombobox',     font=('Segoe UI', 10))
        style.configure('TCheckbutton',  background=CONTENT_BG, font=('Segoe UI', 9))
        style.configure('TLabelframe',   background=CONTENT_BG, font=('Segoe UI', 9, 'bold'))
        style.configure('TLabelframe.Label', background=CONTENT_BG,
                        font=('Segoe UI', 9, 'bold'), foreground='#1F3864')
        style.configure('TNotebook',     background=CONTENT_BG)
        style.configure('TNotebook.Tab', font=('Segoe UI', 9), padding=(10, 4))
        style.configure('Treeview',      font=('Segoe UI', 9), rowheight=22)
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))
        style.configure('TSeparator',    background='#DDDDDD')
        style.configure('TProgressbar',  troughcolor='#E0E0E0', background='#3A6BC4')

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._nav = tk.Frame(self, bg=NAV_BG, width=190)
        self._nav.pack(side='left', fill='y')
        self._nav.pack_propagate(False)

        logo_frame = tk.Frame(self._nav, bg=NAV_BG, pady=20)
        logo_frame.pack(fill='x')
        tk.Label(logo_frame, text="LENEL", font=('Segoe UI', 18, 'bold'),
                 bg=NAV_BG, fg='#FFFFFF').pack()
        tk.Label(logo_frame, text="Attendance Manager", font=('Segoe UI', 8),
                 bg=NAV_BG, fg='#A0B8D8').pack()

        tk.Frame(self._nav, bg='#2E5090', height=1).pack(fill='x', padx=10)

        self._nav_btns = {}
        for label, key in NAV_ITEMS:
            btn = tk.Label(self._nav, text=f"  {label}", font=('Segoe UI', 10),
                           bg=NAV_BG, fg=NAV_FG, anchor='w', padx=12, pady=10,
                           cursor='hand2')
            btn.pack(fill='x')
            btn.bind('<Button-1>', lambda e, k=key: self._show_tab(k))
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=NAV_HOVER)
                     if b.cget('bg') != NAV_ACTIVE else None)
            btn.bind('<Leave>', lambda e, b=btn, k2=key: b.configure(
                bg=NAV_ACTIVE if self._current_tab == k2 else NAV_BG))
            self._nav_btns[key] = btn

        tk.Frame(self._nav, bg='#2E5090', height=1).pack(
            fill='x', padx=10, side='bottom', pady=(0, 4))

        self._tray_hint = tk.Label(
            self._nav,
            text="✕ closes to tray" if _TRAY_AVAILABLE else "",
            font=('Segoe UI', 7), bg=NAV_BG, fg='#5080A0',
            anchor='w', padx=12)
        self._tray_hint.pack(side='bottom', fill='x')

        self._sched_lbl = tk.Label(
            self._nav, text="⏱ Scheduler: Running",
            font=('Segoe UI', 8), bg=NAV_BG, fg='#7EC8A0',
            anchor='w', padx=12, pady=6)
        self._sched_lbl.pack(side='bottom', fill='x')

        tk.Label(self._nav, text=f"v{VERSION}", font=('Segoe UI', 7),
                 bg=NAV_BG, fg='#5080A0', anchor='w', padx=12).pack(
            side='bottom', fill='x')

        self._content = tk.Frame(self, bg=CONTENT_BG)
        self._content.pack(side='left', fill='both', expand=True)

        self._tabs = {
            'dashboard': DashboardTab(self._content),
            'generate':  GenerateTab(self._content),
            'profiles':  ProfilesTab(self._content),
            'settings':  SettingsTab(self._content),
            'logs':      LogsTab(self._content),
        }
        self._current_tab = None

    def _show_tab(self, key):
        for tab in self._tabs.values():
            tab.pack_forget()
        for k, btn in self._nav_btns.items():
            btn.configure(bg=NAV_ACTIVE if k == key else NAV_BG)
        self._tabs[key].pack(fill='both', expand=True)
        self._current_tab = key

        if key == 'dashboard':  self._tabs['dashboard'].refresh()
        elif key == 'generate': self._tabs['generate'].refresh()
        elif key == 'settings': self._tabs['settings'].refresh()
        elif key == 'logs':     self._tabs['logs'].refresh()
        elif key == 'profiles': self._tabs['profiles'].refresh()

    def _start_scheduler(self):
        def _check_and_start():
            try:
                import svc_manager
                if svc_manager.is_running():
                    self.after(0, lambda: self._sched_lbl.configure(
                        text="⏱ Service: Active", fg='#7EC8A0'))
                    config.log_activity(
                        "GUI scheduler skipped — Windows service is active.", "INFO")
                    return
            except Exception:
                pass

            def status_cb(msg):
                self._sched_lbl.configure(text=f"⏱ {msg}")
                self.after(5000, lambda: self._sched_lbl.configure(
                    text="⏱ Scheduler: Running"))

            scheduler.set_status_callback(status_cb)
            scheduler.start()

        threading.Thread(target=_check_and_start, daemon=True).start()

    # ── Window close → hide to tray ───────────────────────────────────────────
    def on_close(self):
        if self._tray:
            self.withdraw()   # hide window, keep tray icon alive
        else:
            scheduler.stop()
            self.destroy()


_instance_mutex = None   # kept alive for the lifetime of the process


def _ensure_single_instance():
    """
    Create a named Windows mutex. If it already exists another instance is
    running — bring that window to the front and return False so we exit.
    """
    global _instance_mutex
    kernel32 = ctypes.windll.kernel32
    _instance_mutex = kernel32.CreateMutexW(None, False, "LenelAttendanceManager_SingleInstance")
    if kernel32.GetLastError() == 183:          # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(_instance_mutex)
        _instance_mutex = None
        # Try to un-hide and focus the existing window
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, APP_NAME)
        if hwnd:
            user32.ShowWindow(hwnd, 9)           # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
        return False
    return True


def main():
    if not _ensure_single_instance():
        return   # another instance is already running
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == '__main__':
    main()
