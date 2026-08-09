# Game-editor API

Holds the GitHub token server-side so it never appears in this repo or the
deployed page. `index.html`/`edit.html` call these endpoints instead of the
GitHub API directly:

- `save-games.js` - writes the games array to `data/games.json` via the
  GitHub Contents API (read-check-sha, then PUT).
- `get-games.js` - reads `data/games.json` via the same Contents API,
  instead of a GitHub-hosted static URL (Pages or raw.githubusercontent.com)
  - both of those sit behind caching/propagation layers that can lag well
  behind an actual commit, which is what made saved edits look like they
  hadn't taken effect.

## One-time setup

1. Sign in at https://vercel.com and click **Add New** -> **Project**.
2. Import the `boxwood-hedge/soccer-stats-dashboard` GitHub repo. Framework
   preset can stay "Other" - no build step is needed, Vercel auto-detects
   `api/save-games.js` and `api/get-games.js` as serverless functions.
3. Before the first deploy finishes (or anytime after, via **Settings** ->
   **Environment Variables**), add two variables, applied to Production:
   - `GITHUB_TOKEN` - the fine-grained PAT (Contents: read/write on this repo
     only).
   - `EDIT_PASSWORD` - `soccer118` (same password used in the dashboard's
     edit gate). Only needed by `save-games.js`.
4. Deploy. Vercel gives the project a domain like
   `https://soccer-stats-dashboard.vercel.app` - the endpoints are that
   domain plus `/api/save-games` and `/api/get-games`. Put the full URLs in
   `index.html`/`edit.html` as `SAVE_ENDPOINT`/`GET_GAMES_ENDPOINT`.

After this, every push to `main` (including edits to the `api/` functions)
auto-deploys through Vercel - same as GitHub Pages auto-deploying the static
site. No manual redeploy step needed.
