"""One-time production fix for the missing admin password.

seed.sql inserts the initial admin row (steve@decipher.com.au, role=admin)
with no password_hash at all, so /api/auth/login always returns 401 for
that account until a password is set. This module sets one on startup,
but only if ADMIN_BOOTSTRAP_PASSWORD is present in the environment and
only if the row still has no password_hash -- it will never overwrite a
password that has already been set (by this bootstrap or by a normal
password change).
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def bootstrap_admin_password() -> None:
    from .db import conn, rows

    bootstrap_pw = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
    if not bootstrap_pw:
        return

    admin_email = os.getenv("ADMIN_EMAIL", "steve@decipher.com.au")
    r = rows("SELECT password_hash FROM respondents WHERE email = %s", (admin_email,))
    if not r:
        log.warning("admin_bootstrap: no respondent row for %s", admin_email)
        return
    if r[0].get("password_hash"):
        return

    import bcrypt

    new_hash = bcrypt.hashpw(bootstrap_pw.encode(), bcrypt.gensalt(rounds=12)).decode()
    with conn() as c:
        c.cursor().execute(
            "UPDATE respondents SET password_hash = %s WHERE email = %s",
            (new_hash, admin_email),
        )
    log.info("admin_bootstrap: password set for %s", admin_email)
