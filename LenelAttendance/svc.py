"""
Lenel Attendance Report Service
================================
Windows service that runs the scheduler headlessly (no GUI needed).

Commands (use LenelAttendanceSvc.exe when frozen, 'python svc.py' in dev):
  install   -- register as a Windows service (requires admin)
  remove    -- unregister the service
  start     -- start the service
  stop      -- stop the service
  debug     -- run in console for testing (Ctrl+C to stop)
"""
import sys
import os

# Path bootstrap — must happen before any local imports so lenel_app.db resolves
if getattr(sys, 'frozen', False):
    _DIR = os.path.dirname(sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(_DIR)
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import win32serviceutil
import win32service
import win32event
import servicemanager

import config
import scheduler

SVC_NAME        = "LenelAttendanceSvc"
SVC_DISPLAY     = "Lenel Attendance Report Service"
SVC_DESCRIPTION = (
    "Automatically generates and emails attendance reports from Lenel OnGuard "
    "according to configured schedules. Managed by Lenel Attendance Manager."
)


class _LenelService(win32serviceutil.ServiceFramework):
    _svc_name_         = SVC_NAME
    _svc_display_name_ = SVC_DISPLAY
    _svc_description_  = SVC_DESCRIPTION

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        scheduler.stop()
        config.log_activity("Lenel Attendance Service: stopping.", "INFO")
        win32event.SetEvent(self._stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        try:
            config.initialize_db()
            config.log_activity("Lenel Attendance Service: started.", "INFO")
            scheduler.start()
            win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)
        except Exception as exc:
            msg = f"Lenel Attendance Service: fatal error — {exc}"
            config.log_activity(msg, "ERROR")
            servicemanager.LogErrorMsg(msg)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments: launched by SCM — enter the service dispatcher
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(_LenelService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # install / remove / start / stop / debug
        win32serviceutil.HandleCommandLine(_LenelService)
