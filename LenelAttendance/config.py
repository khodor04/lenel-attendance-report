import sqlite3
import os
import sys
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
import crypto

# Keys whose values are encrypted at rest with Windows DPAPI
_ENCRYPTED_KEYS = {'smtp_password', 'db_password'}

# When frozen by PyInstaller the db must live next to the .exe, not in the
# temp extraction folder that gets wiped on exit.
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

DB_PATH  = APP_DIR / "lenel_app.db"
LOGS_DIR = APP_DIR / "logs"

_log_lock = threading.Lock()


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS reader_mapping (
            panelid INTEGER,
            readerid INTEGER,
            readerdesc TEXT,
            reader_type TEXT DEFAULT 'IGNORE',
            PRIMARY KEY (panelid, readerid)
        );

        CREATE TABLE IF NOT EXISTS report_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            title TEXT,
            email_subject TEXT,
            output_folder TEXT,
            companies TEXT,
            recipients TEXT,
            cc TEXT,
            email_body TEXT,
            frequency TEXT DEFAULT 'daily',
            day_of_week INTEGER DEFAULT 0,
            day_of_month INTEGER DEFAULT 1,
            run_time TEXT DEFAULT '00:00',
            include_excel INTEGER DEFAULT 1,
            include_pdf INTEGER DEFAULT 1,
            include_remarks INTEGER DEFAULT 1,
            enabled INTEGER DEFAULT 1,
            last_run TEXT,
            last_status TEXT
        );

        -- activity_log removed: logs are now written to logs/YYYY-MM-DD.log text files
        """)

    # Migrate existing databases that predate include_remarks column
    try:
        with get_connection() as conn:
            conn.execute(
                "ALTER TABLE report_profiles ADD COLUMN include_remarks INTEGER DEFAULT 1"
            )
    except Exception:
        pass  # column already exists

    with get_connection() as conn:
        defaults = {
            'db_server': 'localhost',
            'db_name': 'AccessControl',
            'db_auth': 'windows',
            'db_user': '',
            'db_password': '',
            'archive_threshold_days': '30',  # fallback if View_ArchiveConfig-App not available
            'smtp_server': '',
            'smtp_port': '587',
            'smtp_use_tls': '1',
            'smtp_user': '',
            'smtp_password': '',
            'smtp_from': '',
            'output_folder': str(Path.home() / 'Documents' / 'LenelReports'),
            'udf_group_person_id': '',
            'company_name_source': 'division',
            'auto_save_enabled': '1',
            'auto_save_folder': str(Path.home() / 'Documents' / 'LenelReports' / 'Automated Reports'),
            'auto_save_time': '01:00',
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )


def get_setting(key, default=None):
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        value = row[0]
        if key in _ENCRYPTED_KEYS:
            value = crypto.decrypt(value)
        return value


def set_setting(key, value):
    raw = str(value) if value is not None else ''
    if key in _ENCRYPTED_KEYS:
        raw = crypto.encrypt(raw)
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, raw)
        )


def get_all_settings():
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    result = {}
    for key, value in rows:
        if key in _ENCRYPTED_KEYS:
            value = crypto.decrypt(value)
        result[key] = value
    return result


def get_reader_mapping():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT panelid, readerid, readerdesc, reader_type FROM reader_mapping ORDER BY panelid, readerid"
        ).fetchall()
        return [{'panelid': r[0], 'readerid': r[1], 'readerdesc': r[2], 'reader_type': r[3]} for r in rows]


def set_reader_type(panelid, readerid, reader_type):
    with get_connection() as conn:
        conn.execute(
            "UPDATE reader_mapping SET reader_type = ? WHERE panelid = ? AND readerid = ?",
            (reader_type, panelid, readerid)
        )


def sync_readers(readers):
    with get_connection() as conn:
        for r in readers:
            conn.execute(
                "INSERT OR IGNORE INTO reader_mapping (panelid, readerid, readerdesc, reader_type) VALUES (?, ?, ?, 'IGNORE')",
                (r['panelid'], r['readerid'], r['readerdesc'])
            )
            conn.execute(
                "UPDATE reader_mapping SET readerdesc = ? WHERE panelid = ? AND readerid = ?",
                (r['readerdesc'], r['panelid'], r['readerid'])
            )


def get_report_profiles():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM report_profiles ORDER BY name").fetchall()
        if not rows:
            return []
        cols = [d[1] for d in conn.execute("PRAGMA table_info(report_profiles)").fetchall()]
        return [dict(zip(cols, r)) for r in rows]


def get_report_profile(profile_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM report_profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            return None
        cols = [d[1] for d in conn.execute("PRAGMA table_info(report_profiles)").fetchall()]
        return dict(zip(cols, row))


def save_report_profile(profile):
    with get_connection() as conn:
        if profile.get('id'):
            conn.execute("""
                UPDATE report_profiles SET
                    name=?, title=?, email_subject=?, output_folder=?,
                    companies=?, recipients=?, cc=?, email_body=?,
                    frequency=?, day_of_week=?, day_of_month=?,
                    run_time=?, include_excel=?, include_pdf=?, include_remarks=?, enabled=?
                WHERE id=?
            """, (
                profile['name'], profile.get('title', ''), profile.get('email_subject', ''),
                profile.get('output_folder', ''),
                json.dumps(profile.get('companies', [])),
                json.dumps(profile.get('recipients', [])),
                json.dumps(profile.get('cc', [])),
                profile.get('email_body', ''),
                profile.get('frequency', 'daily'), profile.get('day_of_week', 0),
                profile.get('day_of_month', 1), profile.get('run_time', '00:00'),
                1 if profile.get('include_excel', True) else 0,
                1 if profile.get('include_pdf', True) else 0,
                1 if profile.get('include_remarks', True) else 0,
                1 if profile.get('enabled', True) else 0,
                profile['id']
            ))
        else:
            conn.execute("""
                INSERT INTO report_profiles
                    (name, title, email_subject, output_folder, companies, recipients, cc,
                     email_body, frequency, day_of_week, day_of_month, run_time,
                     include_excel, include_pdf, include_remarks, enabled)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                profile['name'], profile.get('title', ''), profile.get('email_subject', ''),
                profile.get('output_folder', ''),
                json.dumps(profile.get('companies', [])),
                json.dumps(profile.get('recipients', [])),
                json.dumps(profile.get('cc', [])),
                profile.get('email_body', ''),
                profile.get('frequency', 'daily'), profile.get('day_of_week', 0),
                profile.get('day_of_month', 1), profile.get('run_time', '00:00'),
                1 if profile.get('include_excel', True) else 0,
                1 if profile.get('include_pdf', True) else 0,
                1 if profile.get('include_remarks', True) else 0,
                1 if profile.get('enabled', True) else 0,
            ))


