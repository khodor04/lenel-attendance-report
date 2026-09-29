import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import config


class LogsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ttk.Label(self, text="Activity Log", font=('Segoe UI', 16, 'bold'),
                  foreground='#1F3864').pack(anchor='w', padx=20, pady=(18, 4))
        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=(0, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', padx=20, pady=(0, 6))
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text="Clear Old Logs (>60 days)", command=self._clear).pack(side='left')

        # Filter
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side='right')
        ttk.Label(filter_frame, text="Filter:").pack(side='left')
        self._filter_var = ttk.Combobox(filter_frame, values=['All', 'INFO', 'WARNING', 'ERROR'],
                                         width=10, state='readonly')
        self._filter_var.set('All')
        self._filter_var.pack(side='left', padx=4)
        self._filter_var.bind('<<ComboboxSelected>>', lambda _: self.refresh())

        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=20, pady=(0, 12))

        cols = ('Timestamp', 'Level', 'Message')
        self._tree = ttk.Treeview(frame, columns=cols, show='headings', height=18)
        self._tree.heading('Timestamp', text='Timestamp')
        self._tree.heading('Level', text='Level')
        self._tree.heading('Message', text='Message')
        self._tree.column('Timestamp', width=160, anchor='center')
        self._tree.column('Level', width=80, anchor='center')
        self._tree.column('Message', width=700, anchor='w')

        self._tree.tag_configure('ERROR', foreground='#E74C3C')
        self._tree.tag_configure('WARNING', foreground='#E67E22')
        self._tree.tag_configure('INFO', foreground='#27AE60')

        vsb = ttk.Scrollbar(frame, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self._count_lbl = ttk.Label(self, text="", foreground='#888888', font=('Segoe UI', 8))
        self._count_lbl.pack(anchor='w', padx=20)

        self.refresh()

    def refresh(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

        level_filter = self._filter_var.get()
        logs = config.get_activity_logs(500)

        count = 0
        for log in logs:
            lvl = log.get('level', 'INFO')
            if level_filter != 'All' and lvl != level_filter:
                continue
            ts = log.get('timestamp', '')
            try:
                ts = datetime.fromisoformat(ts).strftime('%d-%b-%Y %H:%M:%S')
            except Exception:
                pass
            self._tree.insert('', 'end', values=(ts, lvl, log.get('message', '')), tags=(lvl,))
            count += 1

        self._count_lbl.configure(text=f"{count} entries shown")

    def _clear(self):
        if messagebox.askyesno("Clear Logs", "Remove log entries older than 60 days?"):
            config.clear_old_logs(60)
            self.refresh()
