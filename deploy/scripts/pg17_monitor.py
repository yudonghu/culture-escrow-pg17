#!/usr/bin/env python3
"""
pg17 health monitor — run by cron every 5 minutes.

Checks:
  1. /health endpoint reachability and ok status
  2. Disk free space (threshold: PG17_DISK_WARN_GB)

Alert policy:
  - Alert only after PG17_MONITOR_FAIL_THRESHOLD consecutive failures (default: 3)
  - Send recovery email when service comes back up
  - State persisted in PG17_MONITOR_STATE_FILE to avoid duplicate alerts

Email: sent via Gmail SMTP using PG17_ALERT_SMTP_* env vars.
"""
from __future__ import annotations

import json
import os
import smtplib
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

# ── Config from env ───────────────────────────────────────────────────────────

HEALTH_URL        = os.getenv("PG17_HEALTH_URL", "http://127.0.0.1:8787/health")
ALERT_TO          = os.getenv("PG17_ALERT_EMAIL", "hydenluc@gmail.com")
SMTP_HOST         = os.getenv("PG17_ALERT_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = int(os.getenv("PG17_ALERT_SMTP_PORT", "587"))
SMTP_USER         = os.getenv("PG17_ALERT_SMTP_USER", "")
SMTP_PASSWORD     = os.getenv("PG17_ALERT_SMTP_PASSWORD", "")
DISK_WARN_GB      = float(os.getenv("PG17_DISK_WARN_GB", "2.0"))
FAIL_THRESHOLD    = int(os.getenv("PG17_MONITOR_FAIL_THRESHOLD", "3"))
STATE_FILE        = Path(os.getenv("PG17_MONITOR_STATE_FILE",
                                   "/var/lib/pg17/monitor_state.json"))

# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"status": "ok", "fail_count": 0, "alerted": False}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state))


def _send_email(subject: str, body: str) -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[monitor] SMTP not configured, skipping email: {subject}", file=sys.stderr)
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = ALERT_TO
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, [ALERT_TO], msg.as_string())
        print(f"[monitor] alert sent → {ALERT_TO}: {subject}")
    except Exception as e:
        print(f"[monitor] email failed: {e}", file=sys.stderr)


# ── Health check ──────────────────────────────────────────────────────────────

def _check() -> tuple[bool, list[str], dict]:
    """Returns (ok, issues, raw_data)."""
    issues: list[str] = []
    raw: dict = {}
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=10) as r:
            raw = json.loads(r.read())
    except Exception as e:
        return False, [f"health endpoint unreachable: {e}"], raw

    if not raw.get("ok"):
        failing = [k for k, v in raw.get("checks", {}).items() if v is False]
        issues.append(f"health ok=false, failing checks: {failing or 'unknown'}")

    disk_gb = raw.get("checks", {}).get("disk_free_gb", 999)
    if isinstance(disk_gb, (int, float)) and disk_gb < DISK_WARN_GB:
        issues.append(f"disk_free_gb={disk_gb:.2f} below threshold {DISK_WARN_GB:.1f} GB")

    return len(issues) == 0, issues, raw


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts = _now_iso()
    ok, issues, raw = _check()
    state = _load_state()

    if ok:
        disk_gb = raw.get("checks", {}).get("disk_free_gb", "?")
        print(f"[monitor] {ts} ok  disk={disk_gb}GB")
        if state.get("alerted"):
            _send_email(
                "[pg17] ✅ Service recovered",
                f"pg17 is healthy again as of {ts}.\n\n"
                f"Health response:\n{json.dumps(raw, indent=2)}",
            )
        _save_state({"status": "ok", "fail_count": 0, "alerted": False})
        sys.exit(0)
    else:
        fail_count = state.get("fail_count", 0) + 1
        alerted    = state.get("alerted", False)
        print(f"[monitor] {ts} FAIL (#{fail_count}) issues={issues}")

        if fail_count >= FAIL_THRESHOLD and not alerted:
            _send_email(
                f"[pg17] 🚨 ALERT: Service unhealthy ({fail_count} consecutive failures)",
                f"pg17 has been unhealthy for {fail_count} consecutive checks.\n\n"
                f"Issues:\n" + "\n".join(f"  • {i}" for i in issues) + "\n\n"
                f"Health response:\n{json.dumps(raw, indent=2)}\n\n"
                f"Time: {ts}\nURL: {HEALTH_URL}",
            )
            alerted = True

        _save_state({"status": "fail", "fail_count": fail_count, "alerted": alerted})
        sys.exit(1)


if __name__ == "__main__":
    main()
