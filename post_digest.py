#!/usr/bin/env python3
"""Post the HipHipHip digest to Slack.

Reads one row from the PostHog endpoint `hiphiphip_digest_metrics`, builds a
Slack Block Kit message (each metric as its own bold number in a two-column
grid, plus the intended amount), and posts it to a Slack incoming webhook.

No third-party dependencies - standard library only.

Environment variables (set as GitHub Actions secrets):
  POSTHOG_API_KEY    - PostHog personal API key (read scope)
  SLACK_WEBHOOK_URL  - Slack incoming webhook URL for the target channel
Optional overrides:
  POSTHOG_PROJECT_ID - default "629288"
  POSTHOG_ENDPOINT   - default "hiphiphip_digest_metrics"
  POSTHOG_HOST       - default "https://us.posthog.com"

Usage:
  python post_digest.py --window 24h
  python post_digest.py --window 7d --title "HipHipHip - last 7 days"
"""

import argparse
import json
import os
import sys
import urllib.request

HOST = os.environ.get("POSTHOG_HOST", "https://us.posthog.com")
PROJECT_ID = os.environ.get("POSTHOG_PROJECT_ID", "629288")
ENDPOINT = os.environ.get("POSTHOG_ENDPOINT", "hiphiphip_digest_metrics")

# (label, column base name) in display order. Window suffix is added at runtime.
METRICS = [
    ("Page views", "page_views"),
    ("Unique viewers", "unique_viewers"),
    ("Pages created", "pages_created"),
    ("Signups started", "signups_started"),
    ("Signups completed", "signups_completed"),
    ("Contribute clicks", "contribute_clicks"),
    ("Payment initiated", "payment_initiated"),
    ("Wall posts", "wall_posts"),
    ("Gift messages", "gift_messages"),
    ("Pages shared", "pages_shared"),
]


def fetch_metrics():
    """Run the endpoint and return {column_name: value}."""
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
    columns = data["columns"]
    row = data["results"][0]
    return dict(zip(columns, row))


def fmt_int(value):
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "0"


def fmt_naira(value):
    try:
        return f"₦{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return "₦0"


def build_payload(metrics, window, title):
    suffix = "_24h" if window == "24h" else "_7d"

    fields = []
    for label, key in METRICS:
        value = fmt_int(metrics.get(key + suffix, 0))
        # label on top, bold number below
        fields.append({"type": "mrkdwn", "text": f"{label}\n*{value}*"})

    amount = fmt_naira(metrics.get("intended_amount" + suffix, 0))

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title, "emoji": True}},
    ]
    # A section holds at most 10 fields; we have 9, so one section is enough.
    for start in range(0, len(fields), 10):
        blocks.append({"type": "section", "fields": fields[start:start + 10]})
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*Intended amount*\n*{amount}*"},
    })
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": "HipHipHip · via PostHog"}],
    })
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", choices=["24h", "7d"], default="24h")
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    title = args.title or (
        "HipHipHip — last 24 hours" if args.window == "24h"
        else "HipHipHip — last 7 days"
    )

    metrics = fetch_metrics()
    payload = build_payload(metrics, args.window, title)
    post_to_slack(payload)
    print(f"Posted {args.window} digest to Slack.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail loudly so the Action run goes red
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
