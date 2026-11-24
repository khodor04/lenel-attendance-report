import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import config
import scheduler


class DashboardTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._profiles = []
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

        # Header row
        hdr = ttk.Frame(self)
        hdr.pack(fill='x', padx=20, pady=(0, 6))
        ttk.Label(hdr, text="Active Report Profiles", font=('Segoe UI', 11, 'bold'),
                  foreground='#1F3864').pack(side='left')

        # Run Now button
        self._run_btn = ttk.Button(hdr, text="▶ Run Now (resend missed)",
                                    command=self._run_now)
        self._run_btn.pack(side='right')

        # Profile treeview
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=20, pady=(0, 4))

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

        # Run Now status label
        self._run_status = tk.StringVar(value="Select a profile above then click Run Now to resend immediately.")
        ttk.Label(self, textvariable=self._run_status, foreground='#555555',
                  font=('Segoe UI', 9, 'italic')).pack(anchor='w', padx=20, pady=(2, 8))

        self.refresh()

    def _card(self, parent, label, value, color):
        f = ttk.Frame(parent, relief='solid', borderwidth=1)
        f.pack(side='left', padx=(0, 12), pady=4, ipadx=16, ipady=10)
        ttk.Label(f, text=label, font=('Segoe UI', 9), foreground='#888888').pack(anchor='w')
        lbl = ttk.Label(f, text=value, font=('Segoe UI', 13, 'bold'), foreground=color)
        lbl.pack(anchor='w')
        return lbl

    def refresh(self):
        self._profiles = config.get_report_profiles()
        enabled = [p for p in self._profiles if p.get('enabled')]

        self._next_lbl.configure(text=_next_run_text(enabled))

        for item in self._tree.get_children():
            self._tree.delete(item)

        for i, p in enumerate(self._profiles):
            last_run = p.get('last_run', '') or '—'
            if last_run and last_run != '—':
                try:
                    last_run = datetime.fromisoformat(last_run).strftime('%d-%b-%Y %H:%M')
                except Exception:
                    pass
            status = p.get('last_status', '') or '—'
            tag = 'ok' if 'Success' in str(status) else ('err' if 'Error' in str(status) else '')
            self._tree.insert('', 'end', iid=str(i), values=(
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

    def _run_now(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Run Now", "Please select a profile from the list first.")
            return

        idx = int(sel[0])
        profile = self._profiles[idx]
        name = profile.get('name', 'Report')

        start_date, end_date = scheduler.get_missed_date_range(profile)
        if start_date is None:
            messagebox.showerror("Run Now", f"Could not determine date range for '{name}'.")
            return

        confirm = messagebox.askyesno(
            "Run Now",
            f"Run '{name}' immediately?\n\n"
            f"Period: {start_date.strftime('%d-%b-%Y')} to {end_date.strftime('%d-%b-%Y')}\n\n"
            f"This will generate and email the report now."
        )
        if not confirm:
            return

        self._run_btn.configure(state='disabled')
        self._run_status.set(f"Running '{name}'…")

        def run():
            ok, result = scheduler.generate_and_send(profile, start_date, end_date)
            if ok:
                msg = f"'{name}' sent successfully ({start_date.strftime('%d-%b-%Y')} to {end_date.strftime('%d-%b-%Y')})."
                color = '#27AE60'
            else:
                msg = f"'{name}' failed: {result}"
                color = '#E74C3C'
            self.after(0, lambda: self._run_done(msg, color))

        threading.Thread(target=run, daemon=True).start()

    def _run_done(self, msg, color):
        self._run_btn.configure(state='normal')
        self._run_status.set(msg)
        # Update status label color
        for w in self.winfo_children():
            if isinstance(w, ttk.Label) and w.cget('textvariable') == str(self._run_status):
                w.configure(foreground=color)
                break
        self.refresh()


def _next_run_text(profiles):
    if not profiles:
        return "No active profiles"
    times = [p.get('run_time', '00:00') for p in profiles]
    return ', '.join(sorted(set(times)))
