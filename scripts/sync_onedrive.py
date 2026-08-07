import json
import os
import sys
import urllib.parse
import urllib.request

CLIENT_ID = "a590158a-5f89-42c5-a278-b5cbeefc9b0e"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH = "https://graph.microsoft.com/v1.0"

# Game log columns A-N, summary/pivot columns P-X (see index.html for how these render).
GAME_LOG_COLS = slice(0, 14)
SUMMARY_COLS = slice(15, 24)


def post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def main():
    refresh_token = os.environ["MS_GRAPH_REFRESH_TOKEN"]

    token_resp = post_form(
        TOKEN_URL,
        {
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "https://graph.microsoft.com/Files.ReadWrite offline_access",
        },
    )
    access_token = token_resp["access_token"]
    new_refresh_token = token_resp.get("refresh_token", refresh_token)

    if new_refresh_token != refresh_token:
        # Never print token values into the log: Action logs are readable by anyone with
        # repo read access. If rotation breaks the next run, regenerate via device-code
        # login and hand the new value off out-of-band, same as the initial setup.
        print(
            "::warning::Microsoft issued a new refresh token. The stored MS_GRAPH_REFRESH_TOKEN "
            "secret is now stale; if the next run fails to authenticate, redo the device-code "
            "sign-in and update the secret (never via this log)."
        )

    shared = get_json(f"{GRAPH}/me/drive/sharedWithMe", access_token)
    shared_items = shared.get("value", [])
    print(f"Found {len(shared_items)} item(s) shared with this account:")
    for item in shared_items:
        print(" -", item.get("name"), "(", item.get("remoteItem", {}).get("file", {}).get("mimeType", "?"), ")")

    xlsx_items = [item for item in shared_items if item.get("name", "").lower().endswith(".xlsx")]

    if not xlsx_items:
        print("No shared Excel file found. Check that it's shared with this account.")
        sys.exit(1)

    target = xlsx_items[0]
    drive_id = target["remoteItem"]["parentReference"]["driveId"]
    item_id = target["remoteItem"]["id"]

    worksheets = get_json(
        f"{GRAPH}/drives/{drive_id}/items/{item_id}/workbook/worksheets", access_token
    )
    sheet_names = [w["name"] for w in worksheets.get("value", [])]
    print("Worksheets:", sheet_names)

    if not sheet_names:
        print("No worksheets found in the workbook.")
        sys.exit(1)

    sheet = sheet_names[0]
    used_range = get_json(
        f"{GRAPH}/drives/{drive_id}/items/{item_id}/workbook/worksheets('{urllib.parse.quote(sheet)}')/usedRange",
        access_token,
    )
    values = used_range.get("values", [])
    print(f"Used range: {used_range.get('address')} ({len(values)} rows)")

    game_log = [row[GAME_LOG_COLS] for row in values]
    summary = [row[SUMMARY_COLS] for row in values]

    os.makedirs("data", exist_ok=True)
    with open("data/onedrive-export.json", "w") as f:
        json.dump({"sheet": sheet, "gameLog": game_log, "summary": summary}, f, indent=2)

    print(f"Wrote data/onedrive-export.json with {len(game_log)} rows.")


if __name__ == "__main__":
    main()
