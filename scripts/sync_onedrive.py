import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

CLIENT_ID = "a590158a-5f89-42c5-a278-b5cbeefc9b0e"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH = "https://graph.microsoft.com/v1.0"

# Game log column layout (0-indexed): Date, Season, Team, Opponent, MP-Ellie,
# MP-Lilly, GF Total, GA Total, G-Ellie, G-Lilly, A-Ellie, A-Lilly, Other Notes.
PLAYERS = [
    {"name": "Ellie", "mp": 4, "goals": 8, "assists": 10},
    {"name": "Lilly", "mp": 5, "goals": 9, "assists": 11},
]
COL_DATE, COL_SEASON, COL_TEAM, COL_OPPONENT = 0, 1, 2, 3
COL_GF, COL_GA, COL_NOTES = 6, 7, 12

# Only import games on/after this date - earlier rows are pre-2025 aggregate
# entries covering many games at once and don't fit the one-row-per-player-game model.
CUTOFF = date(2025, 4, 12)
EXCEL_EPOCH = date(1899, 12, 30)


def post_form(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_json(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def safe_num(value):
    try:
        n = float(value)
        return int(n) if n == int(n) else n
    except (TypeError, ValueError):
        return 0


def cell(row, idx):
    return row[idx] if idx < len(row) else ""


def parse_start_row(address):
    # e.g. "Sheet1!A1:N500" -> 1
    cell_ref = address.split("!")[-1].split(":")[0]
    digits = "".join(ch for ch in cell_ref if ch.isdigit())
    return int(digits) if digits else 1


def parse_games(values, start_row=1):
    games = []
    for offset, row in enumerate(values):
        row_number = start_row + offset
        raw_date = cell(row, COL_DATE)
        if not isinstance(raw_date, (int, float)) or not raw_date:
            continue  # skip title/header/blank rows

        game_date = EXCEL_EPOCH + timedelta(days=int(raw_date))
        if game_date < CUTOFF:
            continue

        season = cell(row, COL_SEASON)
        team = cell(row, COL_TEAM)
        opponent = cell(row, COL_OPPONENT)
        team_gf = safe_num(cell(row, COL_GF))
        team_ga = safe_num(cell(row, COL_GA))
        notes = cell(row, COL_NOTES)

        for p in PLAYERS:
            mp = safe_num(cell(row, p["mp"]))
            if mp <= 0:
                continue  # this player didn't play in this row
            games.append(
                {
                    "rowNumber": row_number,
                    "date": game_date.isoformat(),
                    "season": season,
                    "team": team,
                    "opponent": opponent,
                    "player": p["name"],
                    "goals": safe_num(cell(row, p["goals"])),
                    "assists": safe_num(cell(row, p["assists"])),
                    "teamGoalsFor": team_gf,
                    "teamGoalsAgainst": team_ga,
                    "notes": notes,
                }
            )
    games.sort(key=lambda g: g["date"], reverse=True)
    return games


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

    share_url = os.environ["ONEDRIVE_SHARE_URL"]
    encoded = "u!" + base64.urlsafe_b64encode(share_url.encode()).decode().rstrip("=")

    drive_item = get_json(f"{GRAPH}/shares/{encoded}/driveItem", access_token)
    print("Resolved shared file:", drive_item.get("name"))

    drive_id = drive_item["parentReference"]["driveId"]
    item_id = drive_item["id"]

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
    address = used_range.get("address", "")
    print(f"Used range: {address} ({len(values)} rows)")

    games = parse_games(values, start_row=parse_start_row(address))
    print(f"Parsed {len(games)} player-game record(s) on/after {CUTOFF.isoformat()}.")

    os.makedirs("data", exist_ok=True)
    with open("data/games.json", "w") as f:
        json.dump({"sheet": sheet, "games": games}, f, indent=2)

    print("Wrote data/games.json.")


if __name__ == "__main__":
    main()
