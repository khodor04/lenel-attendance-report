The easiest way to add this: go to your GitHub repo page → click **"Add a README"** (GitHub shows this button on empty repos) → paste the content below → click **Commit**.

Here's the content — copy everything between the lines:

---

```markdown
# Lenel OnGuard Attendance Report Automation

> A professional Windows desktop application that automates employee attendance reporting from the **Lenel OnGuard** access control system. Built for a client in the UAE with a full Windows service, scheduled email delivery, and multi-format output.

---

## What it does

Connects to the Lenel OnGuard SQL Server database, reads every card-swipe event, pairs entry/exit punches per employee per day, and produces formatted attendance reports.

- **Excel reports** — 4 sheets: Daily Summary, Detailed Report, Raw Data, and a pivot Summary table
- **PDF reports** — print-ready, same data as Excel
- **Scheduled delivery** — runs as a Windows service, sends reports by email on daily / weekly / monthly schedules
- **Multiple profiles** — per-company filters, custom recipient lists, custom schedules
- **Smart remarks** — flags missing punches, out-of-office gaps >2h, unpaired swipes, and days under 8 effective hours
- **Badge number tracking** — shows the actual card number per swipe, handles badge replacements correctly

---

## Tech Stack

| | |
|---|---|
| Language | Python 3.13 |
| GUI | tkinter / ttkbootstrap |
| Excel | openpyxl |
| PDF | reportlab |
| Database | SQL Server via pyodbc (Lenel OnGuard `AccessControl` DB) |
| Config | SQLite |
| Email | smtplib |
| Windows Service | pywin32 |
| Packaging | PyInstaller — single `.exe` |

---

## Architecture

```
LenelAttendance/
├── main.py              # GUI entry point + system tray
├── attendance.py        # Punch pairing, effective hours, remarks logic
├── database.py          # SQL Server queries through secured views
├── report_excel.py      # 4-sheet Excel workbook generator
├── report_pdf.py        # PDF generator
├── scheduler.py         # Background job scheduler
├── svc.py               # Windows service wrapper
├── svc_manager.py       # Install/start/stop service from UI
├── config.py            # SQLite settings + activity logging
├── emailer.py           # SMTP with retry logic
└── tabs/                # UI tabs (dashboard, generate, profiles, settings, logs)
```

---

## Security

The app connects via **three secured SQL views** (`-App` suffix). The `ReportUser` SQL account has `SELECT` only on those views — no direct table access, no write access.

---

## Setup

```bash
pip install -r LenelAttendance/requirements.txt
python LenelAttendance/main.py
```

Run `LenelAttendance/SQL_SETUP_REV3.sql` on the `AccessControl` database first to create the views and the `ReportUser` login.

---

*Developed by [Khodor Ghalayini](https://github.com/khodor04)*
```
