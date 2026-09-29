from datetime import date, datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List
from collections import defaultdict
import re


def _clean_name(name: str) -> str:
    """Remove trailing repeated word sequences, e.g. 'Ethel Jane Aviles Ethel Jane' → 'Ethel Jane Aviles'."""
    if not name:
        return name
    words = name.split()
    n = len(words)
    for suffix_len in range(1, n // 2 + 1):
        if words[:suffix_len] == words[n - suffix_len:]:
            return ' '.join(words[:n - suffix_len])
    return name


def _clean_ssno(ssno: str) -> str:
    """Strip non-numeric suffix, e.g. '1070445-MET' → '1070445'."""
    if not ssno:
        return ssno
    m = re.match(r'^([^-]+)-[A-Za-z]', ssno.strip())
    return m.group(1).strip() if m else ssno.strip()


@dataclass
class AttendanceRecord:
    emp_id: int
    name: str = ''
    badge_no: str = ''
    ssno: str = ''
    report_date: Optional[date] = None
    first_punch_in: Optional[datetime] = None
    last_punch_out: Optional[datetime] = None
    effective_minutes: int = 0
    total_minutes: int = 0
    remarks: List[str] = field(default_factory=list)
    group_person_id: str = ''
    company_name: str = ''

    @property
    def effective_hours_str(self):
        if self.effective_minutes == 0 and not self.first_punch_in:
            return ''
        h, m = divmod(self.effective_minutes, 60)
        return f"{h:02d}:{m:02d}"

    @property
    def total_hours_str(self):
        if self.total_minutes == 0 and not self.first_punch_in:
            return ''
        h, m = divmod(self.total_minutes, 60)
        return f"{h:02d}:{m:02d}"

    @property
    def first_punch_str(self):
        return self.first_punch_in.strftime('%H:%M') if self.first_punch_in else ''

    @property
    def last_punch_str(self):
        return self.last_punch_out.strftime('%H:%M') if self.last_punch_out else ''

    @property
    def remarks_str(self):
        return '; '.join(self.remarks)

    @property
    def has_out_2hr(self):
        return any('Out of office >2h' in r for r in self.remarks)

    @property
    def has_any_remark(self):
        return bool(self.remarks)


def calculate_attendance(events: list, emp_info: dict, report_dates: list) -> list:
    report_date_set = set(report_dates)

    emp_day_events = defaultdict(list)
    for ev in events:
        local_date = ev['punch_time'].date()
        if local_date in report_date_set:
            emp_day_events[(ev['emp_id'], local_date)].append(ev)

    records = []
    for (emp_id, day) in emp_day_events:
        info = emp_info.get(emp_id, {})
        evs = sorted(emp_day_events[(emp_id, day)], key=lambda e: e['punch_time'])

        record = AttendanceRecord(
            emp_id=emp_id,
            name=_clean_name(info.get('name', f'Employee {emp_id}')),
            badge_no=info.get('badge_no', ''),
            ssno=_clean_ssno(info.get('ssno', '')),
            report_date=day,
            group_person_id=_clean_ssno(info.get('group_person_id', '')),
            company_name=info.get('company_name', ''),
        )
        _process_day_punches(record, evs)
        records.append(record)

    records.sort(key=lambda r: (
        r.report_date or date.min,
        r.first_punch_in.replace(second=0, microsecond=0) if r.first_punch_in else datetime.min,
        r.ssno or str(r.emp_id),
    ))
    return records


def _process_day_punches(record: AttendanceRecord, events: list):
    entry_times = sorted([e['punch_time'] for e in events if e['reader_type'] == 'ENTRY'])
    exit_times = sorted([e['punch_time'] for e in events if e['reader_type'] == 'EXIT'])

    if not entry_times and not exit_times:
        return

    if entry_times:
        record.first_punch_in = entry_times[0]
    if exit_times:
        record.last_punch_out = exit_times[-1]

    if not entry_times:
        record.remarks.append("Missing Entry Punch")
    if not exit_times:
        record.remarks.append("Missing Exit Punch")

    # Pair entry→exit chronologically
    all_punches = sorted(
        [{'time': t, 'type': 'ENTRY'} for t in entry_times] +
        [{'time': t, 'type': 'EXIT'} for t in exit_times],
        key=lambda p: p['time']
    )

    paired_intervals = []
    pending_entry = None
    unpaired_entries = 0
    unpaired_exits = 0

    for punch in all_punches:
        if punch['type'] == 'ENTRY':
            if pending_entry is None:
                pending_entry = punch['time']
            else:
                unpaired_entries += 1
                pending_entry = punch['time']
        else:
            if pending_entry is not None:
                paired_intervals.append((pending_entry, punch['time']))
                pending_entry = None
            else:
                unpaired_exits += 1

    if pending_entry is not None:
        unpaired_entries += 1

    if unpaired_entries > 0:
        record.remarks.append(f"Unpaired Entry Punch(es): {unpaired_entries}")
    if unpaired_exits > 0:
        record.remarks.append(f"Unpaired Exit Punch(es): {unpaired_exits}")

    record.effective_minutes = sum(
        int((ex - en).total_seconds() / 60) for en, ex in paired_intervals
    )

    if record.first_punch_in and record.last_punch_out:
        record.total_minutes = int(
            (record.last_punch_out - record.first_punch_in).total_seconds() / 60
        )

    if record.effective_minutes < 480 and record.effective_minutes > 0:
        record.remarks.append("Less than 8 effective hours")

    _check_out_of_office(record, paired_intervals)


def _check_out_of_office(record: AttendanceRecord, intervals: list):
    if len(intervals) < 2:
        return
    for i in range(len(intervals) - 1):
        _, exit_time = intervals[i]
        next_entry, _ = intervals[i + 1]
        gap_minutes = int((next_entry - exit_time).total_seconds() / 60)
        if gap_minutes > 120:
            h, m = divmod(gap_minutes, 60)
            out_str  = exit_time.strftime('%H:%M')
            back_str = next_entry.strftime('%H:%M')
            record.remarks.append(
                f"Out of office >2h ({h}h {m:02d}m): {out_str} – {back_str}"
            )