def delete_report_profile(profile_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM report_profiles WHERE id = ?", (profile_id,))


def update_profile_run_status(profile_id, status, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE report_profiles SET last_run=?, last_status=? WHERE id=?",
            (timestamp, status, profile_id)
        )


def log_activity(message, level='INFO'):
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    line = f"{datetime.now().isoformat()}|{level}|{message}\n"
    with _log_lock:
        with open(log_file, 'a', encoding='utf-8') as fh:
            fh.write(line)


def get_activity_logs(limit=500):
    if not LOGS_DIR.exists():
        return []
    logs = []
    for lf in sorted(LOGS_DIR.glob('*.log'), reverse=True):
        try:
            lines = lf.read_text(encoding='utf-8').splitlines()
            for line in reversed(lines):
                parts = line.split('|', 2)
                if len(parts) == 3:
                    logs.append({'timestamp': parts[0], 'level': parts[1], 'message': parts[2]})
                    if len(logs) >= limit:
                        return logs
        except Exception:
            pass
    return logs


def clear_old_logs(days=60):
    if not LOGS_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=days)
    for lf in LOGS_DIR.glob('*.log'):
        try:
            file_date = datetime.strptime(lf.stem, '%Y-%m-%d')
            if file_date < cutoff:
                lf.unlink()
        except Exception:
            pass
