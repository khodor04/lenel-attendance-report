# SQL Reference — Lenel Attendance App

All SQL queries used by the application against the Lenel `AccessControl` database.
Kept here so queries are never lost across refactors or DB migrations.

---

## ReportUser — Setup & Permissions

Run all of this as `sa` or a sysadmin login on the SQL Server instance.

### 1. Create the login (SQL authentication)

```sql
USE master;
GO
CREATE LOGIN ReportUser
    WITH PASSWORD    = 'YourStrongPassword!',
         DEFAULT_DATABASE = AccessControl,
         CHECK_EXPIRATION = OFF,
         CHECK_POLICY     = OFF;
GO
```

### 2. Create the database user and link it to the login

```sql
USE AccessControl;
GO
CREATE USER ReportUser FOR LOGIN ReportUser;
GO
```

### 3. Grant SELECT on the two app views (only permissions needed)

```sql
USE AccessControl;
GO
GRANT SELECT ON dbo.View_EventsTA     TO ReportUser;
GRANT SELECT ON dbo.View_EventsTA_Arc TO ReportUser;
GO
```

> **That's all.** ReportUser needs no table access, no schema permissions, no roles beyond `public`.

---

### Troubleshooting — Login fails with "Cannot open database"

This means the server-level login and the database-level user exist but their SIDs don't match (orphaned user — common when the login was recreated).

**Diagnose:**
```sql
USE AccessControl;
GO
SELECT dp.name,
       CASE WHEN dp.sid = sp.sid THEN 'Linked OK' ELSE 'ORPHAN' END AS status
FROM sys.database_principals dp
LEFT JOIN sys.server_principals sp ON sp.name = dp.name
WHERE dp.name = 'ReportUser';
```

**Fix:**
```sql
USE AccessControl;
GO
ALTER USER ReportUser WITH LOGIN = ReportUser;
GO
GRANT CONNECT TO ReportUser;
GO
```

---

### App connection string (SQL auth)

In Settings → Database:
- Authentication: `sql`
- SQL Username: `ReportUser`
- SQL Password: *(the password set above)*
- SQL Server: `localhost` (or `hostname\SQLEXPRESS`)
- Database Name: `AccessControl`

---

## View Naming Convention

When deploying to a new client site, create the two views using **exactly these names**.
The app has these names hardcoded — changing them requires a code change.

| View | Name | Source Table |
|------|------|--------------|
| Live events | `dbo.View_EventsTA` | `dbo.EVENTS` |
| Archive events | `dbo.View_EventsTA_Arc` | `dbo.EVENTS_ARCHIVED` |

Pattern: `View_Events` + `TA` (Time & Attendance) + `_Arc` suffix for archive.
If the client DB uses a different schema than `dbo`, both the view creation script and the app config must be updated together.

---

## View Column Safety Rules

The app reads both views using `SELECT *` and accesses columns **by name**.
This means you can safely add new columns to the views at any time — the app will pick them up automatically.

**DO NOT rename or delete these columns — the app will break:**

| Column | Used For |
|--------|----------|
| `Segment_DateTime` | Punch local time (attendance calculation) |
| `EVENT_TIME_UTC` | Date-range filtering (WHERE clause) |
| `Emp ID` | Employee identifier (SSNO) |
| `Last Name` | Employee display name |
| `Punch Type` | Determines Entry vs Exit (`'Entered'` / `'Exited'`) |
| `Reader Desc` | Reader name shown in Detailed Report |

**Safe to add at any time (app picks up automatically with no code change):**

| Column | Notes |
|--------|-------|
| `First Name` | Already in both views; currently NULL in this system |
| `Division` | Company name shown in report |
| `Segment` | Office/location label |
| `Group Person ID` | Add the UDF column here when the client configures it |
| Any other column | Ignored by app unless explicitly mapped |

---

## Live View (v2 — current)

**View name:** `dbo.View_EventsTA`
**Replaces:** Direct query against `dbo.EVENTS` (used in v1)

