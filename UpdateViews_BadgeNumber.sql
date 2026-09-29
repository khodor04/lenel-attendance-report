-- ============================================================
-- Lenel Attendance Report - View Update: Add Badge Number
-- Run this on the CLIENT SQL Server (AccessControl database)
-- as an account with ALTER VIEW permission (e.g. sa or DBO)
-- ============================================================

USE AccessControl;
GO

-- ── 1. Update live events view ────────────────────────────────
ALTER VIEW [dbo].[View_EventsTA-App] AS
SELECT
    CONVERT(DATETIME, DATEADD(MINUTE, 240, EVENTS.EVENT_TIME_UTC)) AS Segment_DateTime,
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
    dbo.SEGMENT.NAME           AS Segment,
    CONVERT(NVARCHAR(20), EVENTS.CARDNUM) AS [Badge Number]
FROM dbo.EVENTS AS EVENTS
INNER JOIN      dbo.EVENT      AS EVENT      ON EVENTS.EVENTTYPE = EVENT.EVTYPEID AND EVENTS.EVENTID = EVENT.EVID
LEFT OUTER JOIN dbo.READER     AS READER     ON EVENTS.MACHINE = READER.PANELID AND EVENTS.DEVID = READER.READERID
LEFT OUTER JOIN dbo.EMP        AS EMP        ON EVENTS.EMPID = EMP.ID
INNER JOIN      dbo.ACCESSPANE AS ACCESSPANE ON EVENTS.MACHINE = ACCESSPANE.PANELID
INNER JOIN      dbo.UDFEMP                   ON EMP.ID = dbo.UDFEMP.ID
LEFT OUTER JOIN dbo.SEGMENT                  ON EMP.SEGMENTID = dbo.SEGMENT.SEGMENTID
LEFT OUTER JOIN dbo.DIVISION                 ON dbo.UDFEMP.DIVISION = dbo.DIVISION.ID
WHERE (EVENTS.EVENTTYPE = 0)
  AND (READER.TIMEATT IS NOT NULL)
  AND (READER.TIMEATT > 0);
GO

-- ── 2. Update archive events view ────────────────────────────
ALTER VIEW [dbo].[View_EventsTA_Arc-App] AS
SELECT
    CONVERT(DATETIME, DATEADD(MINUTE, 240, EA.EVENT_TIME_UTC)) AS Segment_DateTime,
    EA.EVENT_TIME_UTC,
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
    dbo.SEGMENT.NAME           AS Segment,
    CONVERT(NVARCHAR(20), EA.CARDNUM) AS [Badge Number]
FROM dbo.EVENTS_ARCHIVED AS EA
INNER JOIN      dbo.EVENT      AS EVENT      ON EA.EVENTTYPE = EVENT.EVTYPEID AND EA.EVENTID = EVENT.EVID
LEFT OUTER JOIN dbo.READER     AS READER     ON EA.MACHINE = READER.PANELID AND EA.DEVID = READER.READERID
LEFT OUTER JOIN dbo.EMP        AS EMP        ON EA.EMPID = EMP.ID
INNER JOIN      dbo.ACCESSPANE AS ACCESSPANE ON EA.MACHINE = ACCESSPANE.PANELID
INNER JOIN      dbo.UDFEMP                   ON EMP.ID = dbo.UDFEMP.ID
LEFT OUTER JOIN dbo.SEGMENT                  ON EMP.SEGMENTID = dbo.SEGMENT.SEGMENTID
LEFT OUTER JOIN dbo.DIVISION                 ON dbo.UDFEMP.DIVISION = dbo.DIVISION.ID
WHERE (EA.EVENTTYPE = 0)
  AND (READER.TIMEATT IS NOT NULL)
  AND (READER.TIMEATT > 0);
GO

-- ── 3. Re-grant SELECT to ReportUser ─────────────────────────
GRANT SELECT ON dbo.[View_EventsTA-App]     TO ReportUser;
GRANT SELECT ON dbo.[View_EventsTA_Arc-App] TO ReportUser;
GO

-- ── 4. Verify: should show Badge Number column with values ────
SELECT TOP 5 [Emp ID], [First Name], [Last Name], [Badge Number], Division
FROM dbo.[View_EventsTA-App]
WHERE [Emp ID] IS NOT NULL;
GO
