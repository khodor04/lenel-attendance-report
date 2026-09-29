import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import threading
from datetime import date, timedelta

import config
import database
import scheduler


class ProfilesTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        ttk.Label(self, text="Self-Running Report Profiles",
                  font=('Segoe UI', 16, 'bold'), foreground='#1F3864').pack(
            anchor='w', padx=20, pady=(18, 4))
        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=(0, 10))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', padx=20, pady=(0, 6))
        ttk.Button(toolbar, text="+ New Profile", command=self._new).pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text="Edit", command=self._edit).pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text="Delete", command=self._delete).pack(side='left', padx=(0, 6))
        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=8)
        ttk.Button(toolbar, text="Run Now", command=self._run_now).pack(side='left', padx=(0, 6))
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side='right')

        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=20, pady=(0, 12))

        cols = ('Name', 'Title', 'Frequency', 'Run Time', 'Companies', 'Recipients', 'Enabled', 'Last Status')
        self._tree = ttk.Treeview(frame, columns=cols, show='headings', height=12)
        widths = (150, 160, 90, 80, 160, 200, 70, 180)
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w)
        self._tree.column('Enabled', anchor='center')
        self._tree.column('Frequency', anchor='center')
        self._tree.column('Run Time', anchor='center')

        vsb = ttk.Scrollbar(frame, orient='vertical', command=self._tree.yview)
        hsb = ttk.Scrollbar(frame, orient='horizontal', command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')

        self._tree.tag_configure('enabled', foreground='#27AE60')
        self._tree.tag_configure('disabled', foreground='#999999')

        self._status = ttk.Label(self, text="", foreground='#555555', font=('Segoe UI', 9, 'italic'))
        self._status.pack(anchor='w', padx=20, pady=2)

        self.refresh()

    def refresh(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        profiles = config.get_report_profiles()
        divs = {}
        try:
            divs = {d['id']: d['name'] for d in database.get_divisions()}
        except Exception:
            pass

        for p in profiles:
            companies = json.loads(p.get('companies') or '[]')
            company_names = ', '.join(divs.get(c, str(c)) for c in companies) if companies else 'All'
            recipients = json.loads(p.get('recipients') or '[]')
            enabled = '✓' if p.get('enabled') else '✗'
            tag = 'enabled' if p.get('enabled') else 'disabled'
            self._tree.insert('', 'end', iid=str(p['id']), tags=(tag,), values=(
                p['name'],
                p.get('title', ''),
                p.get('frequency', 'daily').title(),
                p.get('run_time', '00:00'),
                company_names,
                ', '.join(recipients[:2]) + ('…' if len(recipients) > 2 else ''),
                enabled,
                p.get('last_status', '') or '—',
            ))

    def _selected_id(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select a profile first.")
            return None
        return int(sel[0])

    def _new(self):
        dlg = _ProfileDialog(self)
        self.wait_window(dlg)
        self.refresh()

    def _edit(self):
        pid = self._selected_id()
        if pid is None:
            return
        profile = config.get_report_profile(pid)
        if not profile:
            return
        dlg = _ProfileDialog(self, profile)
        self.wait_window(dlg)
        self.refresh()

    def _delete(self):
        pid = self._selected_id()
        if pid is None:
            return
        if messagebox.askyesno("Delete", "Delete this profile?"):
            config.delete_report_profile(pid)
            self.refresh()

    def _run_now(self):
        pid = self._selected_id()
        if pid is None:
            return
        profile = config.get_report_profile(pid)
        if not profile:
            return

        yesterday = date.today() - timedelta(days=1)
        start_d, end_d = scheduler.get_report_dates(profile, date.today())

        self._status.configure(text=f"Running '{profile['name']}'…")

        def run():
            ok, result = scheduler.generate_and_send(profile, start_d, end_d)
            msg = f"Done: {len(result)} records" if ok else f"Error: {result}"
            self.after(0, lambda: self._status.configure(text=msg))
            self.after(0, self.refresh)

        threading.Thread(target=run, daemon=True).start()


class _ProfileDialog(tk.Toplevel):
    def __init__(self, parent, profile=None):
        super().__init__(parent)
        self._profile = profile or {}
        self._divs = []
        self._div_vars = {}
        self.title("Edit Profile" if profile else "New Report Profile")
        self.geometry("620x680")
        self.resizable(True, True)
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, borderwidth=0)
        vsb = ttk.Scrollbar(self, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        self._inner = ttk.Frame(canvas, padding=16)
        self._inner_id = canvas.create_window((0, 0), window=self._inner, anchor='nw')
        self._inner.bind('<Configure>', lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')))

        f = self._inner
        p = self._profile

        def field(r, label, default='', width=38, show=''):
            ttk.Label(f, text=label).grid(row=r, column=0, sticky='w', pady=4, padx=(0, 10))
            v = tk.StringVar(value=default)
            e = ttk.Entry(f, textvariable=v, width=width, show=show)
            e.grid(row=r, column=1, columnspan=2, sticky='w')
            return v

        self._name = field(0, "Profile Name:", p.get('name', ''))
        self._title = field(1, "Report Title:", p.get('title', ''))
        self._subject = field(2, "Email Subject:", p.get('email_subject', '{title} for {date}'))

        # Output folder
        ttk.Label(f, text="Output Folder:").grid(row=3, column=0, sticky='w', pady=4)
        folder_frame = ttk.Frame(f)
        folder_frame.grid(row=3, column=1, columnspan=2, sticky='w')
        self._folder = ttk.Entry(folder_frame, width=34)
        self._folder.insert(0, p.get('output_folder') or config.get_setting('output_folder', ''))
        self._folder.pack(side='left')
        ttk.Button(folder_frame, text="…", width=3,
                   command=self._browse).pack(side='left', padx=4)

        # Frequency
        ttk.Label(f, text="Frequency:").grid(row=4, column=0, sticky='w', pady=4)
        freq_frame = ttk.Frame(f)
        freq_frame.grid(row=4, column=1, columnspan=2, sticky='w')
        self._freq = ttk.Combobox(freq_frame, values=['daily', 'weekly', 'monthly'],
                                   width=10, state='readonly')
        self._freq.set(p.get('frequency', 'daily'))
        self._freq.pack(side='left')

        ttk.Label(freq_frame, text="  Run Time (HH:MM):").pack(side='left')
        self._run_time = ttk.Entry(freq_frame, width=8)
        self._run_time.insert(0, p.get('run_time', '00:00'))
        self._run_time.pack(side='left', padx=4)

        # Day of week / month
        ttk.Label(f, text="Day of Week (0=Mon):").grid(row=5, column=0, sticky='w', pady=4)
        dow_frame = ttk.Frame(f)
        dow_frame.grid(row=5, column=1, columnspan=2, sticky='w')
        self._dow = ttk.Spinbox(dow_frame, from_=0, to=6, width=4)
        self._dow.set(p.get('day_of_week', 0))
        self._dow.pack(side='left')
        ttk.Label(dow_frame, text="  Day of Month (1-28):").pack(side='left', padx=8)
        self._dom = ttk.Spinbox(dow_frame, from_=1, to=28, width=4)
        self._dom.set(p.get('day_of_month', 1))
        self._dom.pack(side='left')

        # Recipients
        self._recipients = field(6, "Recipients (comma-sep):",
                                  ', '.join(json.loads(p.get('recipients') or '[]')))
        self._cc = field(7, "CC (comma-sep):",
                          ', '.join(json.loads(p.get('cc') or '[]')))

        # Email body
        ttk.Label(f, text="Email Body:").grid(row=8, column=0, sticky='nw', pady=4)
        self._body = tk.Text(f, width=44, height=4, font=('Segoe UI', 9))
        self._body.insert('1.0', p.get('email_body', ''))
        self._body.grid(row=8, column=1, columnspan=2, sticky='w')

        # Format checkboxes
        fmt_frame = ttk.Frame(f)
        fmt_frame.grid(row=9, column=0, columnspan=3, sticky='w', pady=4)
        self._incl_xlsx = tk.BooleanVar(value=bool(p.get('include_excel', 1)))
        self._incl_pdf = tk.BooleanVar(value=bool(p.get('include_pdf', 1)))
        self._incl_remarks = tk.BooleanVar(value=bool(p.get('include_remarks', 1)))
        self._enabled = tk.BooleanVar(value=bool(p.get('enabled', 1)))
        ttk.Checkbutton(fmt_frame, text="Include Excel", variable=self._incl_xlsx).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(fmt_frame, text="Include PDF", variable=self._incl_pdf).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(fmt_frame, text="Include Remarks", variable=self._incl_remarks).pack(side='left', padx=(0, 10))
        ttk.Checkbutton(fmt_frame, text="Enabled", variable=self._enabled).pack(side='left')

        # Company filter
        ttk.Label(f, text="Companies:").grid(row=10, column=0, sticky='nw', pady=4)
        self._company_frame = ttk.Frame(f)
        self._company_frame.grid(row=10, column=1, columnspan=2, sticky='w')
        self._load_companies(json.loads(p.get('companies') or '[]'))

        # Buttons
        btn_row = ttk.Frame(f)
        btn_row.grid(row=11, column=0, columnspan=3, sticky='e', pady=12)
        ttk.Button(btn_row, text="Save", command=self._save).pack(side='left', padx=4)
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side='left')

    def _browse(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self._folder.delete(0, 'end')
            self._folder.insert(0, folder)

    def _load_companies(self, selected_ids):
        for w in self._company_frame.winfo_children():
            w.destroy()
        self._div_vars = {}
        try:
            self._divs = database.get_divisions()
        except Exception:
            self._divs = []

        self._all_companies_var = tk.BooleanVar(value=(not selected_ids))
        ttk.Checkbutton(self._company_frame, text="All Companies",
                         variable=self._all_companies_var).grid(row=0, column=0, columnspan=4, sticky='w')

        for i, d in enumerate(self._divs):
            v = tk.BooleanVar(value=(d['id'] in selected_ids))
            self._div_vars[d['id']] = v
            col = i % 2
            row_n = 1 + i // 2
            ttk.Checkbutton(self._company_frame, text=d['name'], variable=v).grid(
                row=row_n, column=col, sticky='w', padx=(0, 12))

    def _save(self):
        name = self._name.get().strip()
        if not name:
            messagebox.showerror("Validation", "Profile name is required.", parent=self)
            return

        companies = ([] if self._all_companies_var.get()
                     else [cid for cid, v in self._div_vars.items() if v.get()])
        recipients = [e.strip() for e in self._recipients.get().split(',') if e.strip()]
        cc = [e.strip() for e in self._cc.get().split(',') if e.strip()]

        profile = {
            'id': self._profile.get('id'),
            'name': name,
            'title': self._title.get().strip(),
            'email_subject': self._subject.get().strip(),
            'output_folder': self._folder.get().strip(),
            'frequency': self._freq.get(),
            'run_time': self._run_time.get().strip(),
            'day_of_week': int(self._dow.get()),
            'day_of_month': int(self._dom.get()),
            'recipients': recipients,
            'cc': cc,
            'email_body': self._body.get('1.0', 'end').strip(),
            'include_excel': self._incl_xlsx.get(),
            'include_pdf': self._incl_pdf.get(),
            'include_remarks': self._incl_remarks.get(),
            'enabled': self._enabled.get(),
            'companies': companies,
        }
        try:
            config.save_report_profile(profile)
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save profile:\n{exc}", parent=self)
            return
        self.destroy()
