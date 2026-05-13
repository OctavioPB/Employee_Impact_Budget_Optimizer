"""Email notification channel — sends templated emails via SMTP.

Configuration is read from environment variables:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM

In demo mode (no SMTP config), delivery is simulated and logged.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from notifications.engine import Notification, NotificationBundle, NotificationPriority

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

_PRIORITY_LABELS = {
    NotificationPriority.LOW:      "Info",
    NotificationPriority.MEDIUM:   "Notice",
    NotificationPriority.HIGH:     "Action Required",
    NotificationPriority.CRITICAL: "URGENT",
}

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', Arial, sans-serif; color: #1C1C2E; margin: 0; padding: 0; }}
    .header {{ background: #003366; padding: 24px 32px; }}
    .header h1 {{ color: #fff; font-size: 18px; margin: 0; font-weight: 300; }}
    .header span {{ color: #E8C46A; font-style: italic; }}
    .badge {{ display: inline-block; background: {badge_bg}; color: {badge_fg};
              padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
    .body {{ padding: 24px 32px; }}
    .body h2 {{ color: #003366; font-size: 16px; margin: 0 0 12px; }}
    .body p {{ font-size: 14px; line-height: 1.7; color: #374151; }}
    .footer {{ background: #F4F6F9; padding: 16px 32px; font-size: 11px; color: #6B7280; }}
    .cta {{ display: inline-block; margin: 16px 0; background: #003366; color: #fff !important;
             padding: 10px 20px; border-radius: 6px; text-decoration: none; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>O<span>PB</span> · EIBO Platform</h1>
  </div>
  <div class="body">
    <p><span class="badge">{priority_label}</span></p>
    <h2>{title}</h2>
    <p>{body}</p>
    <p><strong>Source:</strong> {source}</p>
    <a class="cta" href="#">View in EIBO Platform →</a>
  </div>
  <div class="footer">
    This is an automated notification from the EIBO Platform.
    You can manage your notification preferences in your profile settings.
  </div>
</body>
</html>
"""

_BADGE_COLORS = {
    NotificationPriority.LOW:      ("#E5E7EB", "#374151"),
    NotificationPriority.MEDIUM:   ("#FEF3C7", "#92400E"),
    NotificationPriority.HIGH:     ("#FEE2E2", "#991B1B"),
    NotificationPriority.CRITICAL: ("#450A0A", "#FECACA"),
}


class EmailChannel:
    """SMTP email channel with HTML templates.

    Falls back to simulation logging when SMTP is not configured.
    """

    def __init__(
        self,
        smtp_host:     str = "",
        smtp_port:     int = 587,
        smtp_user:     str = "",
        smtp_password: str = "",
        email_from:    str = "noreply@eibo.local",
        user_email_map: Optional[dict[str, str]] = None,
    ) -> None:
        self._host      = smtp_host or os.getenv("SMTP_HOST", "")
        self._port      = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self._user      = smtp_user or os.getenv("SMTP_USER", "")
        self._password  = smtp_password or os.getenv("SMTP_PASSWORD", "")
        self._from      = email_from or os.getenv("EMAIL_FROM", "noreply@eibo.local")
        self._user_map  = user_email_map or {}   # user_id → email address
        self._simulated = not bool(self._host)

    def deliver(self, notification: Notification) -> None:
        recipients = self._resolve_recipients(notification.target_user_ids)
        if not recipients:
            logger.debug("Email: no recipients resolved for notification %s",
                         notification.notification_id)
            return
        html = self._render_html(notification)
        subject = f"[EIBO] {_PRIORITY_LABELS[notification.priority]}: {notification.title}"
        for email in recipients:
            self._send(email, subject, html)

    def deliver_bundle(self, bundle: NotificationBundle) -> None:
        subject = f"[EIBO] Digest: {bundle.title}"
        items_html = "".join(
            f"<li><strong>{n.title}</strong> — {n.body}</li>"
            for n in bundle.notifications
        )
        html = f"<ul>{items_html}</ul>"
        for email in self._user_map.values():
            self._send(email, subject, html)

    def _render_html(self, n: Notification) -> str:
        badge_bg, badge_fg = _BADGE_COLORS.get(n.priority, ("#E5E7EB", "#374151"))
        return _HTML_TEMPLATE.format(
            badge_bg=badge_bg, badge_fg=badge_fg,
            priority_label=_PRIORITY_LABELS[n.priority],
            title=n.title, body=n.body, source=n.source,
        )

    def _send(self, to_email: str, subject: str, html: str) -> None:
        if self._simulated:
            logger.info("EMAIL (simulated) → %s | Subject: %s", to_email, subject)
            return
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = self._from
            msg["To"]      = to_email
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                if self._user:
                    server.login(self._user, self._password)
                server.sendmail(self._from, to_email, msg.as_string())
            logger.info("Email delivered to %s", to_email)
        except smtplib.SMTPException as exc:
            logger.error("SMTP delivery failed to %s: %s", to_email, exc)
            raise

    def _resolve_recipients(self, user_ids: list[str]) -> list[str]:
        if not user_ids:
            return list(self._user_map.values())
        return [self._user_map[uid] for uid in user_ids if uid in self._user_map]

    @property
    def is_configured(self) -> bool:
        return not self._simulated
