import subprocess
import sys
import os
import tempfile
from pathlib import Path

TASK_NAME = "LenelAttendanceManager"


def _get_pythonw():
    """pythonw.exe launches without a console window."""
    p = Path(sys.executable).parent / 'pythonw.exe'
    return str(p) if p.exists() else sys.executable


def get_launch_info():
    """Return (executable, arguments_string) for Task Scheduler."""
    if getattr(sys, 'frozen', False):
        return sys.executable, ''
    # Use .pyw launcher so no console window appears
    script = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LenelAttendance.pyw')
    )
    return _get_pythonw(), f'"{script}"'


def is_registered():
    r = subprocess.run(
        ['schtasks', '/query', '/tn', TASK_NAME],
        capture_output=True
    )
    return r.returncode == 0


def _xml_esc(s):
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


def register():
    cmd, args = get_launch_info()
    args_el = f'\n      <Arguments>{_xml_esc(args)}</Arguments>' if args else ''

    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Lenel Attendance Report Manager - auto start</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT2M</Interval>
      <Count>5</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{_xml_esc(cmd)}</Command>{args_el}
    </Exec>
  </Actions>
</Task>"""

    import os as _os
    fd, tmp_path = tempfile.mkstemp(suffix='.xml', prefix='lenel_task_')
    try:
        with _os.fdopen(fd, 'w', encoding='utf-16') as fh:
            fh.write(xml)
        r = subprocess.run(
            ['schtasks', '/create', '/tn', TASK_NAME, '/xml', tmp_path, '/f'],
            capture_output=True, text=True
        )
    finally:
        try:
            _os.unlink(tmp_path)
        except Exception:
            pass

    if r.returncode == 0:
        return True, "Registered. App will start automatically at login and restart if it crashes (up to 5 times)."
    return False, (r.stderr or r.stdout or 'Unknown error').strip()


def unregister():
    r = subprocess.run(
        ['schtasks', '/delete', '/tn', TASK_NAME, '/f'],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        return True, "Removed from startup."
    return False, (r.stderr or r.stdout or 'Unknown error').strip()
