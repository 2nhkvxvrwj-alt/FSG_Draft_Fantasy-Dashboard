import argparse
import json
from pathlib import Path

from data import TEAM_MAP
from reports.analysis import add_running_totals, analyse_month, analyse_week
from reports.fpl_client import FPLDraftClient, load_week
from reports.render import ai_narrative, render_html


def sample_week(league_entries, gameweek):
    players = {}
    managers = []
    for manager_index, entry in enumerate(league_entries):
        picks = []
        for position in range(1, 16):
            element = manager_index * 20 + position
            points = (element * 7 + gameweek * 3) % 13 - (1 if position <= 11 else 0)
            minutes = 0 if element % 17 == 0 else 90
            players[element] = {"name": f"Sample Player {element}", "points": points, "minutes": minutes}
            picks.append({"element": element, "position": position})
        gameweek_points = sum(players[pick["element"]]["points"] for pick in picks[:11])
        history = [
            {"event": event, "points": gameweek_points + ((event * 3 + manager_index) % 9) - 4}
            for event in range(1, gameweek + 1)
        ]
        managers.append(
            {
                "entry_id": entry["entry_id"],
                "manager": f"{entry['player_first_name']} {entry['player_last_name']}",
                "team": entry["entry_name"],
                "group": TEAM_MAP.get(f"{entry['player_first_name']} {entry['player_last_name']}", "Other"),
                "points": gameweek_points,
                "picks": picks,
                "history": history,
            }
        )
    transactions = []
    for index, manager in enumerate(managers[:3]):
        transactions.append({"event": gameweek, "result": "a", "kind": "w", "entry": manager["entry_id"], "element_in": index * 20 + 1, "element_out": index * 20 + 2})
    return analyse_week(managers, players, transactions, gameweek), managers


def main():
    parser = argparse.ArgumentParser(description="Generate an FPL Draft email report preview")
    parser.add_argument("--league", type=int, default=9292)
    parser.add_argument("--gameweek", type=int, default=1)
    parser.add_argument("--period", choices=("weekly", "monthly"), default="weekly")
    parser.add_argument("--month", help="Calendar month in YYYY-MM format")
    parser.add_argument("--output", type=Path, default=Path("report-preview.html"))
    parser.add_argument("--sample", action="store_true", help="Use clearly labelled sample scores")
    parser.add_argument("--banter-level", type=int, choices=range(1, 6), default=3)
    args = parser.parse_args()

    client = FPLDraftClient()
    if args.period == "weekly":
        bootstrap = client.bootstrap()
        if args.sample:
            report, managers = sample_week(client.league(args.league)["league_entries"], args.gameweek)
        else:
            managers, players, transactions, _ = load_week(client, args.league, args.gameweek)
            report = analyse_week(managers, players, transactions, args.gameweek)
        report = add_running_totals(report, managers, bootstrap["events"], args.gameweek)
    else:
        if not args.month:
            parser.error("--month YYYY-MM is required for monthly reports")
        bootstrap = client.bootstrap()
        events = [
            event for event in bootstrap["events"]
            if event["deadline_time"].startswith(args.month)
            and (args.sample or (event.get("finished") and event.get("data_checked")))
        ]
        if not events:
            parser.error(f"No completed gameweeks found for {args.month}")
        entries = client.league(args.league)["league_entries"]
        weeks = []
        for event in events:
            if args.sample:
                week, _ = sample_week(entries, event["id"])
                weeks.append(week)
            else:
                managers, players, transactions, _ = load_week(client, args.league, event["id"])
                weeks.append(analyse_week(managers, players, transactions, event["id"]))
        report = analyse_month(weeks, args.month)

    narrative, used_ai = ai_narrative(report, banter_level=args.banter_level)
    args.output.write_text(render_html(report, narrative, sample=args.sample), encoding="utf-8")
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {args.output} ({'AI' if used_ai else 'fallback'} narrative)")


if __name__ == "__main__":
    main()
