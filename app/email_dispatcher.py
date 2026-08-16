"""Email dispatcher -- delivers queued DNA report emails via Resend.

Reads audit_jobs WHERE job_type='email' AND status='queued', sends the
PDF attachment, marks the job done or error.

Sends live transactional email via the Resend API (https://resend.com).
Requires RESEND_API_KEY in the environment; MAIL_FROM controls the sender.

Run standalone:
  python -m app.email_dispatcher            # continuous 5-second poll
  python -m app.email_dispatcher --once      # one pass, exit (cron / tests)

Or call dispatch_one() / send_report_email() from other modules.
"""
from __future__ import annotations

import json
import os
import base64
import sys
import time
import urllib.error
import urllib.request

from app.db import conn, rows, event

_RESEND_API_KEY = os.getenv("RESEND_API_KEY")
_RESEND_API_URL = "https://api.resend.com/emails"
_MAIL_FROM = os.getenv("MAIL_FROM", "Decipher Reports <noreply@decipher.com.au>")


def send_report_email(audit_id: int, report_id: int, pdf_path: str) -> None:
    """Build and deliver the DNA report email via Resend.

    Sets reports.delivered_at on success. Raises on API or missing-file errors.
    """
    rec = rows(
        """SELECT r.email, r.first_name, r.name, ar.name AS archetype_name
           FROM audits a
           JOIN respondents r ON r.respondent_id = a.respondent_id
           LEFT JOIN archetype_assignments aa ON aa.audit_id = a.audit_id
           LEFT JOIN archetypes ar ON ar.archetype_id = aa.archetype_id
           WHERE a.audit_id = %s""",
        (audit_id,),
    )
    if not rec or not rec[0].get("email"):
        raise RuntimeError("recipient_missing")
    r = rec[0]
    first = r.get("first_name") or (r.get("name") or "there").split()[0]
    archetype = r.get("archetype_name") or "see report"

    try:
        with open(pdf_path, "rb") as fh:
            pdf_bytes = fh.read()
    except FileNotFoundError:
        raise RuntimeError(f"pdf_missing:{pdf_path}")

    if not _RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY not configured")

    text_body = (
    f"Hi {first},\n\n"
    f"Your attached Decipher DNA report is a first look at how you actually "
    f"operate in the room, not just how you'd describe it. Headline archetype: "
    f"{archetype}.\n\n"
    f"Knowing your pattern is the start. Reps who improve fastest learn which "
    f"frameworks fit their pattern, then practise them on purpose until it's "
    f"instinct, not something they're thinking about mid-meeting.\n\n"
    f"Reply if you want to talk through what that looks like for you.\n\n"
    f"Steve\n\n"
    f"--\n"
    f"Steve Jones\n"
    f"Trainer & Founder\n"
    f"e: steve@deciphersales.com.au"
)
    html_body = (
    "<html><body style='font-family:-apple-system,sans-serif;color:#1c1c1e'>"
    f"<p>Hi {first},</p>"
    f"<p>Your attached <strong>Decipher DNA report</strong> is a first look at how you actually operate in the room, not just how you'd describe it. Headline archetype: <strong>{archetype}</strong>.</p>"
    "<p>Knowing your pattern is the start. Reps who improve fastest learn which frameworks fit their pattern, then practise them on purpose until it's instinct, not something they're thinking about mid-meeting.</p>"
    "<p>Reply if you want to talk through what that looks like for you.</p>"
    "<p>Steve</p>"
    "<hr style='border:0;border-top:1px solid #e5e5ea;margin:20px 0 12px'>"
    "<p style='font-size:13px;line-height:1.5;color:#1c1c1e;margin:0'>"
    "Steve Jones<br>"
    "<span style='color:#2FA84F;font-weight:600'>Trainer &amp; Founder</span><br>"
    "e: <a href='mailto:steve@deciphersales.com.au' style='color:#1A57C7;text-decoration:none'>steve@deciphersales.com.au</a>"
    "</p>"
    "</body></html>"
)

    payload = {
        "from": _MAIL_FROM,
        "to": [r["email"]],
        "subject": "Your Decipher report",
        "text": text_body,
        "html": html_body,
        "attachments": [
            {
                "filename": os.path.basename(pdf_path),
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    }

    req = urllib.request.Request(
        _RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "decipher-app/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"resend_error:{exc.code}:{body[:300]}")

    with conn() as cdb, cdb.cursor() as cur:
        cur.execute(
            "UPDATE reports SET delivered_at = now(), recipient_email = %s WHERE report_id = %s",
            (r["email"], report_id),
        )


def send_resume_link_email(audit_id: int, resume_url: str) -> None:
    """Email the respondent a link back into their in-progress audit.

    Fired from audit_start() as soon as an audit is created, so they can
    pick up where they left off on any device even if they never come
    back to the original browser tab. The link is only good for as long
    as the audit is still 'in_progress' -- app/api_server.py's
    GET /api/audit/{id}/state (and AuditTake.tsx's handling of it) turns
    it into a plain "already completed" message the moment the audit is
    submitted, so this email does not need its own expiry logic.
    """
    rec = rows(
        """SELECT r.email, r.first_name, r.name, av.name AS version_name
             FROM audits a
             JOIN respondents r ON r.respondent_id = a.respondent_id
             JOIN audit_versions av ON av.audit_version_id = a.audit_version_id
            WHERE a.audit_id = %s""",
        (audit_id,),
    )
    if not rec or not rec[0].get("email"):
        raise RuntimeError("recipient_missing")
    r = rec[0]
    first = r.get("first_name") or (r.get("name") or "there").split()[0]
    version_name = r.get("version_name") or "Sales DNA Audit"

    if not _RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY not configured")

    text_body = (
        f"Hi {first},\n\n"
        f"Here is your link to the {version_name}:\n{resume_url}\n\n"
        f"If you do not finish in one sitting, this same link brings you back "
        f"to exactly where you left off, on this device or any other. Once "
        f"you have completed and submitted the audit, this link stops doing "
        f"anything -- your results are on their way separately.\n\n"
        f"Steve\n\n"
        f"--\n"
        f"Steve Jones\n"
        f"Trainer & Founder\n"
        f"e: steve@deciphersales.com.au"
    )
    html_body = (
        "<html><body style='font-family:-apple-system,sans-serif;color:#1c1c1e'>"
        f"<p>Hi {first},</p>"
        f"<p>Here is your link to the <strong>{version_name}</strong>:</p>"
        f"<p><a href='{resume_url}' style='color:#1A57C7'>{resume_url}</a></p>"
        "<p>If you do not finish in one sitting, this same link brings you back "
        "to exactly where you left off, on this device or any other. Once you "
        "have completed and submitted the audit, this link stops doing "
        "anything -- your results are on their way separately.</p>"
        "<p>Steve</p>"
        "<hr style='border:0;border-top:1px solid #e5e5ea;margin:20px 0 12px'>"
        "<p style='font-size:13px;line-height:1.5;color:#1c1c1e;margin:0'>"
        "Steve Jones<br>"
        "<span style='color:#2FA84F;font-weight:600'>Trainer &amp; Founder</span><br>"
        "e: <a href='mailto:steve@deciphersales.com.au' style='color:#1A57C7;text-decoration:none'>steve@deciphersales.com.au</a>"
        "</p>"
        "</body></html>"
    )

    payload = {
        "from": _MAIL_FROM,
        "to": [r["email"]],
        "subject": f"Your {version_name} link",
        "text": text_body,
        "html": html_body,
    }

    req = urllib.request.Request(
        _RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "decipher-app/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"resend_error:{exc.code}:{body[:300]}")


def dispatch_one() -> bool:
    """Claim and execute one queued email job.

    Returns True if a job was processed (success or error), False if the
    queue was empty.

    Uses FOR UPDATE SKIP LOCKED so concurrent dispatcher instances are safe.
    """
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """UPDATE audit_jobs
               SET status = 'running', started_at = now()
               WHERE job_id = (
                   SELECT job_id FROM audit_jobs
                   WHERE job_type = 'email' AND status = 'queued'
                   ORDER BY enqueued_at
                   FOR UPDATE SKIP LOCKED
                   LIMIT 1
               )
               RETURNING job_id, audit_id, payload""",
        )
        row = cur.fetchone()

    if row is None:
        return False

    job_id, audit_id, payload = row
    if isinstance(payload, str):
        payload = json.loads(payload)
    report_id = int(payload.get("report_id", 0))
    pdf_path = str(payload.get("pdf_path", ""))

    try:
        send_report_email(audit_id, report_id, pdf_path)
        with conn() as c, c.cursor() as cur:
            cur.execute(
                "UPDATE audit_jobs SET status = 'done', finished_at = now() WHERE job_id = %s",
                (job_id,),
            )
        event(
            "email.dispatched",
            actor="email_dispatcher",
            subject_id=str(audit_id),
            payload={"job_id": job_id, "report_id": report_id},
        )
    except Exception as exc:
        with conn() as c, c.cursor() as cur:
            cur.execute(
                """UPDATE audit_jobs
                   SET status = 'error', finished_at = now(), error = %s
                   WHERE job_id = %s""",
                (str(exc)[:500], job_id),
            )
        event(
            "email.dispatch_failed",
            actor="email_dispatcher",
            severity="error",
            subject_id=str(audit_id),
            payload={"job_id": job_id, "error": str(exc)},
        )

    return True


def run(poll_interval: int = 5) -> None:
    """Continuous polling loop. Drains the queue, then sleeps poll_interval seconds."""
    print(
        f"[email_dispatcher] started via Resend, from={_MAIL_FROM}"
        f" poll={poll_interval}s",
        flush=True,
    )
    while True:
        try:
            while dispatch_one():
                pass
        except Exception as exc:
            print(f"[email_dispatcher] ERROR: {exc}", flush=True)
        time.sleep(poll_interval)

def send_login_link_email(to_email: str, first_name: str | None, link: str, welcome: bool = False) -> None:
  """Email a one-time Decipher sign-in link via Resend (welcome=True for first-login invites)."""
  first = first_name or "there"
  subject = "You've been added to Decipher" if welcome else "Your Decipher sign-in link"
  intro = "You've just been added to Decipher. Click below to sign in for the first time." if welcome else "Click the link below to sign in to Decipher."
  footer = "This link expires in 15 minutes and can only be used once. If you did not expect this email, you can ignore it."
  text_body = f"Hi {first}, {intro} Sign in: {link} {footer}"
  html_body = (
    "<html><body style='font-family:-apple-system,sans-serif;color:#1c1c1e'>"
    f"<p>Hi {first},</p><p>{intro}</p>"
    f"<p><a href='{link}' style='background:#1A57C7;color:#fff;padding:12px 18px;text-decoration:none;border-radius:6px;font-weight:600;display:inline-block;'>Sign in to Decipher</a></p>"
    f"<p style='font-size:13px;color:#8e8e93'>{footer}</p></body></html>"
  )
  if not _RESEND_API_KEY:
    raise RuntimeError("RESEND_API_KEY not configured")
  payload = {"from": _MAIL_FROM, "to": [to_email], "subject": subject, "text": text_body, "html": html_body}
  req = urllib.request.Request(
    _RESEND_API_URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {_RESEND_API_KEY}", "Content-Type": "application/json", "User-Agent": "decipher-app/1.0"},
    method="POST",
  )
  try:
    with urllib.request.urlopen(req, timeout=15) as resp:
      resp.read()
  except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", "replace")
    raise RuntimeError(f"resend_error:{exc.code}:{body[:300]}")


if __name__ == "__main__":
    if "--once" in sys.argv:
        dispatched = dispatch_one()
        print(f"dispatched: {'yes' if dispatched else 'none (queue empty)'}")
    else:
        run()
