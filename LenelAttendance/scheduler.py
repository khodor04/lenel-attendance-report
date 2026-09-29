import threading
import time as time_module
import json
from datetime import datetime, date, timedelta
from pathlib import Path

import config
import database
import attendance
import report_excel
import report_pdf
import emailer

_thread = None
_running = False
_status_callback = None


def set_status_callback(fn):
    global _status_callback
    _status_callback = fn


def _notify(msg):
    if _status_callback:
        try:
            _status_callback(msg)
        except Exception:
            pass


def _safe_folder_name(name: str) -> str:
    return (''.join(c if c.isalnum() or c in ' -_' else '_' for c in name)).strip() or 'Report'


def generate_and_send(profile: dict, start_date: date, end_date: date) -> tuple:
    name = profile.get('name', 'Report')
    config.log_activity(f"[{name}] Starting — {start_date} to {end_date}", 'INFO')
    _notify(f"Running: {name}…")

    try:
        threshold = database.get_archive_threshold_days()
        cutoff      = date.today() - timedelta(days=threshold)
        use_live    = end_date   >= cutoff
        use_archive = start_date < cutoff

        all_events   = []
        all_emp_info = {}

        if use_live:
            live_from   = cutoff if use_archive else start_date
            live_events, live_emp_info = database.get_events_from_view(live_from, end_date)
            all_events.extend(live_events)
            all_emp_info.update(live_emp_info)
            config.log_activity(f"[{name}] {len(live_events)} live events fetched", 'INFO')

        if use_archive:
            arch_to = (cutoff - timedelta(days=1)) if use_live else end_date
            arch_events, arch_emp_info = database.get_events_from_archive_view(start_date, arch_to)
            all_events.extend(arch_events)
            all_emp_info.update(arch_emp_info)
            config.log_activity(f"[{name}] {len(arch_events)} archive events fetched", 'INFO')

        events   = all_events
        emp_info = all_emp_info
        config.log_activity(f"[{name}] {len(events)} total events", 'INFO')

        # Company filter — stored as division name strings in profile
        company_filter = json.loads(profile.get('companies') or '[]')
        if company_filter:
            allowed = set(company_filter)
            allowed_emp = {eid for eid, inf in emp_info.items()
                           if inf.get('company_name', '') in allowed}
            events   = [e for e in events if e['emp_id'] in allowed_emp]
            emp_info = {k: v for k, v in emp_info.items() if k in allowed_emp}
            config.log_activity(
                f"[{name}] Company filter: {sorted(allowed)} → {len(events)} events", 'INFO')

        report_dates = []
        d = start_date
        while d <= end_date:
            report_dates.append(d)
            d += timedelta(days=1)

        records = attendance.calculate_attendance(events, emp_info, report_dates)
        config.log_activity(f"[{name}] {len(records)} attendance records calculated", 'INFO')

        title = profile.get('title') or 'Attendance Report'
        date_str   = (start_date.strftime('%d-%b-%Y') if start_date == end_date
                      else f"{start_date.strftime('%d-%b-%Y')}_to_{end_date.strftime('%d-%b-%Y')}")
        ts         = datetime.now().strftime('%H%M%S')
        safe_title = title.replace(' ', '_').replace('/', '-').replace(':', '')

        base_folder = profile.get('output_folder') or config.get_setting('output_folder', '.')
        out_folder  = str(Path(base_folder) / _safe_folder_name(profile.get('name', 'Report')))
        Path(out_folder).mkdir(parents=True, exist_ok=True)

        include_remarks = bool(profile.get('include_remarks', 1))

        attachments = []
        if profile.get('include_excel', 1):
            path = str(Path(out_folder) / f"{safe_title}_{date_str}_{ts}.xlsx")
            report_excel.generate_excel(records, title, start_date, end_date, path,
                                        raw_events=events, reader_map={},
                                        include_remarks=include_remarks)
            attachments.append(path)
            config.log_activity(f"[{name}] Excel: {path}", 'INFO')

        if profile.get('include_pdf', 1):
            path = str(Path(out_folder) / f"{safe_title}_{date_str}_{ts}.pdf")
            report_pdf.generate_pdf(records, title, start_date, end_date, path,
                                    include_remarks=include_remarks)
            attachments.append(path)
            config.log_activity(f"[{name}] PDF: {path}", 'INFO')

        recipients = json.loads(profile.get('recipients') or '[]')
        cc_list = json.loads(profile.get('cc') or '[]')

        if recipients:
            subject = (profile.get('email_subject') or title)
            subject = subject.replace('{date}', start_date.strftime('%d-%b-%Y'))
            subject = subject.replace('{title}', title)
            body = profile.get('email_body') or ''
            ok, msg = emailer.send_report_email(recipients, cc_list, subject, body, attachments)
            if ok:
                config.log_activity(f"[{name}] Email sent to {', '.join(recipients)}", 'INFO')
            else:
                config.log_activity(f"[{name}] Email failed: {msg}", 'ERROR')

        if profile.get('id') != '__auto_save__':
            config.update_profile_run_status(profile['id'], f'Success ({len(records)} records)')
        config.log_activity(f"[{name}] Completed successfully", 'INFO')
        _notify(f"Done: {name} ({len(records)} records)")
        return True, records

    except PermissionError as e:
        msg = f"Cannot save report file — close it in Excel and retry. ({e})"
        config.log_activity(f"[{name}] {msg}", 'ERROR')
        if profile.get('id') != '__auto_save__':
            config.update_profile_run_status(profile['id'], f'Error: {msg}')
        _notify(f"Error in {name}: {msg}")
        return False, msg
    except Exception as e:
        config.log_activity(f"[{name}] Error: {e}", 'ERROR')
        if profile.get('id') != '__auto_save__':
            config.update_profile_run_status(profile['id'], f'Error: {e}')
        _notify(f"Error in {name}: {e}")
        return False, str(e)


