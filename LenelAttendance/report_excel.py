import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.styles.numbers import FORMAT_DATE_TIME3
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import List
from attendance import AttendanceRecord

# ── Colours ──────────────────────────────────────────────────────────────────
DARK_BLUE   = "1F3864"
YELLOW      = "FFD700"
LIGHT_RED   = "FFE0E0"
WHITE       = "FFFFFF"
LIGHT_GREY  = "F2F2F2"
MID_GREY    = "888888"
GREEN_HDR   = "375623"   # for Detailed Report header
ORANGE_HDR  = "7F3F00"   # for RAWDATA header

# ── Shared styles ─────────────────────────────────────────────────────────────
_thin   = Side(style='thin',   color='CCCCCC')
_medium = Side(style='medium', color='AAAAAA')
_BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)

def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _font(bold=False, color=WHITE, size=10, italic=False):
    return Font(name='Calibri', bold=bold, color=color, size=size, italic=italic)

_DATA_FONT   = _font(color="000000")
_TITLE_FONT  = Font(name='Calibri', bold=True, size=14, color=DARK_BLUE)
_FOOTER_FONT = Font(name='Calibri', size=8, italic=True, color=MID_GREY)

_CENTER = Alignment(horizontal='center', vertical='center')
_LEFT   = Alignment(horizontal='left',   vertical='center')
_WRAP   = Alignment(horizontal='left',   vertical='center', wrap_text=True)

# ── Excel time/date helpers ───────────────────────────────────────────────────
FMT_TIME    = 'h:mm'            # displayed as 8:30
FMT_HOURS   = '[h]:mm'          # >24h safe:  e.g. 9:45
FMT_DATE    = 'dd-mmm-yyyy'
FMT_DATETIME = 'dd-mmm-yyyy h:mm'


def _to_excel_time(t):
    """Convert a datetime or time object → Excel fraction (fraction of a day)."""
    if t is None:
        return None
    if isinstance(t, datetime):
        return time(t.hour, t.minute, t.second)
    return t


def _minutes_to_time(minutes: int):
    """Convert total minutes → a time object usable as Excel time fraction."""
    if minutes <= 0:
        return None
    h, m = divmod(minutes, 60)
    # Excel stores times as fractions of a day; openpyxl accepts time objects
    if h >= 24:
        # For >24h we return a plain float (days + fraction)
        return h / 24 + m / (24 * 60)
    return time(h, m, 0)


# ── Daily Summary sheet ───────────────────────────────────────────────────────
_DS_COLS = [
    ('Group Person ID', 13),
    ('Name',            24),
    ('Date',            13),
    ('First Punch In',  14),
    ('Last Punch Out',  14),
    ('Effective Hours', 15),
    ('Total Hours',     12),
    ('Company Name',    20),
    ('Remarks',         42),
]
_NCOLS    = len(_DS_COLS)           # 9
_LAST_COL = get_column_letter(_NCOLS)  # 'I'



