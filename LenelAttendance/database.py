import pyodbc
from datetime import datetime, date, timedelta
from config import get_setting, log_activity

_LIVE_VIEW    = 'dbo.[View_EventsTA-App]'
_ARCHIVE_VIEW = 'dbo.[View_EventsTA_Arc-App]'


def _find_driver():
    drivers = pyodbc.drivers()
    for preferred in ['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server',
                      'ODBC Driver 13 for SQL Server', 'SQL Server']:
        if preferred in drivers:
            return preferred
    return drivers[0] if drivers else 'SQL Server'


def get_connection_string():
    server = get_setting('db_server', 'localhost')
    db     = get_setting('db_name', 'AccessControl')
    auth   = get_setting('db_auth', 'windows')
    driver = _find_driver()
    if auth == 'windows':
        return (f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};"
                f"Trusted_Connection=yes;TrustServerCertificate=yes;")
    else:
        user = get_setting('db_user', '')
        pwd  = get_setting('db_password', '')
        return (f"DRIVER={{{driver}}};SERVER={server};DATABASE={db};"
                f"UID={user};PWD={pwd};TrustServerCertificate=yes;")


def test_connection():
    try:
        with pyodbc.connect(get_connection_string(), timeout=5) as conn:
            conn.execute(f"SELECT TOP 1 1 FROM {_LIVE_VIEW}")
        return True, "Connection successful"
    except Exception as e:
        return False, str(e)


_VIEW_COLS = (
    "Segment_DateTime, [Emp ID], [First Name], [Last Name],"
    " [Reader Desc], [Punch Type], Division, [Badge Number]"
)


def _query_ta_view(view_name: str, local_start: datetime, local_end: datetime):
    """
    Query a T&A view by local date range using Segment_DateTime (already local time in view).
    Returns (events_list, emp_info_dict).
    """
    try:
        with pyodbc.connect(get_connection_string()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {_VIEW_COLS} FROM {view_name}"
                f" WHERE Segment_DateTime >= ? AND Segment_DateTime < ?"
                f" ORDER BY Segment_DateTime",
                (local_start, local_end),
            )
            cols   = [d[0] for d in cursor.description]
            events   = []
            emp_info = {}

            for raw in cursor.fetchall():
                row = dict(zip(cols, raw))

                punch_time = row.get('Segment_DateTime')
                if punch_time is None:
                    continue

                ssno = (row.get('Emp ID') or '').strip()
                if not ssno:
                    continue

                punch_type = (row.get('Punch Type') or '').strip()
                if punch_type == 'Entered':
                    reader_type = 'ENTRY'
                elif punch_type == 'Exited':
                    reader_type = 'EXIT'
                else:
                    continue  # skip Unknown / unexpected values

                first = (row.get('First Name') or '').strip()
                last  = (row.get('Last Name')  or '').strip()
                name  = f"{first} {last}".strip() if first else last or ssno
                badge_no = (row.get('Badge Number') or '').strip()

                events.append({
                    'emp_id':      ssno,
                    'punch_time':  punch_time,
                    'reader_type': reader_type,
                    'panelid':     None,
                    'readerid':    None,
                    'reader_desc': (row.get('Reader Desc') or '').strip(),
                    'badge_no':    badge_no,
                })

                if ssno not in emp_info:
                    emp_info[ssno] = {
                        'name':            name,
                        'badge_no':        badge_no,
                        'company_name':    (row.get('Division') or '').strip(),
                        'ssno':            ssno,
                        'group_person_id': '',
                    }
                elif badge_no:
                    # Always update to the most recent badge number (ORDER BY ensures chronological order)
                    emp_info[ssno]['badge_no'] = badge_no

            log_activity(f"{view_name}: {len(events)} events fetched", 'INFO')
            return events, emp_info

    except Exception as e:
        log_activity(f"Error querying {view_name}: {e}", 'ERROR')
        raise


def _local_date_range(start_date: date, end_date: date):
    """Local midnight of start_date to local midnight after end_date."""
    local_start = datetime.combine(start_date, datetime.min.time())
    local_end   = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    return local_start, local_end


def get_events_from_view(start_date: date, end_date: date):
    """Live events from View_EventsTA for the given local date range."""
    local_start, local_end = _local_date_range(start_date, end_date)
    return _query_ta_view(_LIVE_VIEW, local_start, local_end)


def get_events_from_archive_view(start_date: date, end_date: date):
    """Archived events from View_EventsTA_Arc for the given local date range.

    If the archive view references a cross-database table (e.g. AccessControl_Archival.dbo.EVENTS_RESTORED)
    and ReportUser lacks cross-database access, SQL Server raises a permission error even though
    ReportUser has SELECT on the view itself. In that case we log a warning and return empty results
    so the report continues with live data only — no crash, no data loss for recent records.
    """
    local_start, local_end = _local_date_range(start_date, end_date)
    try:
        return _query_ta_view(_ARCHIVE_VIEW, local_start, local_end)
    except Exception as e:
        err = str(e).lower()
        if 'permission' in err or 'select permission' in err or 'does not have permission' in err:
            log_activity(
                f"Archive view permission denied — report will use live data only. "
                f"To fix this, run in SQL Server: "
                f"ALTER DATABASE AccessControl SET DB_CHAINING ON; "
                f"ALTER DATABASE AccessControl_Archival SET DB_CHAINING ON; "
                f"(Original error: {e})",
                'WARNING'
            )
            return [], {}
        raise


def get_archive_threshold_days() -> int:
    """Read archive threshold from View_ArchiveConfig-App. Falls back to config setting."""
    try:
        with pyodbc.connect(get_connection_string(), timeout=5) as conn:
            row = conn.execute(
                "SELECT ArchiveAfterDays FROM [dbo].[View_ArchiveConfig-App]"
            ).fetchone()
            if row and row[0] is not None:
                return int(row[0])
    except Exception:
        pass
    try:
        return int(get_setting('archive_threshold_days', '30') or 30)
    except (TypeError, ValueError):
        return 30


def get_divisions():
    """
    Distinct company/division names from the live view only.
    Used by the profile editor company filter — called on demand, not at startup.
    """
    try:
        with pyodbc.connect(get_connection_string()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT ISNULL(Division, '') AS Division"
                f" FROM {_LIVE_VIEW}"
                f" WHERE Division IS NOT NULL AND RTRIM(Division) != ''"
                f" ORDER BY Division"
            )
            return [{'id': r[0], 'name': r[0]} for r in cursor.fetchall()]
    except Exception as e:
        log_activity(f"Error fetching divisions: {e}", 'ERROR')
        return []


def get_readers_from_view():
    """
    Distinct reader descriptions and punch types from the live view only.
    Used by the Reader List tab — informational only.
    """
    try:
        with pyodbc.connect(get_connection_string()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT [Reader Desc], [Punch Type]"
                f" FROM {_LIVE_VIEW}"
                f" WHERE [Reader Desc] IS NOT NULL AND RTRIM([Reader Desc]) != ''"
                f" ORDER BY [Reader Desc], [Punch Type]"
            )
            return [{'readerdesc': r[0], 'punch_type': r[1]} for r in cursor.fetchall()]
    except Exception as e:
        log_activity(f"Error fetching readers from view: {e}", 'ERROR')
        return []