def get_report_dates(profile: dict, run_date: date) -> tuple:
    freq = profile.get('frequency', 'daily')
    if freq == 'daily':
        d = run_date - timedelta(days=1)
        return d, d
    elif freq == 'weekly':
        start = run_date - timedelta(days=run_date.weekday() + 7)
        return start, start + timedelta(days=6)
    elif freq == 'monthly':
        first = run_date.replace(day=1)
        last_end = first - timedelta(days=1)
        return last_end.replace(day=1), last_end
    return run_date, run_date


def _run_auto_save(today: date):
    yesterday = today - timedelta(days=1)
    folder = config.get_setting(
        'auto_save_folder',
        str(Path.home() / 'Documents' / 'LenelReports' / 'Automated Reports'))
    virtual = {
        'id':            '__auto_save__',
        'name':          'Auto-Save',
        'title':         'Daily Attendance Report',
        'output_folder': folder,
        'include_excel': 1,
        'include_pdf':   0,
        'recipients':    '[]',
        'cc':            '[]',
        'email_subject': '',
        'email_body':    '',
        'companies':     '[]',
        'enabled':       True,
        'frequency':     'daily',
    }
    generate_and_send(virtual, yesterday, yesterday)


def _loop():
    global _running
    last_minute = None
    while _running:
        now = datetime.now()
        cur_min = now.strftime('%H:%M')
        if cur_min != last_minute:
            last_minute = cur_min
            today = now.date()

            # User-configured profiles
            for profile in config.get_report_profiles():
                if not profile.get('enabled'):
                    continue
                if profile.get('run_time', '00:00') != cur_min:
                    continue
                freq = profile.get('frequency', 'daily')
                run = (freq == 'daily' or
                       (freq == 'weekly' and today.weekday() == profile.get('day_of_week', 0)) or
                       (freq == 'monthly' and today.day == profile.get('day_of_month', 1)))
                if run:
                    s, e = get_report_dates(profile, today)
                    threading.Thread(target=generate_and_send, args=(profile, s, e),
                                     daemon=True).start()

            # Built-in daily auto-save (runs regardless of profiles)
            if config.get_setting('auto_save_enabled', '1') == '1':
                if cur_min == config.get_setting('auto_save_time', '01:00'):
                    threading.Thread(target=_run_auto_save, args=(today,),
                                     daemon=True).start()

        time_module.sleep(15)


def start():
    global _thread, _running
    if _thread and _thread.is_alive():
        return
    _running = True
    _thread = threading.Thread(target=_loop, daemon=True, name='LenelScheduler')
    _thread.start()


def stop():
    global _running
    _running = False
