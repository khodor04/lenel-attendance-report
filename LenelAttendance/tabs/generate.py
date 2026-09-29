import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
import os

import config
import database
import attendance
import report_excel
import report_pdf
import emailer


class GenerateTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._records = []
        self._xlsx_path = ''
        self._pdf_path = ''
        self._build()

    def _build(self):
        ttk.Label(self, text="Generate Report", font=('Segoe UI', 16, 'bold'),
                  foreground='#1F3864').pack(anchor='w', padx=20, pady=(18, 4))
        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=(0, 14))

        form = ttk.LabelFrame(self, text="Report Parameters", padding=14)
        form.pack(fill='x', padx=20, pady=(0, 10))

        # Date range
        r = 0
        ttk.Label(form, text="From Date (YYYY-MM-DD):").grid(row=r, column=0, sticky='w', pady=4)
        self._from = ttk.Entry(form, width=16)
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self._from.insert(0, yesterday)
        self._from.grid(row=r, column=1, sticky='w', padx=8)

        r += 1
        ttk.Label(form, text="To Date (YYYY-MM-DD):").grid(row=r, column=0, sticky='w', pady=4)
        self._to = ttk.Entry(form, width=16)
        self._to.insert(0, yesterday)
        self._to.grid(row=r, column=1, sticky='w', padx=8)

        # Quick date buttons
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=r, column=2, sticky='w', padx=16)
        ttk.Button(btn_frame, text="Yesterday", command=self._set_yesterday, width=10).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="This Week", command=self._set_this_week, width=10).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="This Month", command=self._set_this_month, width=10).pack(side='left', padx=2)

        r += 1
        ttk.Label(form, text="Report Title:").grid(row=r, column=0, sticky='w', pady=4)
        self._title = ttk.Entry(form, width=40)
        self._title.insert(0, "Attendance Report")
        self._title.grid(row=r, column=1, columnspan=2, sticky='w', padx=8)

        r += 1
        ttk.Label(form, text="Output Folder:").grid(row=r, column=0, sticky='w', pady=4)
        folder_frame = ttk.Frame(form)
        folder_frame.grid(row=r, column=1, columnspan=2, sticky='w', padx=8)
        self._folder = ttk.Entry(folder_frame, width=40)
        self._folder.insert(0, config.get_setting('output_folder', str(Path.home() / 'Documents' / 'LenelReports')))
        self._folder.pack(side='left')
        ttk.Button(folder_frame, text="Browse…", command=self._browse_folder).pack(side='left', padx=4)

        r += 1
        fmt_frame = ttk.Frame(form)
        fmt_frame.grid(row=r, column=1, columnspan=2, sticky='w', padx=8, pady=4)
        self._excel_var = tk.BooleanVar(value=True)
        self._pdf_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fmt_frame, text="Excel (.xlsx)", variable=self._excel_var).pack(side='left')
        ttk.Checkbutton(fmt_frame, text="PDF", variable=self._pdf_var).pack(side='left', padx=12)

        # Action buttons
        btn_row = ttk.Frame(self)
        btn_row.pack(fill='x', padx=20, pady=6)
        ttk.Button(btn_row, text="Generate Report", command=self._generate,
                   style='Accent.TButton').pack(side='left', padx=(0, 8))
        self._send_btn = ttk.Button(btn_row, text="Send by Email", command=self._send_email,
                                     state='disabled')
        self._send_btn.pack(side='left', padx=(0, 8))
        ttk.Button(btn_row, text="Open Output Folder", command=self._open_folder).pack(side='left')

        # Status
        self._status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self._status, foreground='#555555',
                  font=('Segoe UI', 9, 'italic')).pack(anchor='w', padx=20, pady=2)

        # Progress
        self._progress = ttk.Progressbar(self, mode='indeterminate')
        self._progress.pack(fill='x', padx=20, pady=(0, 8))

        # Results preview
        ttk.Label(self, text="Preview", font=('Segoe UI', 11, 'bold'),
                  foreground='#1F3864').pack(anchor='w', padx=20, pady=(4, 4))

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill='both', expand=True, padx=20, pady=(0, 12))

        cols = ('Group Person ID', 'Name', 'Date', 'First In', 'Last Out',
                'Effective Hrs', 'Total Hrs', 'Company', 'Remarks')
        self._tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=10)
        widths = (110, 160, 100, 80, 80, 100, 90, 150, 220)
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, anchor='w')

        vsb = ttk.Scrollbar(tree_frame, orient='vertical',   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side='right',  fill='y')
        hsb.pack(side='bottom', fill='x')
        self._tree.pack(side='left', fill='both', expand=True)


    def _set_yesterday(self):
        d = (date.today() - timedelta(days=1)).isoformat()
        self._from.delete(0, 'end'); self._from.insert(0, d)
        self._to.delete(0, 'end'); self._to.insert(0, d)

    def _set_this_week(self):
        today = date.today()
        mon = today - timedelta(days=today.weekday())
        self._from.delete(0, 'end'); self._from.insert(0, mon.isoformat())
        self._to.delete(0, 'end'); self._to.insert(0, today.isoformat())

    def _set_this_month(self):
        today = date.today()
        start = today.replace(day=1)
        self._from.delete(0, 'end'); self._from.insert(0, start.isoformat())
        self._to.delete(0, 'end'); self._to.insert(0, today.isoformat())

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._folder.delete(0, 'end')
            self._folder.insert(0, folder)

    def _open_folder(self):
        folder = self._folder.get().strip()
        if folder and Path(folder).exists():
            os.startfile(folder)
        else:
            messagebox.showinfo("Folder", f"Folder not found: {folder}")

    def _generate(self):
        try:
            from_date = date.fromisoformat(self._from.get().strip())
            to_date = date.fromisoformat(self._to.get().strip())
        except ValueError:
            messagebox.showerror("Date Error", "Please enter dates in YYYY-MM-DD format.")
            return

        if from_date > to_date:
            messagebox.showerror("Date Error", "From date must be before To date.")
            return

        self._records = []
        self._xlsx_path = ''
        self._pdf_path = ''
        self._send_btn.configure(state='disabled')
        self._progress.start()
        self._status.set("Fetching data from Lenel database…")

        def run():
            try:
                threshold   = database.get_archive_threshold_days()
                cutoff      = date.today() - timedelta(days=threshold)
                use_live    = to_date   >= cutoff
                use_archive = from_date < cutoff

                all_events   = []
                all_emp_info = {}

                if use_live:
                    live_from = cutoff if use_archive else from_date
                    self.after(0, lambda: self._status.set("Fetching live punch events…"))
                    live_events, live_emp_info = database.get_events_from_view(live_from, to_date)
                    all_events.extend(live_events)
                    all_emp_info.update(live_emp_info)

                if use_archive:
                    arch_to = (cutoff - timedelta(days=1)) if use_live else to_date
                    self.after(0, lambda: self._status.set("Fetching archive punch events…"))
                    try:
                        arch_events, arch_emp_info = database.get_events_from_archive_view(
                            from_date, arch_to)
                        all_events.extend(arch_events)
                        all_emp_info.update(arch_emp_info)
                    except Exception as arch_e:
                        arch_msg = f"Archive query failed: {arch_e}"
                        config.log_activity(arch_msg, 'ERROR')
                        self.after(0, lambda m=arch_msg: self._done_error(m))
                        return

                events   = all_events
                emp_info = all_emp_info

                report_dates = []
                d = from_date
                while d <= to_date:
                    report_dates.append(d)
                    d += timedelta(days=1)

                self.after(0, lambda: self._status.set("Calculating attendance…"))
                records = attendance.calculate_attendance(events, emp_info, report_dates)

                title = self._title.get().strip() or "Attendance Report"
                folder = self._folder.get().strip()
                Path(folder).mkdir(parents=True, exist_ok=True)
                date_str = (from_date.strftime('%d-%b-%Y') if from_date == to_date
                            else f"{from_date.strftime('%d-%b-%Y')}_to_{to_date.strftime('%d-%b-%Y')}")
                ts   = datetime.now().strftime('%H%M%S')
                safe = title.replace(' ', '_').replace('/', '-')

                xlsx_path = ''
                pdf_path = ''

                if self._excel_var.get():
                    self.after(0, lambda: self._status.set("Generating Excel…"))
                    xlsx_path = str(Path(folder) / f"{safe}_{date_str}_{ts}.xlsx")
                    report_excel.generate_excel(records, title, from_date, to_date, xlsx_path,
                                                raw_events=events, reader_map={})

                if self._pdf_var.get():
                    self.after(0, lambda: self._status.set("Generating PDF…"))
                    pdf_path = str(Path(folder) / f"{safe}_{date_str}_{ts}.pdf")
                    report_pdf.generate_pdf(records, title, from_date, to_date, pdf_path)

                self.after(0, lambda: self._done_ok(records, xlsx_path, pdf_path))

            except PermissionError:
                self.after(0, lambda: self._done_error(
                    "Cannot save the report file — it is open in another application "
                    "(e.g. Excel).\n\nClose the file and generate again."))
            except Exception as e:
                err_msg = str(e)
                config.log_activity(f"Report generation error: {err_msg}", 'ERROR')
                self.after(0, lambda m=err_msg: self._done_error(m))

        threading.Thread(target=run, daemon=True).start()

    def _done_ok(self, records, xlsx_path, pdf_path):
        self._progress.stop()
        self._records = records
        self._xlsx_path = xlsx_path
        self._pdf_path = pdf_path
        self._status.set(f"Done — {len(records)} records generated.")
        self._send_btn.configure(state='normal')
        self._populate_tree(records)
        config.log_activity(f"Manual report: {len(records)} records, {xlsx_path or pdf_path}", 'INFO')

    def _done_error(self, msg):
        self._progress.stop()
        short = msg if len(msg) <= 120 else msg[:117] + '...'
        self._status.set(f"Error: {short} — see Activity Log for details")
        if "open in another application" in msg:
            messagebox.showerror("Report Error", msg)

    def _populate_tree(self, records):
        for item in self._tree.get_children():
            self._tree.delete(item)
        for rec in records:
            self._tree.insert('', 'end', values=(
                rec.ssno, rec.name,
                rec.report_date.strftime('%d-%b-%Y') if rec.report_date else '',
                rec.first_punch_str, rec.last_punch_str,
                rec.effective_hours_str, rec.total_hours_str,
                rec.company_name, rec.remarks_str,
            ))

    def _send_email(self):
        if not self._records:
            return
        dlg = _EmailDialog(self, self._xlsx_path, self._pdf_path)
        self.wait_window(dlg)

    def refresh(self):
        pass


