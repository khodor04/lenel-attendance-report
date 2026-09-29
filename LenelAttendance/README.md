# Lenel Attendance Report Manager
### Complete User & Administrator Guide

---

## Table of Contents

1. [What This Application Does](#1-what-this-application-does)
2. [System Requirements](#2-system-requirements)
3. [Installation](#3-installation)
4. [First-Time Setup (Step by Step)](#4-first-time-setup-step-by-step)
5. [Settings — Database](#5-settings--database)
6. [Settings — Email / SMTP](#6-settings--email--smtp)
7. [Settings — Reader Mapping](#7-settings--reader-mapping)
8. [Settings — Attribute Mapping](#8-settings--attribute-mapping)
9. [Report Profiles (Scheduled Reports)](#9-report-profiles-scheduled-reports)
10. [Generate Report (Manual)](#10-generate-report-manual)
11. [Dashboard](#11-dashboard)
12. [Activity Log](#12-activity-log)
13. [System Tray — Close to Tray](#13-system-tray--close-to-tray)
14. [Auto-Start at Windows Login](#14-auto-start-at-windows-login)
15. [Windows Service (Recommended for 24/7 Operation)](#15-windows-service-recommended-for-247-operation)
16. [Manual Task Scheduler Setup](#16-manual-task-scheduler-setup)
17. [Backup & Restore Settings](#17-backup--restore-settings)
18. [How Attendance Is Calculated](#18-how-attendance-is-calculated)
19. [Understanding the Excel Report](#19-understanding-the-excel-report)
20. [Troubleshooting](#20-troubleshooting)

---

## 1. What This Application Does

The **Lenel Attendance Report Manager** connects directly to the Lenel OnGuard access-control database installed on the same PC. It reads every card-swipe event, pairs entry and exit punches per employee per day, and produces professional attendance reports in **Excel (.xlsx)** and **PDF** formats.

Reports can be:
- Generated **manually** for any date range with a single click
- Sent **automatically by email** on a daily, weekly, or monthly schedule
- Filtered by **company / division**
- Delivered to **different recipient lists** under different profiles

**Key calculated fields per employee per day:**

| Field | Description |
|---|---|
| First Punch In | Earliest entry swipe of the day |
| Last Punch Out | Latest exit swipe of the day |
| Effective Hours | Sum of all paired entry→exit intervals (breaks excluded) |
| Total Hours | Span from first entry to last exit (includes breaks) |
| Remarks | Missing punches, out of office >2 hours, unpaired swipes |

---

## 2. System Requirements

| Requirement | Detail |
|---|---|
| Operating System | Windows 10 / Windows 11 (64-bit) |
| Lenel OnGuard | Must be installed on the **same machine** |
| SQL Server ODBC Driver | Already installed by Lenel OnGuard — no action needed |
| Network | Not required — connects to local SQL Server Express |
| Internet | Required only for sending emails via SMTP |

> **No Python installation required.** The `.exe` is completely self-contained.

---

## 3. Installation

1. Copy both executables to a permanent folder on the PC.
   Recommended location: `C:\Program Files\LenelAttendance\`

   | File | Purpose |
   |---|---|
   | `LenelAttendance.exe` | Main GUI application |
   | `LenelAttendanceSvc.exe` | Windows service (for 24/7 unattended operation) |

2. Double-click `LenelAttendance.exe` to launch.

3. **Install the code signing certificate** (one-time, first machine only).
   Double-click `LenelAttendance_CodeSign.cer` → **Install Certificate** → Local Machine →
   **Trusted Publishers** and also **Trusted Root Certification Authorities** → Finish.

4. On first launch, the application creates **`lenel_app.db`** in the same folder as the exe. This file stores all your settings, reader mappings, and report profiles. **Do not delete it.**

> The executables are digitally signed by **Khodor Ghalayini**. After installing the certificate above, no SmartScreen warning will appear. If the certificate has not been installed yet, Windows may show a prompt — click **More info** → **Run anyway**.

---

## 4. First-Time Setup (Step by Step)

Follow these steps in order the very first time you run the app on a new machine.

### Step 1 — Verify Database Connection
Go to **Settings → Database**.
- Server should be `localhost`
- Database should be `AccessControl`
- Authentication should be `windows`

Click **Test Connection**. You should see: *Connection successful*

If it fails, see [Troubleshooting → Cannot connect to database](#troubleshooting).

### Step 2 — Configure Reader Mapping
Go to **Settings → Reader Mapping**.
- Click **Sync from Lenel** — this pulls all card readers from Lenel OnGuard
- Click **Auto-detect (En/Ex)** — readers whose name ends in `En` are tagged ENTRY, `Ex` are tagged EXIT
- Review the list and correct any that were misidentified (double-click a row to cycle: IGNORE → ENTRY → EXIT → IGNORE)
- Click **Save Mapping**

> This step is critical. Without correct reader mapping, no attendance can be calculated.

### Step 3 — Configure Email
Go to **Settings → Email / SMTP**.
- Enter your SMTP server, port, username, password, and From address
- Click **Test SMTP** to verify it works before setting up profiles

### Step 4 — Create Report Profiles
Go to **Report Profiles**.
- Click **New Profile** and fill in the form (see Section 9 for full details)
- Create one profile per report type (e.g. daily report for Company A, weekly report for Company B)

### Step 5 — Set Up Unattended Scheduling

**Option A — Windows Service (recommended):** Go to **Settings → System → Windows Service** and click **Install Service**. The service runs in the background even when no user is logged in and starts automatically with Windows. See [Section 15](#15-windows-service-recommended-for-247-operation) for full details.

**Option B — Auto-Start at Login:** Go to **Settings → System** and click **Install at Startup**. The app starts automatically when the Windows user logs in (requires the user to be logged in for reports to run).

### Step 6 — Export a Backup
Go to **Settings → System → Backup & Restore**.
- Click **Export Backup** and save the file to a USB drive or network share
- Label it with today's date

---

## 5. Settings — Database

| Field | Description |
|---|---|
| SQL Server | Hostname or IP. Use `localhost` when Lenel is on the same machine |
| Database Name | Always `AccessControl` for Lenel OnGuard |
| Authentication | `windows` = use Windows login (recommended). `sql` = SQL username/password |
| UTC Offset | Hours ahead of UTC. UAE/Oman = **4**, KSA/Qatar/Lebanon = **3**, Egypt = **2** |
| Output Folder | Default folder where Excel and PDF files are saved |

Click **Save Settings** then **Test Connection** to verify.

---

## 6. Settings — Email / SMTP

| Field | Description |
|---|---|
| SMTP Server | Your mail server address (e.g. `smtp.office365.com`, `smtp.gmail.com`) |
| Port | 587 for STARTTLS (most common), 465 for SSL, 25 for plain |
| Username | Your email address or login |
| Password | Email password or App Password |
| From Address | The sender address that appears on reports |
| Encryption | STARTTLS (port 587) is recommended |

**Gmail users:** You must use an **App Password**, not your regular password.
Go to Google Account → Security → 2-Step Verification → App Passwords → create one for "Mail".

**Office 365 users:** Use `smtp.office365.com` port `587` STARTTLS with your full email as username.

---

## 7. Settings — Reader Mapping

This screen maps every physical card reader in Lenel OnGuard to one of three types:

| Type | Meaning |
|---|---|
| ENTRY | This reader records employees entering the building / office |
| EXIT | This reader records employees leaving |
| IGNORE | This reader is not used for attendance (e.g. server room, parking) |

**Controls:**
- **Sync from Lenel** — pulls the latest reader list from the Lenel database. Safe to run again any time; it never changes existing assignments.
- **Auto-detect (En/Ex)** — inspects reader names. If the name ends with ` En` it becomes ENTRY; ` Ex` becomes EXIT. All others stay IGNORE.
- **Double-click any row** — cycles the type: IGNORE → ENTRY → EXIT → IGNORE
- **Save Mapping** — writes all changes to the local database

> You must click **Save Mapping** before your changes take effect. Leaving the tab without saving will discard changes.

---

## 8. Settings — Attribute Mapping

| Field | Description |
|---|---|
| Company Name Source | Leave as `division` — company names come from the Lenel DIVISION table |
| Group Person ID Field | The column name in Lenel's UDFEMP table that holds the 7-digit Group Person ID. Leave blank if not configured in Lenel yet. |

Click **Load UDFEMP Columns** to see all available columns in Lenel's custom employee fields table, then type the correct column name into the Group Person ID field.

---

## 9. Report Profiles (Scheduled Reports)

A **Report Profile** defines one automatic scheduled report. You can have as many profiles as you need — one per company, per frequency, or per recipient group.

### Creating a Profile

Click **New Profile**. Fill in the following:

**Basic Info**

| Field | Example | Description |
|---|---|---|
| Profile Name | `Maire Daily` | Internal name shown in the app |
| Report Title | `Maire Attendance Report` | Appears as the heading inside the report |
| Email Subject | `{title} for {date}` | Subject line of the email. `{title}` and `{date}` are replaced automatically |

The subject `{title} for {date}` will produce:
`Maire Attendance Report for 19-Jun-26`

**Output**

| Field | Description |
|---|---|
| Output Folder | Base folder for this profile's reports. A subfolder named after the profile is created automatically inside it (e.g. `LenelReports\Maire Daily\`). Leave blank to use the global Output Folder from Settings → Database. |
| Include Excel | Tick to attach an `.xlsx` file |
| Include PDF | Tick to attach a `.pdf` file |

> Each profile saves into its own subfolder so reports from different profiles never mix.

**Company Filter**

Select one or more companies from the list. Only employees belonging to those companies will appear in this report. Leave all unchecked to include everyone.

**Schedule**

| Field | Options | Description |
|---|---|---|
| Frequency | Daily / Weekly / Monthly | How often the report runs |
| Run Time | e.g. `07:00` | Time of day to generate and send |
| Day of Week | Monday–Sunday | Only for Weekly frequency |
| Day of Month | 1–31 | Only for Monthly frequency |

For a **daily report**, the report covers **yesterday** (the previous calendar day).
For a **weekly report**, the report covers **last Monday to last Sunday**. The report runs once per week on the configured day, generates the Excel/PDF for the full previous week, saves it to the output folder, and emails it.
For a **monthly report**, the report covers **the entire previous calendar month**.

**Recipients**

| Field | Example | Description |
|---|---|---|
| To (Recipients) | `manager@company.com, hr@company.com` | Main recipients, comma-separated |
| CC | `director@company.com` | Optional CC, comma-separated |
| Email Body | `Please find the attendance report attached.` | Body text of the email |

**Enabled toggle** — uncheck to temporarily pause a profile without deleting it.

### Editing / Deleting a Profile

Select a profile in the list and click **Edit** or **Delete**.

---

## 10. Generate Report (Manual)

Use this tab to generate a report immediately for any date range.

1. Set **From Date** and **To Date** in `YYYY-MM-DD` format, or use the quick buttons:
   - **Yesterday** — single day
   - **This Week** — Monday to today
   - **This Month** — 1st of month to today

2. Enter a **Report Title** (appears as the heading in the file)

3. Choose the **Output Folder** where files will be saved

4. Tick **Excel** and/or **PDF**

5. Click **Generate Report**

The preview table at the bottom shows all records. When done:
- Click **Open Output Folder** to view the files
- Click **Send by Email** to email the files immediately without using a profile

> To filter by company, create a Report Profile (Section 9) with the desired company filter and click **Run Now** from the Dashboard.

---

## 11. Dashboard

The Dashboard shows at a glance:
- All report profiles with their last run time and status
- Whether the scheduler is running
- A **Run Now** button on each profile to trigger it immediately without waiting for the schedule

---

## 12. Activity Log

Every action the application takes is recorded here: report generation, emails sent, errors, settings changes.

- Use the **Level** filter to show only ERRORS or WARNINGS
- Use the **Search** box to find specific entries
- Logs older than 60 days are automatically pruned

---

## 13. System Tray — Close to Tray

When you click the **X** (close button) on the main window, the application **does not exit**. It hides to the Windows system tray (notification area, bottom-right of the taskbar).

The scheduler continues running in the background. Reports will still be generated and emailed on schedule.

**To reopen the window:** Double-click the tray icon, or right-click it and choose **Open Lenel Attendance**.

**To fully exit the application:** Right-click the tray icon → **Exit**.

> Note: If you fully exit, no scheduled reports will run until you reopen the app. For 24/7 unattended operation, always use the tray instead of Exit, and make sure Auto-Start is installed (Section 14).

---

## 14. Auto-Start at Windows Login

Go to **Settings → System** and click **Install at Startup**.

This registers the application with **Windows Task Scheduler** to:
- Launch automatically every time any user logs in to Windows
- Restart automatically if it crashes (up to 5 attempts, 2 minutes apart)

To stop the auto-start: click **Remove from Startup**.

The **Status** label confirms whether the app is currently registered.

> If the Install button returns an error, use the manual method below (Section 16). For unattended 24/7 operation, the Windows Service (Section 15) is the better choice.

---

## 15. Windows Service (Recommended for 24/7 Operation)

The **Windows Service** runs scheduled reports in the background as a system service, even when no user is logged in to Windows. It starts automatically with the PC and survives user logouts.

### Why use the service instead of the tray app?

| | Tray App | Windows Service |
|---|---|---|
| Runs when no user is logged in | ✗ | ✓ |
| Starts with Windows (no login needed) | ✗ | ✓ |
| Visible to the user | ✓ | ✗ |
| Manual report generation | ✓ | ✗ |

Use both together: install the service for 24/7 scheduling, and keep the GUI for manual reports and settings. The GUI automatically detects when the service is running and skips its own internal scheduler to avoid double-runs.

### Service Controls

Go to **Settings → System → Windows Service**.

| Button | Action |
|---|---|
| **Install Service** | Registers `LenelAttendanceSvc.exe` as a Windows service and starts it |
| **Uninstall Service** | Stops and removes the service |
| **Start** | Starts a stopped (but installed) service |
| **Stop** | Stops the service without uninstalling it |

The current state is shown next to the controls: **Running ✓** (green), **Stopped** (orange), or **Not installed** (grey).

> **Administrator rights required.** If the Install/Uninstall buttons fail, right-click `LenelAttendance.exe` and choose **Run as administrator**, then retry.

### What the service uses

The service reads all settings from the same `lenel_app.db` as the GUI. Configure everything via the GUI first (database, email, reader mapping, report profiles), then install the service.

### Service exe location

`LenelAttendanceSvc.exe` must be in the **same folder** as `LenelAttendance.exe` and `lenel_app.db`.

### Auto-Save Daily Report

Go to **Settings → System → Auto-Save Daily Report**.

This is a built-in safety net that runs every day at the configured time (default **01:00**) and saves yesterday's full attendance report (all employees, no company filter) to a local folder — **with no email**. It runs regardless of whether any report profiles are configured.

| Setting | Description |
|---|---|
| Enable auto-save | Turn on/off the daily auto-save |
| Run Time | Time of day to run (24-hour format, default `01:00`) |
| Save Folder | Where to save the daily files (default: `Documents\LenelReports\Automated Reports`) |

Reports are saved as Excel files named `Auto-Save_<date>_<time>.xlsx`. Click **Open Folder** to browse them.

> The auto-save requires either the Windows Service or the GUI app to be running at the configured time.

---

## 16. Manual Task Scheduler Setup

If the **Install at Startup** button fails (e.g. due to permissions), follow these steps to register the app manually using Windows Task Scheduler.

### Step 1 — Open Task Scheduler

Press **Win + R**, type `taskschd.msc`, press **Enter**.

Or: Start Menu → search **Task Scheduler** → open it.

### Step 2 — Create a New Task

In the right panel, click **Create Task** (not "Create Basic Task" — you need the full form).

### Step 3 — General Tab

| Setting | Value |
|---|---|
| Name | `LenelAttendanceManager` |
| Description | `Lenel Attendance Report Manager - auto start` |
| Security options | Select **Run only when user is logged on** |
| Configure for | Windows 10 / Windows 11 |

### Step 4 — Triggers Tab

1. Click **New…**
2. Set **Begin the task** to: `At log on`
3. Set **Specific user** to the Windows user account that normally uses this PC
4. Make sure **Enabled** is ticked
5. Click **OK**

### Step 5 — Actions Tab

1. Click **New…**
2. **Action:** `Start a program`
3. **Program/script:** Click Browse and navigate to `LenelAttendance.exe`
   - Example: `C:\Program Files\LenelAttendance\LenelAttendance.exe`
4. **Start in (optional):** Enter the folder containing the exe
   - Example: `C:\Program Files\LenelAttendance\`
   - This is important — it ensures `lenel_app.db` is found next to the exe
5. Click **OK**

### Step 6 — Conditions Tab

Uncheck **"Start the task only if the computer is on AC power"** — otherwise the task won't run on a laptop on battery.

### Step 7 — Settings Tab

| Setting | Value |
|---|---|
| Allow task to be run on demand | ✅ Checked |
| If the task is already running | `Do not start a new instance` |
| If the running task does not end when requested, force it to stop | ✅ Checked |

**For automatic restart on crash:**

1. Tick **If the task fails, restart every:** `2 minutes`
2. Set **Attempt to restart up to:** `5` times

### Step 8 — Save the Task

Click **OK**. If prompted, enter your Windows password to confirm.

### Step 9 — Test It

Right-click **LenelAttendanceManager** in the task list → **Run**.
The application should open. If it doesn't, right-click → **Properties** → **History** tab to see the error.

### How to Edit or Delete the Task Later

Open Task Scheduler → expand **Task Scheduler Library** → find **LenelAttendanceManager** → right-click → **Properties** to edit, or **Delete** to remove.

---

## 17. Backup & Restore Settings

All application data — settings, reader mapping, and report profiles — are stored in a single SQLite file: **`lenel_app.db`** (located in the same folder as the exe).

**If this file is lost, all configuration must be re-entered from scratch.** Back it up regularly.

### Export a Backup

Go to **Settings → System → Backup & Restore** → click **Export Backup…**

Choose a location (USB drive, network share, or cloud folder) and save. The filename includes the date and time automatically: `lenel_backup_20260627_0930.db`

**Recommended schedule:** Export a backup after any configuration change and once a month.

### Restore a Backup

Go to **Settings → System → Backup & Restore** → click **Import / Restore…**

Select the backup file. Confirm the warning (this replaces all current settings). After restoring, restart the application.

### Manual Backup (Alternative)

You can also back up manually by simply copying `lenel_app.db` to a safe location. To restore, copy it back next to the exe and restart the app.

### What the backup contains

| Included | Not included |
|---|---|
| Database connection settings | Generated Excel/PDF report files |
| Email / SMTP credentials | Lenel OnGuard data |
| Reader mapping (Entry/Exit assignments) | Activity log |
| All report profiles and schedules | |
| Attribute mapping | |

---

## 18. How Attendance Is Calculated

### Entry & Exit Pairing

For each employee on each day, the application collects all card-swipe events from readers marked as ENTRY or EXIT. It then pairs them chronologically:

```
ENTRY 08:02  →  EXIT 13:15   =  5h 13m  (effective)
ENTRY 14:00  →  EXIT 18:30   =  4h 30m  (effective)

Effective Hours  =  5h 13m + 4h 30m  =  9h 43m
Total Hours      =  08:02 to 18:30   =  10h 28m  (includes the 45-min break)
```

### Remarks Generated Automatically

| Remark | Meaning |
|---|---|
| `Out of office >2h (Xh YYm): HH:MM – HH:MM` | Gap between one exit and the next entry exceeded 2 hours within the same day. Shows exact out and back times. |
| `Missing Entry Punch` | The day has exit events but no entry event |
| `Missing Exit Punch` | The day has entry events but no exit event |
| `Unpaired Entry Punch(es): N` | More entries than exits; N entries could not be paired |
| `Unpaired Exit Punch(es): N` | More exits than entries; N exits could not be paired |

### Row Highlighting in Reports

| Colour | Meaning |
|---|---|
| Yellow | Employee was out of office for more than 2 hours |
| Light red | Any other remark (missing punch, unpaired swipe) |
| Light blue | Alternating rows (no issue) |
| White | Normal row (no issue) |

### What is NOT flagged

- Overnight gaps are ignored. An employee who leaves at 18:00 and returns at 08:00 the next day is not flagged.
- Only intra-day gaps (within the same working day) are checked for the >2-hour rule.

---

## 19. Understanding the Excel Report

Each Excel file contains three sheets:

### Sheet 1 — Daily Summary

The main report. One row per employee per day.

| Column | Description |
|---|---|
| Name | Employee full name from Lenel |
| Badge No | Badge number from Lenel |
| Date | The working date |
| First Punch In | Time of first entry swipe |
| Last Punch Out | Time of last exit swipe |
| Effective Hours | Total productive time (breaks excluded) |
| Total Hours | First in to last out (breaks included) |
| Remarks | Automatic notes about anomalies |
| Group Person ID | 7-digit custom ID (if configured in Lenel) |
| Company Name | Division / company from Lenel |

Time columns (First Punch In, Last Punch Out, Effective Hours, Total Hours) are stored as real Excel time values — you can sum them, format them, or use them in formulas.

### Sheet 2 — Detailed Report

One row per entry→exit pair. Shows every individual interval the employee worked, with the specific reader names and the calculated time for that interval.

### Sheet 3 — RAWDATA

Raw paired punch records with full date+time stamps. Useful for auditing or importing into other systems.

---

## 20. Troubleshooting

### Cannot connect to database

**Symptom:** Settings → Database → Test Connection shows an error.

**Check:**
1. Lenel OnGuard SQL Server service is running.
   Open Services (`Win + R` → `services.msc`) and look for **SQL Server (SQLEXPRESS)** — it must be **Running**.
2. The database name is exactly `AccessControl` (case-sensitive).
3. The current Windows user has access to the database. Lenel OnGuard normally grants this automatically to the Lenel service account and local admins.

---

### No attendance records generated

**Symptom:** Report shows 0 records.

**Check:**
1. Settings → Reader Mapping — at least one reader must be tagged ENTRY and one EXIT.
2. The date range contains actual working days. Check the Activity Log for event counts.
3. The UTC Offset is correct. If events are stored in UTC+4 and you have offset set to 0, the date range query will miss all records.

---

### Reader Mapping shows no readers

**Symptom:** Sync from Lenel returns nothing.

**Check:**
1. Database connection is working (Test Connection in Settings → Database).
2. There are recent card-swipe events in the Lenel database. The reader list is pulled from the T&A view which only contains readers that have had activity. If no events exist in the date range, no readers will appear.

---

### Email sending fails

**Symptom:** Test SMTP returns an error or emails are not received.

**Check:**
1. SMTP server, port, and credentials are correct.
2. For Gmail: use an App Password (not your regular password) and enable STARTTLS port 587.
3. For Office 365: your account must allow SMTP AUTH. This may need to be enabled by your IT administrator in the Microsoft 365 admin portal.
4. Firewall or antivirus is not blocking outbound port 587 or 465.

> **Automatic retries:** The application retries failed email sends up to **3 times**, waiting **30 seconds** between each attempt. If all 3 attempts fail, the error is logged in the Activity Log with level ERROR. The report file is always saved locally regardless of email outcome.

---

### App not starting at Windows login

**Symptom:** PC restarts but the app doesn't open automatically.

**Check:**
1. Go to **Settings → System** — status should say "Registered".
2. If not registered, click **Install at Startup** again.
3. If Install at Startup fails with a permissions error, follow the [Manual Task Scheduler Setup](#16-manual-task-scheduler-setup) steps.
4. Open Task Scheduler, find **LenelAttendanceManager**, right-click → **Run** manually to test. Check the History tab for errors.

---

### Scheduled report did not run

**Symptom:** A profile is enabled but the email was not received.

**Check:**
1. If using the Windows Service (Section 15): go to **Settings → System → Windows Service** and confirm status shows **Running ✓**. If not, click **Start**.
2. If using the tray app: the application must have been running at the scheduled time (check tray icon or Activity Log).
3. The **Run Time** in the profile is set correctly (24-hour format, e.g. `07:00`).
4. Check **Activity Log** — filter by the profile name to see if it ran and what happened.
5. Check that the correct **frequency** and **day** are set (weekly profiles only run on the selected day of the week).

---

### Tray icon is not visible

**Symptom:** You closed the window but cannot find the tray icon.

The icon may be hidden in the overflow tray. Click the **^** arrow in the bottom-right taskbar to expand hidden tray icons. You can drag the Lenel icon out of the overflow area to keep it permanently visible.

---

### Group Person ID shows blank

This field requires a custom UDF column to be added in Lenel OnGuard by your system administrator. Once added, go to **Settings → Attribute Mapping**, click **Load UDFEMP Columns**, find the column name, enter it in the Group Person ID Field, and save.

---

*Lenel Attendance Report Manager — v2.0*
*Developed by Khodor Ghalayini*
*For support contact your system administrator.*
