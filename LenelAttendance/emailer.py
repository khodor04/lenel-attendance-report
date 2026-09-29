import smtplib
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path
from config import get_setting, log_activity

_MAX_RETRIES  = 3
_RETRY_DELAY  = 30   # seconds between attempts


def send_report_email(recipients: list, cc: list, subject: str,
                       body: str, attachments: list) -> tuple:
    smtp_server = get_setting('smtp_server', '').strip()
    smtp_port = int(get_setting('smtp_port', '587') or '587')
    use_tls = get_setting('smtp_use_tls', '1') == '1'
    smtp_user = get_setting('smtp_user', '').strip()
    smtp_password = get_setting('smtp_password', '').strip()
    smtp_from = (get_setting('smtp_from', '').strip() or smtp_user)

    if not smtp_server:
        return False, "SMTP server not configured. Go to Settings → Email."
    if not recipients:
        return False, "No recipients specified."

    # Build the message once — reused across retry attempts
    msg = MIMEMultipart()
    msg['From'] = smtp_from
    msg['To'] = ', '.join(recipients)
    if cc:
        msg['Cc'] = ', '.join(cc)
    msg['Subject'] = subject
    msg.attach(MIMEText(body or 'Please find the attendance report attached.', 'plain'))

    for file_path in attachments:
        p = Path(file_path)
        if p.exists():
            with open(p, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{p.name}"')
            msg.attach(part)

    all_to = list(recipients) + (cc or [])
    raw_msg = msg.as_string()

    last_error = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            if use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    if smtp_user:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, all_to, raw_msg)
            else:
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                    if smtp_user:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, all_to, raw_msg)

            log_activity(
                f"Email sent to {', '.join(recipients)} | Subject: {subject}"
                + (f" (attempt {attempt})" if attempt > 1 else ""), 'INFO')
            return True, f"Email sent to {', '.join(recipients)}"

        except Exception as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                log_activity(
                    f"Email attempt {attempt}/{_MAX_RETRIES} failed: {e} "
                    f"— retrying in {_RETRY_DELAY}s", 'WARNING')
                time.sleep(_RETRY_DELAY)
            else:
                log_activity(
                    f"Email failed after {_MAX_RETRIES} attempts: {e}", 'ERROR')

    return False, str(last_error)


def test_smtp() -> tuple:
    smtp_server = get_setting('smtp_server', '').strip()
    smtp_port = int(get_setting('smtp_port', '587') or '587')
    use_tls = get_setting('smtp_use_tls', '1') == '1'
    smtp_user = get_setting('smtp_user', '').strip()
    smtp_password = get_setting('smtp_password', '').strip()

    if not smtp_server:
        return False, "SMTP server not configured."
    try:
        if use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.ehlo()
                server.starttls(context=context)
                if smtp_user:
                    server.login(smtp_user, smtp_password)
        else:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10) as server:
                if smtp_user:
                    server.login(smtp_user, smtp_password)
        return True, "SMTP connection successful."
    except Exception as e:
        return False, str(e)