def _write_daily_summary(wb, records: List[AttendanceRecord],
                          report_title: str, period_start: date, period_end: date,
                          include_remarks: bool = True):
    ws = wb.active
    ws.title = "Daily Summary"
    ws.sheet_view.showGridLines = False

    # Row 1 — Title
    ws.merge_cells(f'A1:{_LAST_COL}1')
    c = ws['A1']
    c.value     = report_title
    c.font      = _TITLE_FONT
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 32

    # Row 2 — Period
    ws.merge_cells(f'A2:{_LAST_COL}2')
    period_text = period_start.strftime('%d-%b-%Y')
    if period_end != period_start:
        period_text += f" to {period_end.strftime('%d-%b-%Y')}"
    c = ws['A2']
    c.value     = f"Period: {period_text}"
    c.font      = Font(name='Calibri', size=10, italic=True, color="555555")
    c.alignment = Alignment(horizontal='center')
    ws.row_dimensions[2].height = 18

    # Row 3 — Headers
    HR = 3
    HDR_FILL = _fill(DARK_BLUE)
    HDR_FONT = _font(bold=True)
    for col, (header, width) in enumerate(_DS_COLS, 1):
        c = ws.cell(row=HR, column=col, value=header)
        c.font      = HDR_FONT
        c.fill      = HDR_FILL
        c.alignment = _CENTER
        c.border    = _BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[HR].height = 24
    ws.freeze_panes = f'A{HR + 1}'

    REMARKS_COL = 9  # 1-based column index of 'Remarks' in Daily Summary (last column)

    # Sort by name, then date (client request)
    records = sorted(records, key=lambda r: (r.name or '', r.report_date or date.min))

    for i, rec in enumerate(records):
        row = HR + 1 + i

        first_in = _to_excel_time(rec.first_punch_in) if rec.first_punch_in else None
        last_out = _to_excel_time(rec.last_punch_out) if rec.last_punch_out else None
        eff_t    = _minutes_to_time(rec.effective_minutes)
        tot_t    = _minutes_to_time(rec.total_minutes)

        row_data = [
            rec.ssno,
            rec.name,
            rec.report_date,
            first_in,
            last_out,
            eff_t,
            tot_t,
            rec.company_name,
            rec.remarks_str if include_remarks else '',
        ]
        fmts = ['@', None, FMT_DATE, FMT_TIME, FMT_TIME, FMT_HOURS, FMT_HOURS,
                None, None]
        alignments = [_LEFT, _LEFT, _LEFT, _LEFT, _LEFT, _LEFT,
                      _LEFT, _LEFT, _WRAP]

        for col, (value, fmt, aln) in enumerate(zip(row_data, fmts, alignments), 1):
            c = ws.cell(row=row, column=col, value=value)
            c.font      = _DATA_FONT
            c.border    = _BORDER
            c.alignment = aln
            if fmt:
                c.number_format = fmt

        if include_remarks:
            if rec.has_out_2hr:
                ws.cell(row=row, column=REMARKS_COL).fill = _fill(YELLOW)
            elif rec.has_any_remark:
                ws.cell(row=row, column=REMARKS_COL).fill = _fill(LIGHT_RED)

        ws.row_dimensions[row].height = 18

    # Footer
    r = HR + len(records) + 2
    c = ws.cell(row=r, column=1)
    c.value = f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    c.font  = _FOOTER_FONT


