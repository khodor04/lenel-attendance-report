import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import shutil
import sqlite3
from datetime import datetime
import config
import database
import emailer
import startup
import svc_manager


class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ttk.Label(self, text="Settings", font=('Segoe UI', 16, 'bold'),
                  foreground='#1F3864').pack(anchor='w', padx=20, pady=(18, 4))
        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=(0, 10))

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=20, pady=(0, 12))

        self._db_tab     = _DBSettings(nb)
        self._email_tab  = _EmailSettings(nb)
        self._reader_tab = _ReaderList(nb)
        self._system_tab = _SystemSettings(nb)

        nb.add(self._db_tab,     text="Database")
        nb.add(self._email_tab,  text="Email / SMTP")
        nb.add(self._reader_tab, text="Reader List")
        nb.add(self._system_tab, text="System")

    def refresh(self):
        pass


class _DBSettings(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=16)
        f.pack(fill='both', expand=True)
        f.columnconfigure(1, weight=1)

        s = config.get_all_settings()

        def row(r, label, key, show=''):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=5, padx=(0, 12))
            v = tk.StringVar(value=s.get(key, ''))
            e = ttk.Entry(f, textvariable=v, width=38, show=show)
            e.grid(row=r, column=1, sticky='w')
            return v

        self._server = row(0, "SQL Server:", 'db_server')
        self._db     = row(1, "Database Name:", 'db_name')

        ttk.Label(f, text="Authentication:").grid(row=2, column=0, sticky='w', pady=5)
        self._auth = ttk.Combobox(f, values=['windows', 'sql'], width=15, state='readonly')
        self._auth.set(s.get('db_auth', 'windows'))
        self._auth.grid(row=2, column=1, sticky='w')
        self._auth.bind('<<ComboboxSelected>>', self._toggle_sql_auth)

        self._user = row(3, "SQL Username:", 'db_user')

        # SQL Password with show/hide toggle
        ttk.Label(f, text="SQL Password:").grid(row=4, column=0, sticky='w', pady=5)
        db_pwd_frame = ttk.Frame(f)
        db_pwd_frame.grid(row=4, column=1, sticky='w')
        self._pwd = tk.StringVar(value=s.get('db_password', ''))
        self._db_pwd_entry = ttk.Entry(db_pwd_frame, textvariable=self._pwd, width=32, show='*')
        self._db_pwd_entry.pack(side='left')
        self._db_pwd_visible = False
        self._db_pwd_btn = ttk.Button(db_pwd_frame, text="Show", width=5,
                                      command=self._toggle_db_pwd)
        self._db_pwd_btn.pack(side='left', padx=(4, 0))

        ttk.Label(f, text="Archive Threshold:").grid(row=5, column=0, sticky='w', pady=5)
        arch_frame = ttk.Frame(f)
        arch_frame.grid(row=5, column=1, sticky='w')
        self._arch_lbl = ttk.Label(arch_frame, text="fetching…", foreground='#555555')
        self._arch_lbl.pack(side='left')
        ttk.Label(arch_frame, text="  (auto-read from View_ArchiveConfig-App)",
                  foreground='#888888', font=('Segoe UI', 8)).pack(side='left', padx=6)
        self.after(500, lambda: threading.Thread(target=self._load_archive_threshold, daemon=True).start())

        ttk.Label(f, text="Output Folder:").grid(row=6, column=0, sticky='w', pady=5)
        self._folder = ttk.Entry(f, width=38)
        self._folder.insert(0, s.get('output_folder', ''))
        self._folder.grid(row=6, column=1, sticky='w')

        btn_row = ttk.Frame(f)
        btn_row.grid(row=7, column=0, columnspan=3, sticky='w', pady=12)
        ttk.Button(btn_row, text="Save Settings", command=self._save).pack(side='left', padx=(0, 8))
        ttk.Button(btn_row, text="Test Connection", command=self._test).pack(side='left')

        self._status = ttk.Label(f, text="", foreground='#555555')
        self._status.grid(row=8, column=0, columnspan=2, sticky='w')

        self._toggle_sql_auth()

    def _load_archive_threshold(self):
        try:
            import database
            days = database.get_archive_threshold_days()
            self.after(0, lambda: self._arch_lbl.configure(
                text=f"{days} days", foreground='#27AE60'))
        except Exception:
            self.after(0, lambda: self._arch_lbl.configure(
                text="unavailable", foreground='#E74C3C'))

    def _toggle_db_pwd(self):
        self._db_pwd_visible = not self._db_pwd_visible
        self._db_pwd_entry.configure(show='' if self._db_pwd_visible else '*')
        self._db_pwd_btn.configure(text='Hide' if self._db_pwd_visible else 'Show')

    def _toggle_sql_auth(self, *_):
        pass   # windows auth ignores user/pwd fields; leave them visible

    def _save(self):
        config.set_setting('db_server', self._server.get().strip())
        config.set_setting('db_name', self._db.get().strip())
        config.set_setting('db_auth', self._auth.get())
        config.set_setting('db_user', self._user.get().strip())
        config.set_setting('db_password', self._pwd.get())
        config.set_setting('output_folder', self._folder.get().strip())
        self._status.configure(text="Settings saved.", foreground='#27AE60')

    def _test(self):
        self._status.configure(text="Testing…", foreground='#555555')
        self.update()

        def run():
            ok, msg = database.test_connection()
            color = '#27AE60' if ok else '#E74C3C'
            if ok:
                display = msg
            else:
                display = 'Connection failed — see Activity Log for details.'
                config.log_activity(f"Connection test failed: {msg}", 'ERROR')
            self.after(0, lambda m=display, c=color: self._status.configure(text=m, foreground=c))

        threading.Thread(target=run, daemon=True).start()


