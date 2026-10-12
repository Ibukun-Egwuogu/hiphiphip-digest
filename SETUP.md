# HipHipHip Slack digest (GitHub Actions)

Posts the HipHipHip metrics to Slack on a schedule. Free, no Power BI, no Microsoft licensing. GitHub Actions runs the script; the script reads the PostHog endpoint and posts a Block Kit message to a Slack channel.

```
post_digest.py                     # the script (stdlib only, no pip installs)
.github/workflows/daily-digest.yml  # runs daily  08:00 Africa/Lagos
.github/workflows/weekly-digest.yml # runs Mondays 08:00 Africa/Lagos
```

## Setup (about 10 minutes, all on your side)

### 1. Put these files in a GitHub repo
Create a repo (private is fine) and commit these files at the repo root, keeping the `.github/workflows/` path exactly as-is.

### 2. PostHog personal API key
PostHog → Settings → Personal API keys → **+ Create**. Give it read-only query scope (least privilege). Copy the value once.

### 3. Slack incoming webhook (for #analytics-digest)
- Go to https://api.slack.com/apps → **Create New App** (or reuse one) → **From scratch** → pick your workspace.
- **Incoming Webhooks** → turn **On** → **Add New Webhook to Workspace** → choose **#analytics-digest** → **Allow**.
- Copy the webhook URL (looks like `https://hooks.slack.com/services/T000/B000/xxxx`).

### 4. Add both as GitHub repo secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `POSTHOG_API_KEY` = the key from step 2
- `SLACK_WEBHOOK_URL` = the URL from step 3

Secrets live only in GitHub. They are never in the code and never shared with anyone.

### 5. Test it now
Repo → **Actions** tab → **HipHipHip daily digest** → **Run workflow** (this is the manual trigger). Check #analytics-digest for the post. Do the same for the weekly one.

Done. After that it runs on its own: daily at 08:00 Lagos, weekly on Mondays at 08:00 Lagos.

## Notes
- **Schedule is UTC under the hood.** `0 7 * * *` = 08:00 Lagos. Change the crons in the two yml files to re-time.
- **Delays:** GitHub's scheduled runs can be a few minutes late under load, and very rarely skipped. Fine for a daily digest.
- **Cost:** each run takes seconds; private-repo Actions minutes are free up to 2,000/month, public repos are unlimited. This uses a negligible amount.
- **Adding a metric later:** it's one line in the endpoint query (ask Claude) and one entry in `METRICS` in `post_digest.py`. Nothing else changes.
- **Changing windows** (e.g. calendar "yesterday" instead of rolling 24h): that's a change to the PostHog endpoint query, not this script.
