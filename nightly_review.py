#!/usr/bin/env python3
"""Post the HipHipHip nightly review to Slack.

Reads one row from the PostHog endpoint `hiphiphip_nightly_review` (today's
signup and contribution drop-off plus friction session counts) and posts a
Slack message with a direct "watch" link to the relevant replay playlist for
each surface. The point is triage: a glance at the counts, then click into
only the surfaces that had activity, instead of watching every session.

No third-party dependencies - standard library only.

Environment variables (GitHub Actions secrets, same as the digest):
  POSTHOG_API_KEY    - PostHog personal API key (read scope)
  SLACK_WEBHOOK_URL  - Slack incoming webhook for #analytics-digest
Optional overrides:
  POSTHOG_PROJECT_ID - default "629288"
  POSTHOG_ENDPOINT   - default "hiphiphip_nightly_review"
  POSTHOG_HOST       - default "https://us.posthog.com"
"""

import json
import os
import sys
import urllib.request
from datetime import datetime

HOST = os.environ.get("POSTHOG_HOST", "https://us.posthog.com")
PROJECT_ID = os.environ.get("POSTHOG_PROJECT_ID", "629288")
ENDPOINT = os.environ.get("POSTHOG_ENDPOINT", "hiphiphip_nightly_review")

# Replay playlist links (one per surface).
_BASE = f"{HOST}/project/{PROJECT_ID}/replay/playlists"
PLAYLISTS = {
    "signup": f"{_BASE}/ZVY0bjIJ",      # Signup flow sessions
    "contrib": f"{_BASE}/lIARkINt",     # Contribution flow sessions
    "rage": f"{_BASE}/UYfnI6wx",        # Recordings with Rage Clicks (default)
    "dead": f"{_BASE}/V6NhTWzB",        # Dead click sessions
    "console": f"{_BASE}/G0D79rg4",     # Recordings with 5+ console log errors (default)
}


def fetch_metrics():
    api_key = os.environ["POSTHOG_API_KEY"]
    url = f"{HOST}/api/projects/{PROJECT_ID}/endpoints/{ENDPOINT}/run"
    req = urllib.request.Request(
        url,
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    return dict(zip(data["columns"], data["results"][0]))


def lagos_date():
    """Today's date in Africa/Lagos, for the footer. Falls back to UTC."""
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("Africa/Lagos"))
    except Exception:
        now = datetime.utcnow()
    return now.strftime("%a %d %b %Y")


def i(metrics, key):
    try:
        return int(metrics.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def build_payload(metrics):
    s_start = i(metrics, "signups_started")
    s_done = i(metrics, "signups_completed")
    s_drop = max(0, s_start - s_done)

    c_start = i(metrics, "contrib_started")
    c_pay = i(metrics, "contrib_payment")
    c_drop = max(0, c_start - c_pay)

    rage = i(metrics, "rageclick_sessions")
    dead = i(metrics, "deadclick_sessions")

    signup_line = (
        f"*Signups:* {s_start} started, {s_done} completed, "
        f"*{s_drop} didn't finish*   <{PLAYLISTS['signup']}|watch drop-offs>"
    )
    contrib_line = (
        f"*Contributions:* {c_start} clicked Contribute, {c_pay} reached payment, "
        f"*{c_drop} didn't*   <{PLAYLISTS['contrib']}|watch drop-offs>"
    )
    friction_line = (
        f"*Friction:* {rage} rage-click · {dead} dead-click sessions today\n"
        f"Watch: <{PLAYLISTS['rage']}|Rage> · "
        f"<{PLAYLISTS['dead']}|Dead clicks> · "
        f"<{PLAYLISTS['console']}|Console errors>"
    )

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "HipHipHip nightly review", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": signup_line}},
        {"type": "section", "text": {"type": "mrkdwn", "text": contrib_line}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": friction_line}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"{lagos_date()} · counts are for today · via PostHog"}
        ]},
    ]
    return {"blocks": blocks}


def post_to_slack(payload):
    webhook = os.environ["SLACK_WEBHOOK_URL"]
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "replace")
        if resp.status != 200 or body.strip() != "ok":
            raise RuntimeError(f"Slack responded {resp.status}: {body}")


def main():
    metrics = fetch_metrics()
    post_to_slack(build_payload(metrics))
    print("Posted nightly review to Slack.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