```sql
SELECT
    CASE
        WHEN SEGMENT.SEGMENTID IN (0, 1, 5) THEN CONVERT(datetime, DATEADD(MINUTE, 240, EVENTS.EVENT_TIME_UTC))
        WHEN SEGMENT.SEGMENTID IN (2, 4)    THEN CONVERT(datetime, DATEADD(MINUTE, 180, EVENTS.EVENT_TIME_UTC))
        WHEN SEGMENT.SEGMENTID IN (3, 6)    THEN CONVERT(datetime, DATEADD(MINUTE, 120, EVENTS.EVENT_TIME_UTC))
        ELSE                                     CONVERT(datetime, DATEADD(MINUTE, 240, EVENTS.EVENT_TIME_UTC))
    END                        AS Segment_DateTime,
    EVENTS.EVENT_TIME_UTC,
    EMP.SSNO                   AS [Emp ID],
    EMP.FIRSTNAME              AS [First Name],
    EMP.LASTNAME               AS [Last Name],
    READER.READERDESC          AS [Reader Desc],
    EVENT.EVDESCR              AS [Event Type],
    CASE
        WHEN READER.TIMEATT = 1 THEN 'Entered'
        WHEN READER.TIMEATT = 2 THEN 'Exited'
        ELSE 'Unknown'
    END                        AS [Punch Type],
    ACCESSPANE.NAME            AS [Panel Name],
    dbo.DIVISION.NAME          AS Division,
    dbo.SEGMENT.NAME           AS Segment
FROM dbo.EVENTS AS EVENTS
INNER JOIN      dbo.EVENT      AS EVENT      ON EVENTS.EVENTTYPE = EVENT.EVTYPEID AND EVENTS.EVENTID = EVENT.EVID
LEFT OUTER JOIN dbo.READER     AS READER     ON EVENTS.MACHINE = READER.PANELID AND EVENTS.DEVID = READER.READERID
LEFT OUTER JOIN dbo.EMP        AS EMP        ON EVENTS.EMPID = EMP.ID
INNER JOIN      dbo.ACCESSPANE AS ACCESSPANE ON EVENTS.MACHINE = ACCESSPANE.PANELID
INNER JOIN      dbo.UDFEMP                   ON EMP.ID = dbo.UDFEMP.ID
LEFT OUTER JOIN dbo.SEGMENT    AS SEGMENT    ON EMP.SEGMENTID = dbo.SEGMENT.SEGMENTID
LEFT OUTER JOIN dbo.DIVISION                 ON dbo.UDFEMP.DIVISION = dbo.DIVISION.ID
WHERE (EVENTS.EVENTTYPE = 0)
  AND (READER.TIMEATT IS NOT NULL)
  AND (READER.TIMEATT > 0)
```

**App query against this view:**
```sql
SELECT * FROM dbo.<ViewName>
WHERE EVENT_TIME_UTC >= ?    -- UTC start (local midnight - max offset)
  AND EVENT_TIME_UTC <  ?    -- UTC end   (local midnight+1 - min offset)
```

---

## Archive View (v2 — current)

**View name:** `dbo.View_EventsTA_Arc`
**Replaces:** Direct query against `dbo.EVENTS_ARCHIVED` (used in v1)

