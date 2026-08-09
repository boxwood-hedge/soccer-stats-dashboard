// Vercel serverless function: reads the current game records straight from
// the GitHub Contents API, instead of a GitHub-hosted static URL (Pages or
// raw.githubusercontent.com). Both of those sit behind their own caching
// layers with propagation delays that don't line up with when a save
// actually lands - this hits the same live API save-games.js already uses
// to check the file's current sha before every save, which saves prove is
// immediately consistent (they'd fail with a sha conflict otherwise).
//
// Expects the same GITHUB_TOKEN Vercel environment variable as
// save-games.js (see api/README.md for setup).

const OWNER = "boxwood-hedge";
const REPO = "soccer-stats-dashboard";
const BRANCH = "main";
const PATH = "data/games.json";
const ALLOWED_ORIGIN = "https://boxwood-hedge.github.io";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", ALLOWED_ORIGIN);
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Cache-Control", "no-store");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const apiUrl = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${PATH}?ref=${BRANCH}`;

  try {
    const ghResp = await fetch(apiUrl, {
      headers: {
        Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "soccer-stats-editor-vercel",
      },
    });
    if (!ghResp.ok) {
      res.status(502).json({ error: `Couldn't read the current file (${ghResp.status}).` });
      return;
    }
    const file = await ghResp.json();
    const content = Buffer.from(file.content, "base64").toString("utf8");
    res.status(200).send(content);
  } catch (err) {
    res.status(500).json({ error: err.message || "Unexpected server error." });
  }
}
