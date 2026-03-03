"""
Email service – sends transactional emails via SMTP (Gmail by default).
Uses only Python's built-in smtplib / email.mime — no extra packages needed.
"""

import smtplib
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def send_reset_code_email(to_email: str, reset_code: str) -> None:
    """
    Send a password-reset code to `to_email`.

    Raises:
        RuntimeError – if SMTP credentials are missing or sending fails.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP credentials not configured. "
            "Set SMTP_USER and SMTP_PASSWORD in your .env file."
        )

    # Gmail App Passwords are sometimes written with spaces (e.g. "abcd efgh ijkl mnop")
    # Strip them so smtplib receives the raw 16-char token.
    smtp_password = settings.SMTP_PASSWORD.replace(" ", "")

    subject = "Econex – Your Password Reset Code"
    html_body = _build_reset_email_html(reset_code)
    plain_body = (
        f"Your Econex password reset code is: {reset_code}\n\n"
        f"This code expires in 15 minutes.\n"
        f"If you did not request a reset, please ignore this email."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Econex <{settings.SMTP_USER}>"
    msg["To"] = to_email

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, smtp_password)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        print(f"[EMAIL] Reset code sent successfully to {to_email}")
    except Exception as exc:
        # Print full traceback so you can diagnose the exact problem in uvicorn console
        print(f"[EMAIL] ❌ Failed to send reset email to {to_email}:")
        traceback.print_exc()
        raise RuntimeError(f"Failed to send email: {exc}") from exc



# ── HTML email template ────────────────────────────────────────────────────────

def _build_reset_email_html(code: str) -> str:
    digits = list(code)
    digit_boxes = "".join(
        f"""<span style="
                display:inline-block;
                width:44px; height:52px;
                line-height:52px;
                text-align:center;
                font-size:28px;
                font-weight:700;
                color:#7c3aed;
                background:#f3f0ff;
                border:2px solid #c4b5fd;
                border-radius:8px;
                margin:0 4px;
            ">{d}</span>"""
        for d in digits
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Econex Password Reset</title>
</head>
<body style="margin:0;padding:0;background:#0f0a1e;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f0a1e;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0"
               style="background:linear-gradient(145deg,#1a0d3d,#120830);
                      border:1px solid #7c3aed44;
                      border-radius:16px;
                      overflow:hidden;">

          <!-- Header -->
          <tr>
            <td align="center"
                style="background:linear-gradient(135deg,#7c3aed,#5b21b6);
                       padding:32px 40px;">
              <p style="margin:0;font-size:28px;font-weight:800;color:#fff;
                         letter-spacing:2px;">ECONEX</p>
              <p style="margin:6px 0 0;font-size:13px;color:#c4b5fd;
                         letter-spacing:1px;">ECONOMIC INTELLIGENCE PLATFORM</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 44px;">
              <p style="margin:0 0 8px;font-size:22px;font-weight:700;color:#e9d5ff;">
                Password Reset Request
              </p>
              <p style="margin:0 0 28px;font-size:14px;color:#a78bfa;line-height:1.6;">
                We received a request to reset your Econex account password.
                Use the code below — it expires in&nbsp;<strong style="color:#c4b5fd;">15&nbsp;minutes</strong>.
              </p>

              <!-- Code boxes -->
              <div style="text-align:center;margin:0 0 28px;">
                {digit_boxes}
              </div>

              <p style="margin:0 0 28px;font-size:13px;color:#7c6fa0;line-height:1.6;text-align:center;">
                Enter this code on the verification page to set your new password.
              </p>

              <hr style="border:none;border-top:1px solid #7c3aed33;margin:0 0 24px;" />

              <p style="margin:0;font-size:12px;color:#6b5e8a;line-height:1.7;">
                If you did not request a password reset, you can safely ignore this email —
                your password will not be changed.<br/><br/>
                &copy; 2025 Econex Platform. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
