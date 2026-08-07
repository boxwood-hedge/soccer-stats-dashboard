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
        print(
            "::warning::Microsoft issued a new refresh token. The MS_GRAPH_REFRESH_TOKEN "
            "secret needs to be updated manually or the next run may fail to authenticate."
        )
        with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as f:
            f.write(
                "\n**Refresh token rotated.** Update the `MS_GRAPH_REFRESH_TOKEN` secret "
                "with the value printed in this step's log (masked runs may hide it; re-run "
                "with debug logging if needed).\n"
            )
        print(f"NEW_REFRESH_TOKEN={new_refresh_token}")

    shared = get_json(f"{GRAPH}/me/drive/sharedWithMe", access_token)
    xlsx_items = [
        item for item in shared.get("value", []) if item.get("name", "").lower().endswith(".xlsx")
    ]

    print(f"Found {len(xlsx_items)} shared .xlsx file(s):")
    for item in xlsx_items:
        print(" -", item["name"])

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