class _EmailDialog(tk.Toplevel):
    def __init__(self, parent, xlsx_path, pdf_path):
        super().__init__(parent)
        self.title("Send Report by Email")
        self.geometry("520x380")
        self.resizable(False, False)
        self._xlsx = xlsx_path
        self._pdf = pdf_path
        self._build()

    def _build(self):
        f = ttk.Frame(self, padding=16)
        f.pack(fill='both', expand=True)

        ttk.Label(f, text="Recipients (comma-separated):").grid(row=0, column=0, sticky='w', pady=4)
        self._to = ttk.Entry(f, width=55)
        self._to.grid(row=0, column=1, sticky='w', padx=6)

        ttk.Label(f, text="CC:").grid(row=1, column=0, sticky='w', pady=4)
        self._cc = ttk.Entry(f, width=55)
        self._cc.grid(row=1, column=1, sticky='w', padx=6)

        ttk.Label(f, text="Subject:").grid(row=2, column=0, sticky='w', pady=4)
        self._subject = ttk.Entry(f, width=55)
        self._subject.insert(0, "Attendance Report")
        self._subject.grid(row=2, column=1, sticky='w', padx=6)

        ttk.Label(f, text="Body:").grid(row=3, column=0, sticky='nw', pady=4)
        self._body = tk.Text(f, width=42, height=6, font=('Segoe UI', 9))
        self._body.insert('1.0', "Please find the attendance report attached.")
        self._body.grid(row=3, column=1, sticky='w', padx=6)

        attach_frame = ttk.Frame(f)
        attach_frame.grid(row=4, column=0, columnspan=2, sticky='w', pady=6)
        self._attach_xlsx = tk.BooleanVar(value=bool(self._xlsx))
        self._attach_pdf = tk.BooleanVar(value=bool(self._pdf))
        if self._xlsx:
            ttk.Checkbutton(attach_frame, text="Attach Excel", variable=self._attach_xlsx).pack(side='left')
        if self._pdf:
            ttk.Checkbutton(attach_frame, text="Attach PDF", variable=self._attach_pdf).pack(side='left', padx=8)

        btn_row = ttk.Frame(f)
        btn_row.grid(row=5, column=0, columnspan=2, sticky='e', pady=8)
        ttk.Button(btn_row, text="Send", command=self._send).pack(side='left', padx=4)
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side='left')

        self._status = ttk.Label(f, text="", foreground='#555555')
        self._status.grid(row=6, column=0, columnspan=2, sticky='w')

    def _send(self):
        to_raw = self._to.get().strip()
        if not to_raw:
            messagebox.showerror("Email", "Please enter at least one recipient.", parent=self)
            return
        recipients = [e.strip() for e in to_raw.split(',') if e.strip()]
        cc = [e.strip() for e in self._cc.get().split(',') if e.strip()]
        subject = self._subject.get().strip() or "Attendance Report"
        body = self._body.get('1.0', 'end').strip()
        attachments = []
        if self._xlsx and self._attach_xlsx.get():
            attachments.append(self._xlsx)
        if self._pdf and self._attach_pdf.get():
            attachments.append(self._pdf)

        self._status.configure(text="Sending…")
        self.update()

        ok, msg = emailer.send_report_email(recipients, cc, subject, body, attachments)
        if ok:
            messagebox.showinfo("Email Sent", msg, parent=self)
            self.destroy()
        else:
            messagebox.showerror("Email Failed", msg, parent=self)
            self._status.configure(text=f"Error: {msg}")
