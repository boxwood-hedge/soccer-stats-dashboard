// Cloudflare Worker: proxies game-record saves from edit.html to the GitHub
// Contents API. The GitHub token never reaches the browser or the git repo -
// it lives only as a Worker secret (see README in this folder for setup).
//
// Expects two Worker secrets:
//   GITHUB_TOKEN  - fine-grained PAT, Contents: read/write on this repo only
//   EDIT_PASSWORD - same password as the dashboard's edit gate ("soccer118")

const OWNER = "boxwood-hedge";
const REPO = "soccer-stats-dashboard";
const BRANCH = "main";
const PATH = "data/games.json";
const ALLOWED_ORIGIN = "https://boxwood-hedge.github.io";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders(), "Content-Type": "application/json" },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "POST") {
      return json({ error: "Method not allowed" }, 405);
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ error: "Invalid JSON body" }, 400);
    }

    if (body.password !== env.EDIT_PASSWORD) {
      return json({ error: "Unauthorized" }, 401);
    }
    if (!Array.isArray(body.games)) {
      return json({ error: "Missing games array" }, 400);
    }

    const apiUrl = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${PATH}`;
    const ghHeaders = {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "soccer-stats-editor-worker",
    };

    const getResp = await fetch(`${apiUrl}?ref=${BRANCH}`, { headers: ghHeaders });
    if (!getResp.ok) {
      return json({ error: `Couldn't read the current file (${getResp.status}).` }, 502);
    }
    const currentFile = await getResp.json();

    const newContent = JSON.stringify({ games: body.games }, null, 2);
    const contentBase64 = btoa(String.fromCharCode(...new TextEncoder().encode(newContent)));

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
      return json({ error: errBody.message || `Save failed (${putResp.status}).` }, 502);
    }

    return json({ ok: true });
  },
};
