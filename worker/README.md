# Game-editor Worker

Holds the GitHub token server-side so it never appears in this repo or the
deployed page. `edit.html` calls this Worker instead of the GitHub API
directly.

## One-time setup

1. Sign in (or sign up, free tier is enough) at https://dash.cloudflare.com.
2. Go to **Workers & Pages** -> **Create** -> **Create Worker**.
3. Give it a name (e.g. `soccer-stats-editor`) and deploy the default template.
4. Click **Edit code**, replace everything with the contents of
   `soccer-stats-editor.js` in this folder, and click **Deploy**.
5. Go to the Worker's **Settings** -> **Variables and Secrets** and add two
   **encrypted** secrets:
   - `GITHUB_TOKEN` - the fine-grained PAT (Contents: read/write on this repo
     only).
   - `EDIT_PASSWORD` - `soccer118` (same password used in the dashboard's
     edit gate).
6. Copy the Worker's URL (shown on its overview page, looks like
   `https://soccer-stats-editor.<your-subdomain>.workers.dev`) and put it in
   `edit.html` as `WORKER_URL`.

Redeploying after an edit to `soccer-stats-editor.js` just means pasting the
updated file into the same Worker's **Edit code** view again and clicking
**Deploy** - no CLI or account changes needed.