```sql
SELECT
    CASE
        WHEN PANELTZ = 3            THEN CONVERT(datetime, DATEADD(MINUTE, 240, EVENTS_ARCHIVED.EVENT_TIME_UTC))
        WHEN PANELTZ = 47           THEN CONVERT(datetime, DATEADD(MINUTE, 180, EVENTS_ARCHIVED.EVENT_TIME_UTC))
        WHEN PANELTZ = 81 OR
             PANELTZ = 23           THEN CONVERT(datetime, DATEADD(MINUTE, 120, EVENTS_ARCHIVED.EVENT_TIME_UTC))
        ELSE                             CONVERT(datetime, DATEADD(MINUTE, 240, EVENTS_ARCHIVED.EVENT_TIME_UTC))
    END                        AS Segment_DateTime,
    EVENTS_ARCHIVED.EVENT_TIME_UTC,
    EMP.SSNO                   AS [Emp ID],
    EMP.FIRSTNAME              AS [First Name],
    EMP.LASTNAME               AS [Last Name],
    READER.READERDESC          AS [Reader Desc],
    EVENT.EVDESCR              AS [Event Type],
    CASE
        WHEN READER.TIMEATT = 1 THEN 'Entered'
        WHEN READER.TIMEATT = 2 THEN 'Exited'
        ELSE 'Unknown'
    END                        AS [Punch Type],
    ACCESSPANE.NAME            AS [Panel Name],
    dbo.DIVISION.NAME          AS Division,
    dbo.SEGMENT.NAME           AS Segment
FROM dbo.EVENTS_ARCHIVED AS EVENTS_ARCHIVED
INNER JOIN      dbo.EVENT      AS EVENT      ON EVENTS_ARCHIVED.EVENTTYPE = EVENT.EVTYPEID AND EVENTS_ARCHIVED.EVENTID = EVENT.EVID
LEFT OUTER JOIN dbo.READER     AS READER     ON EVENTS_ARCHIVED.MACHINE = READER.PANELID AND EVENTS_ARCHIVED.DEVID = READER.READERID
LEFT OUTER JOIN dbo.EMP        AS EMP        ON EVENTS_ARCHIVED.EMPID = EMP.ID
INNER JOIN      dbo.ACCESSPANE AS ACCESSPANE ON EVENTS_ARCHIVED.MACHINE = ACCESSPANE.PANELID
INNER JOIN      dbo.UDFEMP                   ON EMP.ID = dbo.UDFEMP.ID
LEFT OUTER JOIN dbo.SEGMENT    AS SEGMENT    ON EMP.SEGMENTID = dbo.SEGMENT.SEGMENTID
LEFT OUTER JOIN dbo.DIVISION                 ON dbo.UDFEMP.DIVISION = dbo.DIVISION.ID
WHERE (EVENTS_ARCHIVED.EVENTTYPE = 0)
  AND (READER.TIMEATT IS NOT NULL)
  AND (READER.TIMEATT > 0)
```

**App query against this view:**
```sql
SELECT * FROM dbo.<ArchiveViewName>
WHERE EVENT_TIME_UTC >= ?    -- UTC start with buffer
  AND EVENT_TIME_UTC <  ?    -- UTC end   with buffer
```

---

## Legacy Queries (v1 — kept for reference)

These queries were used before the view-based refactor. Do not delete them —
useful if views are unavailable or need to be recreated from scratch.

---

### v1 — Live Events

**Function:** `database.get_events_for_period()`
**Table:** `dbo.EVENTS`

```sql
SELECT
    E.EMPID,
    E.EVENT_TIME_UTC,
    E.MACHINE  AS PanelID,
    E.DEVID    AS ReaderID
FROM dbo.EVENTS E
WHERE E.EVENTTYPE = 0
  AND E.EVENT_TIME_UTC >= ?
  AND E.EVENT_TIME_UTC <  ?
ORDER BY E.EMPID, E.EVENT_TIME_UTC
```

**Notes:**
- T&A filtering applied in Python by cross-referencing reader mapping in `lenel_app.db`.
- Timezone conversion done in Python using `EMP.SEGMENTID` offset map.
- `MACHINE` = `READER.PANELID`, `DEVID` = `READER.READERID`.

---

### v1 — Archive Events

**Function:** `database.get_events_from_archive()`
**Table:** `dbo.EVENTS_ARCHIVED`