# ── Detailed Report sheet ─────────────────────────────────────────────────────
def _write_detailed_report(wb, records: List[AttendanceRecord], raw_events: list,
                            reader_map: dict, include_remarks: bool = True):
    """
    raw_events: list of {emp_id, punch_time, reader_type, panelid, readerid}
    reader_map: {(panelid,readerid): readerdesc}
    """
    ws = wb.create_sheet("Detailed Report")
    ws.sheet_view.showGridLines = False

    # Build name/badge lookup from records
    emp_lookup = {rec.emp_id: rec for rec in records}

    # Group events by (emp_id, date)
    from collections import defaultdict
    emp_day = defaultdict(list)
    for ev in raw_events:
        emp_day[(ev['emp_id'], ev['punch_time'].date())].append(ev)

    DR_COLS = [
        ('Group Person ID', 13), ('Name', 22), ('Date', 13),
        ('Punch In Time', 14), ('In Reader', 26),
        ('Punch Out Time', 14), ('Out Reader', 26),
        ('Calculated Time', 15), ('Company Name', 20), ('Remarks', 28),
    ]
    HDR_FILL = _fill(GREEN_HDR)
    HDR_FONT = _font(bold=True, color=WHITE)

    for col, (header, width) in enumerate(DR_COLS, 1):
        c = ws.cell(row=1, column=col, value=header)
        c.font      = HDR_FONT
        c.fill      = HDR_FILL
        c.alignment = _CENTER
        c.border    = _BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = 'A2'

    REMARKS_COL_DR = 10  # 1-based column index of 'Remarks' in Detailed Report
    data_row = 2

    for (emp_id, day), evs in sorted(emp_day.items()):
        rec  = emp_lookup.get(emp_id)
        name = rec.name if rec else f'Employee {emp_id}'

        sorted_evs = sorted(evs, key=lambda e: e['punch_time'])
        # Pair entry→exit
        entries = [e for e in sorted_evs if e['reader_type'] == 'ENTRY']
        exits   = [e for e in sorted_evs if e['reader_type'] == 'EXIT']

        pairs = []
        used_exits = set()
        for en in entries:
            for i, ex in enumerate(exits):
                if i not in used_exits and ex['punch_time'] > en['punch_time']:
                    pairs.append((en, ex))
                    used_exits.add(i)
                    break
            else:
                pairs.append((en, None))

        # Unpaired exits
        for i, ex in enumerate(exits):
            if i not in used_exits:
                pairs.append((None, ex))

        pairs.sort(key=lambda p: (p[0]['punch_time'] if p[0] else p[1]['punch_time']))

        for en_ev, ex_ev in pairs:
            in_time   = _to_excel_time(en_ev['punch_time']) if en_ev else None
            out_time  = _to_excel_time(ex_ev['punch_time']) if ex_ev else None
            in_reader = (en_ev.get('reader_desc') or
                         reader_map.get((en_ev.get('panelid'), en_ev.get('readerid')), '')) if en_ev else ''
            out_reader = (ex_ev.get('reader_desc') or
                          reader_map.get((ex_ev.get('panelid'), ex_ev.get('readerid')), '')) if ex_ev else ''

            calc_time = None
            if in_time and out_time:
                en_dt = en_ev['punch_time']
                ex_dt = ex_ev['punch_time']
                mins  = int((ex_dt - en_dt).total_seconds() / 60)
                calc_time = _minutes_to_time(mins)

            remark = ''
            if include_remarks:
                if en_ev and not ex_ev:
                    remark = 'Missing Exit Punch'
                elif ex_ev and not en_ev:
                    remark = 'Missing Entry Punch'

            ssno_val = rec.ssno if rec else ''
            company  = rec.company_name if rec else ''
            row_vals = [ssno_val, name, day, in_time, in_reader,
                        out_time, out_reader, calc_time, company, remark]
            fmts     = ['@', None, FMT_DATE, FMT_TIME, None,
                        FMT_TIME, None, FMT_HOURS, None, None]

            for col, (val, fmt) in enumerate(zip(row_vals, fmts), 1):
                c = ws.cell(row=data_row, column=col, value=val)
                c.font      = _DATA_FONT
                c.border    = _BORDER
                c.alignment = _CENTER if col in (1, 3, 4, 6, 8) else _LEFT
                if fmt:
                    c.number_format = fmt
            if include_remarks and remark:
                ws.cell(row=data_row, column=REMARKS_COL_DR).fill = _fill(LIGHT_RED)
            ws.row_dimensions[data_row].height = 17
            data_row += 1


