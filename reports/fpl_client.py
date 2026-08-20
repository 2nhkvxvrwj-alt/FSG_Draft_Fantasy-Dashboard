import requests

from data import TEAM_MAP


class FPLDraftClient:
    DRAFT = "https://draft.premierleague.com/api"
    CLASSIC = "https://fantasy.premierleague.com/api"

    def __init__(self, timeout=20):
        self.timeout = timeout
        self.session = requests.Session()

    def get(self, url):
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def bootstrap(self):
        return self.get(f"{self.CLASSIC}/bootstrap-static/")

    def league(self, league_id):
        return self.get(f"{self.DRAFT}/league/{league_id}/details")

    def transactions(self, league_id):
        data = self.get(f"{self.DRAFT}/draft/league/{league_id}/transactions")
        return data.get("transactions", data if isinstance(data, list) else [])

    def event_live(self, gameweek):
        return self.get(f"{self.DRAFT}/event/{gameweek}/live")

    def entry_event(self, entry_id, gameweek):
        return self.get(f"{self.DRAFT}/entry/{entry_id}/event/{gameweek}")

    def entry_history(self, entry_id):
        return self.get(f"{self.DRAFT}/entry/{entry_id}/history")


def _event_points(history, gameweek):
    row = next((row for row in history.get("history", []) if row.get("event") == gameweek), None)
    return row.get("points", 0) if row else 0


def normalize_live_elements(live):
    elements = live.get("elements", {})
    if isinstance(elements, dict):
        return [
            {"id": int(element_id), **(value if isinstance(value, dict) else {})}
            for element_id, value in elements.items()
        ]
    return elements


def load_week(client, league_id, gameweek, allow_unfinished=False):
    bootstrap = client.bootstrap()
    event = next((event for event in bootstrap["events"] if event["id"] == gameweek), None)
    if not event:
        raise ValueError(f"Gameweek {gameweek} does not exist")
    if not allow_unfinished and not (event.get("finished") and event.get("data_checked")):
        raise ValueError(f"Gameweek {gameweek} is not finished and data-checked")

    player_names = {
        player["id"]: f"{player['first_name']} {player['second_name']}".strip()
        for player in bootstrap["elements"]
    }
    live = client.event_live(gameweek)
    player_stats = {}
    for player in normalize_live_elements(live):
        stats = player.get("stats", {})
        player_stats[player["id"]] = {
            "name": player_names.get(player["id"], f"Player {player['id']}"),
            "points": stats.get("total_points", player.get("total_points", 0)),
            "minutes": stats.get("minutes", player.get("minutes", 0)),
        }

    managers = []
    for entry in client.league(league_id)["league_entries"]:
        manager_name = f"{entry['player_first_name']} {entry['player_last_name']}"
        picks = client.entry_event(entry["entry_id"], gameweek).get("picks", [])
        history = client.entry_history(entry["entry_id"])
        managers.append(
            {
                "entry_id": entry["entry_id"],
                "manager": manager_name,
                "team": entry["entry_name"],
                "group": TEAM_MAP.get(manager_name, "Other"),
                "points": _event_points(history, gameweek),
                "picks": picks,
                "history": history.get("history", []),
            }
        )

    return managers, player_stats, client.transactions(league_id), event