class _EmailSettings(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=16)
        f.pack(fill='both', expand=True)
        f.columnconfigure(1, weight=1)
        s = config.get_all_settings()

        def row(r, label, key, show=''):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=5, padx=(0, 12))
            v = tk.StringVar(value=s.get(key, ''))
            e = ttk.Entry(f, textvariable=v, width=38, show=show)
            e.grid(row=r, column=1, sticky='w')
            return v

        self._server = row(0, "SMTP Server:", 'smtp_server')
        self._port   = row(1, "Port:",        'smtp_port')
        self._user   = row(2, "Username:",    'smtp_user')
        self._from   = row(4, "From Address:",'smtp_from')

        # Password row with show/hide toggle
        ttk.Label(f, text="Password:").grid(row=3, column=0, sticky='w', pady=5, padx=(0, 12))
        pwd_frame = ttk.Frame(f)
        pwd_frame.grid(row=3, column=1, sticky='w')
        self._pwd = tk.StringVar(value=s.get('smtp_password', ''))
        self._pwd_entry = ttk.Entry(pwd_frame, textvariable=self._pwd, width=32, show='*')
        self._pwd_entry.pack(side='left')
        self._pwd_visible = False
        self._pwd_toggle_btn = ttk.Button(pwd_frame, text="Show", width=5,
                                          command=self._toggle_pwd)
        self._pwd_toggle_btn.pack(side='left', padx=(4, 0))

        ttk.Label(f, text="Encryption:").grid(row=5, column=0, sticky='w', pady=5)
        self._tls = ttk.Combobox(f, values=['STARTTLS (port 587)', 'SSL/TLS (port 465)', 'None'],
                                  width=22, state='readonly')
        self._tls.set('STARTTLS (port 587)' if s.get('smtp_use_tls', '1') == '1' else 'None')
        self._tls.grid(row=5, column=1, sticky='w')

        btn_row = ttk.Frame(f)
        btn_row.grid(row=6, column=0, columnspan=2, sticky='w', pady=12)
        ttk.Button(btn_row, text="Save", command=self._save).pack(side='left', padx=(0, 8))
        ttk.Button(btn_row, text="Test SMTP", command=self._test).pack(side='left')

        self._status = ttk.Label(f, text="", foreground='#555555')
        self._status.grid(row=7, column=0, columnspan=2, sticky='w')

        ttk.Label(f, text="Tip: For Gmail use smtp.gmail.com:587 with an App Password.",
                  foreground='#888888', font=('Segoe UI', 8, 'italic')).grid(
            row=8, column=0, columnspan=2, sticky='w', pady=(8, 0))

    def _toggle_pwd(self):
        self._pwd_visible = not self._pwd_visible
        self._pwd_entry.configure(show='' if self._pwd_visible else '*')
        self._pwd_toggle_btn.configure(text='Hide' if self._pwd_visible else 'Show')

    def _save(self):
        port_str = self._port.get().strip()
        try:
            if not (1 <= int(port_str) <= 65535):
                raise ValueError()
        except (ValueError, TypeError):
            messagebox.showerror("Invalid Port",
                                 "SMTP Port must be a number between 1 and 65535.")
            return
        config.set_setting('smtp_server', self._server.get().strip())
        config.set_setting('smtp_port', port_str)
        config.set_setting('smtp_user', self._user.get().strip())
        config.set_setting('smtp_password', self._pwd.get())
        config.set_setting('smtp_from', self._from.get().strip())
        tls = '0' if 'None' in self._tls.get() else '1'
        config.set_setting('smtp_use_tls', tls)
        self._status.configure(text="Email settings saved.", foreground='#27AE60')

    def _test(self):
        self._save()
        self._status.configure(text="Connecting…", foreground='#555555')
        self.update()

        def run():
            ok, msg = emailer.test_smtp()
            color = '#27AE60' if ok else '#E74C3C'
            self.after(0, lambda: self._status.configure(text=msg, foreground=color))

        threading.Thread(target=run, daemon=True).start()


