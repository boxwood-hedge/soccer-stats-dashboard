// Vercel serverless function: proxies game-record saves from edit.html to
// the GitHub Contents API. The GitHub token never reaches the browser or
// this git repo - it lives only as a Vercel environment variable (see
// api/README.md for setup).
//
// Expects two Vercel environment variables:
//   GITHUB_TOKEN  - fine-grained PAT, Contents: read/write on this repo only
//   EDIT_PASSWORD - same password as the dashboard's edit gate ("soccer118")

const OWNER = "boxwood-hedge";
const REPO = "soccer-stats-dashboard";
const BRANCH = "main";
const PATH = "data/games.json";
const ALLOWED_ORIGIN = "https://boxwood-hedge.github.io";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", ALLOWED_ORIGIN);
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method not allowed" });
    return;
  }

  const { password, games } = req.body || {};

  if (password !== process.env.EDIT_PASSWORD) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }
  if (!Array.isArray(games)) {
    res.status(400).json({ error: "Missing games array" });
    return;
  }

  const apiUrl = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${PATH}`;
  const ghHeaders = {
    Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "User-Agent": "soccer-stats-editor-vercel",
  };

  try {
    const getResp = await fetch(`${apiUrl}?ref=${BRANCH}`, { headers: ghHeaders });
    if (!getResp.ok) {
      res.status(502).json({ error: `Couldn't read the current file (${getResp.status}).` });
      return;
    }
    const currentFile = await getResp.json();

    const newContent = JSON.stringify({ games }, null, 2);
    const contentBase64 = Buffer.from(newContent, "utf8").toString("base64");

    const putResp = await fetch(apiUrl, {
      method: "PUT",
      headers: { ...ghHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "Update game records via dashboard editor",
        content: contentBase64,
        sha: currentFile.sha,
        branch: BRANCH,
      }),
    });

    if (!putResp.ok) {
      const errBody = await putResp.json().catch(() => ({}));
      res.status(502).json({ error: errBody.message || `Save failed (${putResp.status}).` });
      return;
    }

    res.status(200).json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: err.message || "Unexpected server error." });
  }
}
