"""Email dispatcher -- delivers queued DNA report emails via Resend.

Reads audit_jobs WHERE job_type='email' AND status='queued', sends the
PDF attachment, marks the job done or error.

Sends live transactional email via the Resend API (https://resend.com).
Requires RESEND_API_KEY in the environment; MAIL_FROM controls the sender.

Run standalone:
    python -m app.email_dispatcher           # continuous 5-second poll
    python -m app.email_dispatcher --once    # one pass, exit (cron / tests)

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
        f"Your Decipher DNA report is attached. Headline archetype: {archetype}.\n\n"
        f"Full breakdown across Cognitive Empathy, Emotional Intelligence, "
        f"Pressure Composure and Narrative Persuasion is on page 1.\n\n"
        f"decipher.com.au"
    )
    html_body = (
        "<html><body style='font-family:-apple-system,sans-serif;color:#1c1c1e'>"
        f"<p>Hi {first},</p>"
        "<p>Your <strong>Decipher DNA report</strong> is attached.</p>"
        f"<p>Headline archetype: <strong>{archetype}</strong>. "
        "Full breakdown across the four traits is on page 1; per-trait coaching "
        "actions are on pages 2 and 3.</p>"
        "<p style='color:#636366;font-size:12px;'>decipher.com.au</p>"
        "</body></html>"
    )

    payload = {
        "from": _MAIL_FROM,
        "to": [r["email"]],
        "subject": f"Your Decipher DNA report · {archetype}",
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
    pdf_path  = str(payload.get("pdf_path", ""))

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
        f"  poll={poll_interval}s",
        flush=True,
    )
    while True:
        try:
            while dispatch_one():
                pass
        except Exception as exc:
            print(f"[email_dispatcher] ERROR: {exc}", flush=True)
        time.sleep(poll_interval)


if __name__ == "__main__":
    if "--once" in sys.argv:
        dispatched = dispatch_one()
        print(f"dispatched: {'yes' if dispatched else 'none (queue empty)'}")
    else:
        run()