```sql
SELECT
    EA.EVENT_TIME_UTC,
    ISNULL(AP.PANELTZ, 3)                        AS PANELTZ,
    ISNULL(RTRIM(E.SSNO), '')                    AS SSNO,
    ISNULL(RTRIM(E.LASTNAME), '')                AS LastName,
    ISNULL(CAST(EA.CARDNUM AS NVARCHAR(50)), '') AS Badge,
    ISNULL(R.READERDESC, '')                     AS ReaderDesc,
    R.TIMEATT,
    ISNULL(D.NAME, '')                           AS Division
FROM dbo.EVENTS_ARCHIVED AS EA
LEFT JOIN dbo.READER     AS R  ON EA.MACHINE = R.PANELID AND EA.DEVID = R.READERID
LEFT JOIN dbo.EMP        AS E  ON EA.EMPID = E.ID
LEFT JOIN dbo.ACCESSPANE AS AP ON EA.MACHINE = AP.PANELID
LEFT JOIN dbo.UDFEMP     AS U  ON E.ID = U.ID
LEFT JOIN dbo.DIVISION   AS D  ON U.DIVISION = D.ID
WHERE EA.EVENTTYPE = 0
  AND R.TIMEATT IS NOT NULL
  AND R.TIMEATT > 0
  AND EA.EVENT_TIME_UTC >= ?
  AND EA.EVENT_TIME_UTC <  ?
ORDER BY E.SSNO, EA.EVENT_TIME_UTC
```

**Notes:**
- UTC range uses ±4h buffer to cover all timezone offsets.
- `PANELTZ` → UTC offset mapping hardcoded in Python: `{3: 240, 47: 180, 81: 120, 23: 120}`.

---

### v1 — Employee Info

**Function:** `database.get_employee_info()`
**Tables:** `dbo.EMP`, `dbo.BADGE`, `dbo.UDFEMP`, `dbo.DIVISION`

```sql
SELECT
    E.ID AS EmpID,
    ISNULL(
        RTRIM(ISNULL(E.FIRSTNAME,'')) + ' ' + RTRIM(ISNULL(E.LASTNAME,'')),
        ISNULL(RTRIM(E.FIRSTNAME), ISNULL(RTRIM(E.LASTNAME), ''))
    ) AS Name,
    COALESCE(
        NULLIF(CAST(B.EMBOSSED AS NVARCHAR(50)), '0'),
        CAST(B.ID AS NVARCHAR(50)),
        ''
    ) AS BadgeNo,
    ISNULL(D.NAME, '')                               AS CompanyName,
    ISNULL(CAST(U.[<udf_field>] AS NVARCHAR(50)), '') AS GroupPersonID,
    ISNULL(CAST(E.SSNO AS NVARCHAR(50)), '')         AS SSNO
FROM dbo.EMP E
LEFT JOIN (
    SELECT EMPID, EMBOSSED, ID,
           ROW_NUMBER() OVER (PARTITION BY EMPID ORDER BY STATUS DESC, ID) AS rn
    FROM dbo.BADGE
) B ON B.EMPID = E.ID AND B.rn = 1
LEFT JOIN dbo.UDFEMP   U ON U.ID = E.ID
LEFT JOIN dbo.DIVISION D ON D.ID = U.DIVISION
WHERE E.VISITOR = 0
  AND E.ID IN (?, ?, ...)
```

---

### v1 — Reader List

**Function:** `database.get_all_readers(ta_only=True)`
**Table:** `dbo.READER`

```sql
SELECT PANELID, READERID, ISNULL(READERDESC, '') AS READERDESC, ISNULL(TIMEATT, 0) AS TIMEATT
FROM dbo.READER
WHERE TIMEATT IS NOT NULL AND TIMEATT > 0
ORDER BY PANELID, READERID
```

---

### v1 — Company / Division List

**Function:** `database.get_divisions()`
**Table:** `dbo.DIVISION`

```sql
SELECT ID, ISNULL(NAME, '') AS NAME
FROM dbo.DIVISION
WHERE NAME IS NOT NULL AND RTRIM(NAME) != ''
ORDER BY NAME
```

---

### v1 — UDFEMP Column Discovery

**Function:** `database.get_udfemp_columns()`

```sql
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'UDFEMP'
ORDER BY ORDINAL_POSITION
```