class _ReaderList(ttk.Frame):
    """Read-only view of all T&A readers as known by the two database views."""

    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        top = ttk.Frame(self, padding=(16, 10, 16, 4))
        top.pack(fill='x')
        ttk.Label(top,
                  text="Readers and their type as reported by the database views. Read-only.",
                  foreground='#555555').pack(side='left')
        ttk.Button(top, text="Refresh from DB", command=self._refresh).pack(side='right')

        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=16, pady=(6, 4))

        cols = ('Reader Description', 'Punch Type')
        self._tree = ttk.Treeview(frame, columns=cols, show='headings', height=16)
        self._tree.heading('Reader Description', text='Reader Description')
        self._tree.heading('Punch Type',         text='Punch Type')
        self._tree.column('Reader Description', width=380)
        self._tree.column('Punch Type',         width=100, anchor='center')
        self._tree.tag_configure('entry', background='#D5E8D4')
        self._tree.tag_configure('exit',  background='#DAE8FC')

        vsb = ttk.Scrollbar(frame, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self._status = ttk.Label(self, text="", foreground='#888888',
                                  font=('Segoe UI', 8, 'italic'))
        self._status.pack(padx=16, anchor='w', pady=(2, 8))

        self._refresh()

    def _refresh(self):
        self._status.configure(text="Loading…")

        def run():
            try:
                readers = database.get_readers_from_view()
                def update(rows=readers):
                    for item in self._tree.get_children():
                        self._tree.delete(item)
                    for r in rows:
                        pt  = r['punch_type'] or ''
                        tag = 'entry' if pt == 'Entered' else ('exit' if pt == 'Exited' else '')
                        self._tree.insert('', 'end', values=(r['readerdesc'], pt), tags=(tag,))
                    self._status.configure(
                        text=f"{len(rows)} reader/type combinations loaded from views.")
                self.after(0, update)
            except Exception as e:
                self.after(0, lambda err=str(e): self._status.configure(text=f"Error: {err}"))

        threading.Thread(target=run, daemon=True).start()


class _SystemSettings(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=20)
        f.pack(fill='both', expand=True)
        f.columnconfigure(1, weight=1)

        # ── Windows Service ───────────────────────────────────────────────────
        ttk.Label(f, text="Windows Service",
                  font=('Segoe UI', 11, 'bold'), foreground='#1F3864').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 4))

        ttk.Label(f,
                  text="Run the scheduler as a Windows service so reports are sent\n"
                       "even when no user is logged in. Requires Administrator to install.",
                  foreground='#555555', font=('Segoe UI', 9)).grid(
            row=1, column=0, columnspan=2, sticky='w', pady=(0, 10))

        self._svc_status_var = tk.StringVar()
        self._svc_status_lbl = ttk.Label(f, textvariable=self._svc_status_var,
                                          font=('Segoe UI', 9, 'bold'))
        self._svc_status_lbl.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 8))

        svc_btn_row = ttk.Frame(f)
        svc_btn_row.grid(row=3, column=0, columnspan=2, sticky='w')
        self._svc_install_btn   = ttk.Button(svc_btn_row, text="Install Service",
                                              command=self._svc_install)
        self._svc_uninstall_btn = ttk.Button(svc_btn_row, text="Uninstall Service",
                                              command=self._svc_uninstall)
        self._svc_start_btn     = ttk.Button(svc_btn_row, text="Start",
                                              command=self._svc_start)
        self._svc_stop_btn      = ttk.Button(svc_btn_row, text="Stop",
                                              command=self._svc_stop)
        self._svc_refresh_btn   = ttk.Button(svc_btn_row, text="↻ Refresh",
                                              command=self._refresh_svc_status)
        for b in (self._svc_install_btn, self._svc_uninstall_btn,
                  self._svc_start_btn, self._svc_stop_btn, self._svc_refresh_btn):
            b.pack(side='left', padx=(0, 6))

        self._svc_msg = ttk.Label(f, text="", foreground='#555555', wraplength=560)
        self._svc_msg.grid(row=4, column=0, columnspan=2, sticky='w', pady=(6, 0))

        ttk.Separator(f, orient='horizontal').grid(
            row=5, column=0, columnspan=2, sticky='ew', pady=16)

        # ── Windows Startup ───────────────────────────────────────────────────
        ttk.Label(f, text="Windows Startup (GUI)",
                  font=('Segoe UI', 11, 'bold'), foreground='#1F3864').grid(
            row=6, column=0, columnspan=2, sticky='w', pady=(0, 4))

        ttk.Label(f,
                  text="Register the app to launch automatically when Windows starts.\n"
                       "If the app crashes, Windows will restart it automatically (up to 5 times, every 2 min).",
                  foreground='#555555', font=('Segoe UI', 9)).grid(
            row=7, column=0, columnspan=2, sticky='w', pady=(0, 10))

        self._status_var = tk.StringVar()
        self._status_lbl = ttk.Label(f, textvariable=self._status_var,
                                      font=('Segoe UI', 9, 'bold'))
        self._status_lbl.grid(row=8, column=0, columnspan=2, sticky='w', pady=(0, 10))

        btn_row = ttk.Frame(f)
        btn_row.grid(row=9, column=0, columnspan=2, sticky='w')
        ttk.Button(btn_row, text="Install at Startup",
                   command=self._install).pack(side='left', padx=(0, 8))
        ttk.Button(btn_row, text="Remove from Startup",
                   command=self._remove).pack(side='left')

        self._msg = ttk.Label(f, text="", wraplength=500)
        self._msg.grid(row=10, column=0, columnspan=2, sticky='w', pady=(8, 0))

        ttk.Separator(f, orient='horizontal').grid(
            row=11, column=0, columnspan=2, sticky='ew', pady=16)

        ttk.Label(f, text="Closing the window minimises the app to the system tray.\n"
                           "Right-click the tray icon and choose Exit to fully close.",
                  foreground='#888888', font=('Segoe UI', 8, 'italic')).grid(
            row=12, column=0, columnspan=2, sticky='w')

        # ── Backup & Restore ──────────────────────────────────────────────────
        ttk.Separator(f, orient='horizontal').grid(
            row=13, column=0, columnspan=2, sticky='ew', pady=16)

        ttk.Label(f, text="Backup & Restore",
                  font=('Segoe UI', 11, 'bold'), foreground='#1F3864').grid(
            row=14, column=0, columnspan=2, sticky='w', pady=(0, 6))

        ttk.Label(f,
                  text="All settings and report profiles live in lenel_app.db.\n"
                       "Back it up so they can be restored if the PC is replaced or fails.",
                  foreground='#555555', font=('Segoe UI', 9)).grid(
            row=15, column=0, columnspan=2, sticky='w', pady=(0, 10))

        bak_row = ttk.Frame(f)
        bak_row.grid(row=16, column=0, columnspan=2, sticky='w')
        ttk.Button(bak_row, text="Export Backup…",
                   command=self._export_backup).pack(side='left', padx=(0, 8))
        ttk.Button(bak_row, text="Import / Restore…",
                   command=self._import_backup).pack(side='left')

        self._bak_msg = ttk.Label(f, text="", wraplength=480)
        self._bak_msg.grid(row=17, column=0, columnspan=2, sticky='w', pady=(8, 0))

        # ── Auto-Save Daily Report ────────────────────────────────────────────
        ttk.Separator(f, orient='horizontal').grid(
            row=18, column=0, columnspan=2, sticky='ew', pady=16)

        ttk.Label(f, text="Auto-Save Daily Report",
                  font=('Segoe UI', 11, 'bold'), foreground='#1F3864').grid(
            row=19, column=0, columnspan=2, sticky='w', pady=(0, 4))

        ttk.Label(f,
                  text="Automatically saves yesterday's full attendance report every day,\n"
                       "even if no report profiles are configured. No email — local save only.",
                  foreground='#555555', font=('Segoe UI', 9)).grid(
            row=20, column=0, columnspan=2, sticky='w', pady=(0, 10))

        self._auto_save_enabled = tk.BooleanVar(
            value=config.get_setting('auto_save_enabled', '1') == '1')
        ttk.Checkbutton(f, text="Enable auto-save daily report",
                        variable=self._auto_save_enabled).grid(
            row=21, column=0, columnspan=2, sticky='w', pady=(0, 8))

        ttk.Label(f, text="Run Time (HH:MM):").grid(
            row=22, column=0, sticky='w', pady=5, padx=(0, 12))
        self._auto_save_time = ttk.Entry(f, width=8)
        self._auto_save_time.insert(0, config.get_setting('auto_save_time', '01:00'))
        self._auto_save_time.grid(row=22, column=1, sticky='w')

        ttk.Label(f, text="Save Folder:").grid(
            row=23, column=0, sticky='w', pady=5, padx=(0, 12))
        auto_folder_frame = ttk.Frame(f)
        auto_folder_frame.grid(row=23, column=1, sticky='w')
        self._auto_save_folder = ttk.Entry(auto_folder_frame, width=32)
        self._auto_save_folder.insert(0, config.get_setting('auto_save_folder', ''))
        self._auto_save_folder.pack(side='left')
        ttk.Button(auto_folder_frame, text="Browse…",
                   command=self._browse_auto_folder).pack(side='left', padx=(4, 0))

        auto_btn_row = ttk.Frame(f)
        auto_btn_row.grid(row=24, column=0, columnspan=2, sticky='w', pady=(10, 0))
        ttk.Button(auto_btn_row, text="Save Auto-Save Settings",
                   command=self._save_auto_save).pack(side='left', padx=(0, 8))
        ttk.Button(auto_btn_row, text="Open Folder",
                   command=self._open_auto_folder).pack(side='left')

        self._auto_save_msg = ttk.Label(f, text="", foreground='#555555')
        self._auto_save_msg.grid(row=25, column=0, columnspan=2, sticky='w', pady=(6, 0))

        # ── Prepare for Update ────────────────────────────────────────────────
        ttk.Separator(f, orient='horizontal').grid(
            row=26, column=0, columnspan=2, sticky='ew', pady=16)

        ttk.Label(f, text="Prepare for Update",
                  font=('Segoe UI', 11, 'bold'), foreground='#C0392B').grid(
            row=27, column=0, columnspan=2, sticky='w', pady=(0, 4))

        ttk.Label(f,
                  text="Stops the Windows service, the in-app scheduler and closes the app\n"
                       "so you can copy the updated EXE file(s) without getting a file-in-use error.",
                  foreground='#555555', font=('Segoe UI', 9)).grid(
            row=28, column=0, columnspan=2, sticky='w', pady=(0, 10))

        ttk.Button(f, text="Stop Service & Exit App",
                   command=self._stop_and_exit).grid(
            row=29, column=0, columnspan=2, sticky='w')

        self._refresh_status()
        self._refresh_svc_status()

    def _refresh_svc_status(self):
        status = svc_manager.get_status()
        if status == 'running':
            self._svc_status_var.set("Status: Running ✓")
            self._svc_status_lbl.configure(foreground='#27AE60')
        elif status == 'stopped':
            self._svc_status_var.set("Status: Stopped")
            self._svc_status_lbl.configure(foreground='#E67E22')
        else:
            self._svc_status_var.set("Status: Not installed")
            self._svc_status_lbl.configure(foreground='#888888')

        installed = (status != 'not_installed')
        running   = (status == 'running')
        self._svc_install_btn.configure(  state='disabled' if installed else 'normal')
        self._svc_uninstall_btn.configure(state='normal'   if installed else 'disabled')
        self._svc_start_btn.configure(    state='disabled' if running   else ('normal' if installed else 'disabled'))
        self._svc_stop_btn.configure(     state='normal'   if running   else 'disabled')

    def _svc_install(self):
        self._svc_install_btn.configure(state='disabled')
        self._svc_msg.configure(text="Installing… (this may take a few seconds)", foreground='#555555')

        def run():
            ok, msg = svc_manager.install()
            def done(o=ok, m=msg):
                self._svc_msg.configure(text=m, foreground='#27AE60' if o else '#E74C3C')
                self._refresh_svc_status()
            self.after(0, done)

        threading.Thread(target=run, daemon=True).start()

    def _svc_uninstall(self):
        if not messagebox.askyesno("Uninstall Service",
                                    "Stop and remove the Lenel Attendance Service?\n\n"
                                    "Scheduled reports will no longer run unless the "
                                    "GUI app is open.", icon='warning'):
            return
        self._svc_uninstall_btn.configure(state='disabled')
        self._svc_msg.configure(text="Uninstalling… (this may take a few seconds)", foreground='#555555')

        def run():
            ok, msg = svc_manager.uninstall()
            def done(o=ok, m=msg):
                self._svc_msg.configure(text=m, foreground='#27AE60' if o else '#E74C3C')
                self._refresh_svc_status()
            self.after(0, done)

        threading.Thread(target=run, daemon=True).start()

    def _svc_start(self):
        ok, msg = svc_manager.start()
        self._svc_msg.configure(text=msg, foreground='#27AE60' if ok else '#E74C3C')
        self.after(1500, self._refresh_svc_status)   # give SCM a moment

    def _svc_stop(self):
        ok, msg = svc_manager.stop()
        self._svc_msg.configure(text=msg, foreground='#27AE60' if ok else '#E74C3C')
        self.after(1500, self._refresh_svc_status)

    def _browse_auto_folder(self):
        folder = filedialog.askdirectory(title="Select Auto-Save Folder")
        if folder:
            self._auto_save_folder.delete(0, 'end')
            self._auto_save_folder.insert(0, folder)

    def _save_auto_save(self):
        import os
        time_val = self._auto_save_time.get().strip()
        try:
            h, m = time_val.split(':')
            if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
                raise ValueError()
        except (ValueError, TypeError):
            messagebox.showerror("Invalid Time", "Run Time must be in HH:MM format (e.g. 01:00).")
            return
        folder = self._auto_save_folder.get().strip()
        if folder:
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Invalid Folder", f"Cannot create folder: {e}")
                return
        config.set_setting('auto_save_enabled', '1' if self._auto_save_enabled.get() else '0')
        config.set_setting('auto_save_time', time_val)
        config.set_setting('auto_save_folder', folder)
        self._auto_save_msg.configure(text="Auto-save settings saved.", foreground='#27AE60')

    def _open_auto_folder(self):
        import os, subprocess
        folder = self._auto_save_folder.get().strip() or config.get_setting('auto_save_folder', '')
        if folder and os.path.isdir(folder):
            subprocess.Popen(['explorer', folder])
        else:
            messagebox.showinfo("Folder Not Found",
                                "The auto-save folder does not exist yet. It will be created when the first report runs.")

    def _refresh_status(self):
        try:
            if startup.is_registered():
                self._status_var.set("Status: Registered — starts automatically at login ✓")
                self._status_lbl.configure(foreground='#27AE60')
            else:
                self._status_var.set("Status: Not registered")
                self._status_lbl.configure(foreground='#888888')
        except Exception as e:
            self._status_var.set(f"Status: Unable to check ({e})")

    def _install(self):
        ok, msg = startup.register()
        self._msg.configure(text=msg, foreground='#27AE60' if ok else '#E74C3C')
        self._refresh_status()

    def _remove(self):
        ok, msg = startup.unregister()
        self._msg.configure(text=msg, foreground='#27AE60' if ok else '#E74C3C')
        self._refresh_status()

    def _stop_and_exit(self):
        if not messagebox.askyesno(
                "Stop Service & Exit",
                "This will:\n"
                "  • Stop the Windows service (if running)\n"
                "  • Stop the in-app scheduler\n"
                "  • Close the application\n\n"
                "You can then replace the EXE files.\n\n"
                "Continue?",
                icon='warning'):
            return
        import threading
        def do_stop():
            svc_manager.stop()   # stop Windows service (no-op if not running)
            import scheduler as _sched
            _sched.stop()
            root = self.winfo_toplevel()
            root.after(0, _force_exit, root)

        def _force_exit(root):
            if hasattr(root, '_tray') and root._tray:
                try:
                    root._tray.stop()
                except Exception:
                    pass
            root.destroy()

        threading.Thread(target=do_stop, daemon=True).start()

    def _export_backup(self):
        fname = f"lenel_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"
        path = filedialog.asksaveasfilename(
            title="Save Settings Backup",
            defaultextension=".db",
            filetypes=[("Database backup", "*.db"), ("All files", "*.*")],
            initialfile=fname,
        )
        if not path:
            return
        try:
            shutil.copy2(str(config.DB_PATH), path)
            self._bak_msg.configure(
                text=f"Backup saved to: {path}", foreground='#27AE60')
        except Exception as e:
            self._bak_msg.configure(text=f"Export failed: {e}", foreground='#E74C3C')

    def _import_backup(self):
        path = filedialog.askopenfilename(
            title="Select Backup File",
            filetypes=[("Database backup", "*.db"), ("All files", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno(
                "Restore Backup",
                "This will replace all current settings, reader mappings and report "
                "profiles with the backup.\n\nContinue?",
                icon='warning'):
            return
        try:
            with sqlite3.connect(path) as check_conn:
                result = check_conn.execute("PRAGMA integrity_check").fetchone()
            if result != ('ok',):
                self._bak_msg.configure(
                    text=f"Backup file failed integrity check ({result[0]}). Restore aborted.",
                    foreground='#E74C3C')
                return
            shutil.copy2(path, str(config.DB_PATH))
            config.initialize_db()   # ensure schema is up to date
            self._bak_msg.configure(
                text="Backup restored. Restart the app for all changes to take effect.",
                foreground='#27AE60')
        except Exception as e:
            self._bak_msg.configure(text=f"Restore failed: {e}", foreground='#E74C3C')
