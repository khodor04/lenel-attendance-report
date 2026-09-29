-- ============================================================
-- Lenel Attendance App — SQL Setup Script Rev 3
-- Run entirely as sa on the SQL Server instance
-- ============================================================

USE AccessControl;
GO

-- ── 1. Create login ─────────────────────────────────────────
CREATE LOGIN ReportUser
    WITH PASSWORD        = 'YourStrongPassword!',
         DEFAULT_DATABASE = AccessControl,
         CHECK_EXPIRATION = OFF,
         CHECK_POLICY     = OFF;
GO

-- ── 2. Create database user ──────────────────────────────────
CREATE USER ReportUser FOR LOGIN ReportUser;
GO

-- ── 3. Live events view ──────────────────────────────────────
-- Change 240 to match client timezone: UTC+3 = 180, UTC+2 = 120
CREATE OR ALTER VIEW [dbo].[View_EventsTA-App] AS
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
    dbo.SEGMENT.NAME           AS Segment
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

-- ── 4. Archive events view ───────────────────────────────────
-- Uses dbo.EVENTS_ARCHIVED (Lenel bridge view to AccessControl_Archival)
-- No cross-database ownership chaining needed
CREATE OR ALTER VIEW [dbo].[View_EventsTA_Arc-App] AS
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
    dbo.SEGMENT.NAME           AS Segment
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

-- ── 5. Archive config view ───────────────────────────────────
-- App reads this to auto-detect how many days back before switching to archive
CREATE OR ALTER VIEW [dbo].[View_ArchiveConfig-App] AS
SELECT MIN(DAYS_OLD) AS ArchiveAfterDays
FROM dbo.ARCHIVE_CONFIG;
GO

-- ── 6. Grant permissions ─────────────────────────────────────
GRANT SELECT ON [dbo].[View_EventsTA-App]      TO ReportUser;
GRANT SELECT ON [dbo].[View_EventsTA_Arc-App]  TO ReportUser;
GRANT SELECT ON [dbo].[View_ArchiveConfig-App] TO ReportUser;
GO