# ── RAWDATA sheet ─────────────────────────────────────────────────────────────
def _write_rawdata(wb, raw_events: list, records: List[AttendanceRecord],
                   reader_map: dict):
    ws   = wb.create_sheet("RAWDATA")
    ws.sheet_view.showGridLines = False

    emp_lookup = {rec.emp_id: rec for rec in records}

    cols = [
        ('Group Person ID', 13), ('Cardholder Name', 24), ('Badge Number', 13),
        ('Company Name', 20), ('In Date/Time', 18),
        ('In Reader', 28), ('Out Date/Time', 18),
        ('Out Reader', 28), ('Elapsed Time', 13),
    ]
    HDR_FILL = _fill(ORANGE_HDR)
    HDR_FONT = _font(bold=True, color=WHITE)

    for col, (header, width) in enumerate(cols, 1):
        c = ws.cell(row=1, column=col, value=header)
        c.font      = HDR_FONT
        c.fill      = HDR_FILL
        c.alignment = _CENTER
        c.border    = _BORDER
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = 'A2'

    from collections import defaultdict
    emp_day = defaultdict(list)
    for ev in raw_events:
        emp_day[(ev['emp_id'], ev['punch_time'].date())].append(ev)

    data_row = 2
    for (emp_id, day), evs in sorted(emp_day.items()):
        rec  = emp_lookup.get(emp_id)
        name = rec.name if rec else f'Employee {emp_id}'

        entries = sorted([e for e in evs if e['reader_type'] == 'ENTRY'],
                         key=lambda e: e['punch_time'])
        exits   = sorted([e for e in evs if e['reader_type'] == 'EXIT'],
                         key=lambda e: e['punch_time'])

        pairs     = []
        used_exits = set()
        for en in entries:
            for i, ex in enumerate(exits):
                if i not in used_exits and ex['punch_time'] > en['punch_time']:
                    pairs.append((en, ex))
                    used_exits.add(i)
                    break
            else:
                pairs.append((en, None))
        for i, ex in enumerate(exits):
            if i not in used_exits:
                pairs.append((None, ex))

        pairs.sort(key=lambda p: (p[0]['punch_time'] if p[0] else p[1]['punch_time']))

        for en_ev, ex_ev in pairs:
            in_dt    = en_ev['punch_time'] if en_ev else None
            out_dt   = ex_ev['punch_time'] if ex_ev else None
            in_rdr  = (en_ev.get('reader_desc') or
                       reader_map.get((en_ev.get('panelid'), en_ev.get('readerid')), '')) if en_ev else ''
            out_rdr = (ex_ev.get('reader_desc') or
                       reader_map.get((ex_ev.get('panelid'), ex_ev.get('readerid')), '')) if ex_ev else ''
            elapsed  = ''
            if in_dt and out_dt:
                mins = int((out_dt - in_dt).total_seconds() / 60)
                elapsed = f"{mins // 60}:{mins % 60:02d}"

            the_rec  = emp_lookup.get(emp_id)
            ssno_val = the_rec.ssno         if the_rec else ''
            company  = the_rec.company_name if the_rec else ''
            # Use per-swipe badge from the actual event (reflects badge changes within the period)
            ev_for_badge = en_ev if en_ev else ex_ev
            badge = (ev_for_badge.get('badge_no') or '') if ev_for_badge else (the_rec.badge_no if the_rec else '')
            row_vals = [ssno_val, name, badge, company, in_dt, in_rdr, out_dt, out_rdr, elapsed]
            fmts     = ['@', None, '@', None, FMT_DATETIME, None, FMT_DATETIME, None, None]
            for col, (val, fmt) in enumerate(zip(row_vals, fmts), 1):
                c = ws.cell(row=data_row, column=col, value=val)
                c.font      = _DATA_FONT
                c.border    = _BORDER
                c.alignment = _LEFT
                if fmt:
                    c.number_format = fmt
            ws.row_dimensions[data_row].height = 17
            data_row += 1


