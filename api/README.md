# Game-editor API

Holds the GitHub token server-side so it never appears in this repo or the
deployed page. `edit.html` calls this endpoint instead of the GitHub API
directly.

## One-time setup

1. Sign in at https://vercel.com and click **Add New** -> **Project**.
2. Import the `boxwood-hedge/soccer-stats-dashboard` GitHub repo. Framework
   preset can stay "Other" - no build step is needed, Vercel auto-detects
   `api/save-games.js` as a serverless function.
3. Before the first deploy finishes (or anytime after, via **Settings** ->
   **Environment Variables**), add two variables, applied to Production:
   - `GITHUB_TOKEN` - the fine-grained PAT (Contents: read/write on this repo
     only).
   - `EDIT_PASSWORD` - `soccer118` (same password used in the dashboard's
     edit gate).
4. Deploy. Vercel gives the project a domain like
   `https://soccer-stats-dashboard.vercel.app` - the save endpoint is that
   domain plus `/api/save-games`. Put the full URL in `edit.html` as
   `SAVE_ENDPOINT`.

After this, every push to `main` (including edits to `api/save-games.js`)
auto-deploys through Vercel - same as GitHub Pages auto-deploying the static
site. No manual redeploy step needed.
