import tkinter as tk
from tkinter import ttk
from datetime import datetime
import config


class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ttk.Label(self, text="Dashboard", font=('Segoe UI', 16, 'bold'),
                  foreground='#1F3864').pack(anchor='w', padx=20, pady=(18, 4))
        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=(0, 14))

        # Status cards row
        cards = ttk.Frame(self)
        cards.pack(fill='x', padx=20)
        self._scheduler_lbl = self._card(cards, "Scheduler", "Running", "#2ECC71")
        self._next_lbl = self._card(cards, "Next Scheduled Run", "—", "#1F3864")
        self._last_lbl = self._card(cards, "Last Run", "—", "#555555")

        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=14)

        # Recent profiles
        ttk.Label(self, text="Active Report Profiles", font=('Segoe UI', 11, 'bold'),
                  foreground='#1F3864').pack(anchor='w', padx=20, pady=(0, 6))

        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))

        cols = ('Profile', 'Frequency', 'Run Time', 'Last Run', 'Status')
        self._tree = ttk.Treeview(frame, columns=cols, show='headings', height=8)
        widths = (180, 90, 90, 160, 200)
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor='center')
        self._tree.column('Profile', anchor='w')
        self._tree.column('Status', anchor='w')

        sb = ttk.Scrollbar(frame, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self.refresh()

    def _card(self, parent, label, value, color):
        f = ttk.Frame(parent, relief='solid', borderwidth=1)
        f.pack(side='left', padx=(0, 12), pady=4, ipadx=16, ipady=10)
        ttk.Label(f, text=label, font=('Segoe UI', 9), foreground='#888888').pack(anchor='w')
        lbl = ttk.Label(f, text=value, font=('Segoe UI', 13, 'bold'), foreground=color)
        lbl.pack(anchor='w')
        return lbl

    def refresh(self):
        profiles = config.get_report_profiles()
        enabled = [p for p in profiles if p.get('enabled')]

        self._next_lbl.configure(text=_next_run_text(enabled))

        for item in self._tree.get_children():
            self._tree.delete(item)

        for p in profiles:
            last_run = p.get('last_run', '') or '—'
            if last_run and last_run != '—':
                try:
                    last_run = datetime.fromisoformat(last_run).strftime('%d-%b-%Y %H:%M')
                except Exception:
                    pass
            status = p.get('last_status', '') or '—'
            tag = 'ok' if 'Success' in str(status) else ('err' if 'Error' in str(status) else '')
            self._tree.insert('', 'end', values=(
                p['name'],
                p.get('frequency', 'daily').title(),
                p.get('run_time', '00:00'),
                last_run,
                status,
            ), tags=(tag,))

        self._tree.tag_configure('ok', foreground='#27AE60')
        self._tree.tag_configure('err', foreground='#E74C3C')

        logs = config.get_activity_logs(1)
        if logs:
            try:
                ts = datetime.fromisoformat(logs[0]['timestamp']).strftime('%d-%b-%Y %H:%M')
                self._last_lbl.configure(text=ts)
            except Exception:
                pass


def _next_run_text(profiles):
    if not profiles:
        return "No active profiles"
    times = [p.get('run_time', '00:00') for p in profiles]
    return ', '.join(sorted(set(times)))