# ── Summary sheet (pivot: employees as rows, dates as columns) ────────────────
def _write_summary(wb, records: List[AttendanceRecord],
                   report_title: str, period_start: date, period_end: date):
    ws = wb.create_sheet("Summary")
    ws.sheet_view.showGridLines = False

    from collections import defaultdict

    # Collect unique employees (sorted by company then name)
    emp_info = {}
    for rec in records:
        key = rec.ssno or str(rec.emp_id)
        if key not in emp_info:
            emp_info[key] = {
                'ssno': key,
                'name': rec.name,
                'company': rec.company_name or '',
            }
    employees = sorted(emp_info.values(), key=lambda e: (e['company'], e['name']))

    # All dates in the requested range (show empty columns for dates with no data)
    all_dates = []
    d = period_start
    while d <= period_end:
        all_dates.append(d)
        d += timedelta(days=1)

    # Build pivot: (ssno, date) → effective_minutes
    pivot = defaultdict(int)
    for rec in records:
        key = rec.ssno or str(rec.emp_id)
        if rec.report_date:
            pivot[(key, rec.report_date)] += rec.effective_minutes

    # Layout: 3 fixed cols (Group Person ID, Name, Company) + one col per date
    N_FIXED = 3
    ncols = N_FIXED + len(all_dates)
    last_col_letter = get_column_letter(ncols)

    PURPLE_HDR = "2C3E7A"
    HDR_FILL = _fill(PURPLE_HDR)
    HDR_FONT = _font(bold=True)

    period_text = period_start.strftime('%d-%b-%Y')
    if period_end != period_start:
        period_text += f" to {period_end.strftime('%d-%b-%Y')}"

    # Row 1: Title
    ws.merge_cells(f'A1:{last_col_letter}1')
    c = ws['A1']
    c.value     = report_title
    c.font      = _TITLE_FONT
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 32

    # Row 2: Period
    ws.merge_cells(f'A2:{last_col_letter}2')
    c = ws['A2']
    c.value     = f"Period: {period_text}"
    c.font      = Font(name='Calibri', size=10, italic=True, color="555555")
    c.alignment = Alignment(horizontal='center')
    ws.row_dimensions[2].height = 18

    # Row 3: "EFFECTIVE HOURS (HH:MM)" section label over date columns only
    for col in range(1, N_FIXED + 1):
        ws.cell(row=3, column=col).fill   = HDR_FILL
        ws.cell(row=3, column=col).border = _BORDER
    if all_dates:
        ws.merge_cells(f'{get_column_letter(N_FIXED + 1)}3:{last_col_letter}3')
    c = ws.cell(row=3, column=N_FIXED + 1, value='EFFECTIVE HOURS (HH:MM)')
    c.font      = HDR_FONT
    c.fill      = HDR_FILL
    c.alignment = _CENTER
    c.border    = _BORDER
    ws.row_dimensions[3].height = 22

    # Row 4: fixed column headers + one date column per day
    HDR_ROW = 4
    fixed_headers = [('Group Person ID', 13), ('Name', 26), ('Company', 20)]
    for col_idx, (hdr, width) in enumerate(fixed_headers, 1):
        c = ws.cell(row=HDR_ROW, column=col_idx, value=hdr)
        c.font      = HDR_FONT
        c.fill      = HDR_FILL
        c.alignment = _CENTER
        c.border    = _BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    for i, d in enumerate(all_dates):
        col_idx = N_FIXED + 1 + i
        c = ws.cell(row=HDR_ROW, column=col_idx, value=d)
        c.font          = HDR_FONT
        c.fill          = HDR_FILL
        c.alignment     = _CENTER
        c.border        = _BORDER
        c.number_format = 'dd-mmm'
        ws.column_dimensions[get_column_letter(col_idx)].width = 9
    ws.row_dimensions[HDR_ROW].height = 24
    ws.freeze_panes = f'D{HDR_ROW + 1}'

    # Data rows: one row per employee
    for r_idx, emp in enumerate(employees):
        row  = HDR_ROW + 1 + r_idx
        fill = _fill(LIGHT_GREY) if r_idx % 2 == 0 else None

        for col_idx, val in enumerate([emp['ssno'], emp['name'], emp['company']], 1):
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font      = _DATA_FONT
            c.border    = _BORDER
            c.alignment = _LEFT
            if fill:
                c.fill = fill

        for i, d in enumerate(all_dates):
            col_idx = N_FIXED + 1 + i
            mins = pivot.get((emp['ssno'], d), 0)
            val  = _minutes_to_time(mins) if mins > 0 else None
            c = ws.cell(row=row, column=col_idx, value=val)
            c.font      = _DATA_FONT
            c.border    = _BORDER
            c.alignment = _CENTER
            if val is not None:
                c.number_format = FMT_HOURS
            if fill:
                c.fill = fill
        ws.row_dimensions[row].height = 17

    # Footer
    footer_row = HDR_ROW + len(employees) + 2
    c = ws.cell(row=footer_row, column=1)
    c.value = f"Generated: {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    c.font  = _FOOTER_FONT


# ── Public API ────────────────────────────────────────────────────────────────
def generate_excel(records: List[AttendanceRecord], report_title: str,
                   period_start: date, period_end: date, output_path: str,
                   raw_events: list = None, reader_map: dict = None,
                   include_remarks: bool = True) -> str:
    """
    Generate multi-sheet Excel report.
    include_remarks=False suppresses all punch remarks (for client-facing reports).
    """
    if not include_remarks:
        from copy import copy
        from dataclasses import replace as dc_replace
        clean = []
        for rec in records:
            r2 = AttendanceRecord(
                emp_id=rec.emp_id, name=rec.name, badge_no=rec.badge_no,
                ssno=rec.ssno, report_date=rec.report_date,
                first_punch_in=rec.first_punch_in, last_punch_out=rec.last_punch_out,
                effective_minutes=rec.effective_minutes, total_minutes=rec.total_minutes,
                group_person_id=rec.group_person_id, company_name=rec.company_name,
                remarks=[],
            )
            clean.append(r2)
        records = clean

    wb = openpyxl.Workbook()

    _write_daily_summary(wb, records, report_title, period_start, period_end,
                         include_remarks=include_remarks)
    _write_summary(wb, records, report_title, period_start, period_end)

    if raw_events is not None and reader_map is not None:
        _write_detailed_report(wb, records, raw_events, reader_map,
                               include_remarks=include_remarks)
        _write_rawdata(wb, raw_events, records, reader_map)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    return output_path
