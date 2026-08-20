from collections import defaultdict


def _eligible_player(player):
    return player.get("minutes", 0) > 0


def analyse_week(managers, player_stats, transactions, gameweek):
    """Calculate report facts from normalized manager, player and transfer data."""
    standings = sorted(
        (
            {
                "entry_id": manager["entry_id"],
                "manager": manager["manager"],
                "team": manager["team"],
                "group": manager["group"],
                "points": manager["points"],
            }
            for manager in managers
        ),
        key=lambda row: (-row["points"], row["team"]),
    )

    selected = []
    bench_mistakes = []
    manager_by_entry = {manager["entry_id"]: manager for manager in managers}

    for manager in managers:
        starters = []
        bench = []
        for pick in manager.get("picks", []):
            stats = player_stats.get(pick["element"], {})
            player = {
                "element": pick["element"],
                "name": stats.get("name", f"Player {pick['element']}"),
                "points": stats.get("points", 0),
                "minutes": stats.get("minutes", 0),
                "manager": manager["manager"],
                "team": manager["team"],
                "position": pick["position"],
            }
            (starters if pick["position"] <= 11 else bench).append(player)

        eligible_starters = [player for player in starters if _eligible_player(player)]
        selected.extend(eligible_starters)
        eligible_bench = [player for player in bench if _eligible_player(player)]
        if eligible_starters and eligible_bench:
            benched = max(eligible_bench, key=lambda player: player["points"])
            started = min(eligible_starters, key=lambda player: player["points"])
            if benched["points"] > started["points"]:
                bench_mistakes.append(
                    {
                        "manager": manager["manager"],
                        "team": manager["team"],
                        "benched": benched,
                        "started": started,
                        "cost": benched["points"] - started["points"],
                    }
                )

    transfer_rows = []
    for transaction in transactions:
        if transaction.get("event") != gameweek or transaction.get("result") not in {"a", "accepted"}:
            continue
        manager = manager_by_entry.get(transaction.get("entry"))
        if not manager:
            continue
        incoming = player_stats.get(transaction["element_in"], {})
        outgoing = player_stats.get(transaction["element_out"], {})
        transfer_rows.append(
            {
                "manager": manager["manager"],
                "team": manager["team"],
                "kind": "Waiver" if transaction.get("kind") == "w" else "Free agent",
                "player_in": incoming.get("name", f"Player {transaction['element_in']}"),
                "player_out": outgoing.get("name", f"Player {transaction['element_out']}"),
                "points_in": incoming.get("points", 0),
                "points_out": outgoing.get("points", 0),
                "gain": incoming.get("points", 0) - outgoing.get("points", 0),
            }
        )

    group_points = defaultdict(int)
    for row in standings:
        group_points[row["group"]] += row["points"]

    return {
        "period": "weekly",
        "gameweek": gameweek,
        "standings": standings,
        "group_standings": sorted(
            ({"group": group, "points": points} for group, points in group_points.items()),
            key=lambda row: (-row["points"], row["group"]),
        ),
        "best_manager": standings[0] if standings else None,
        "worst_manager": standings[-1] if standings else None,
        "best_player": max(selected, key=lambda player: player["points"], default=None),
        "worst_player": min(selected, key=lambda player: player["points"], default=None),
        "best_transfer": max(transfer_rows, key=lambda row: row["gain"], default=None),
        "worst_transfer": min(transfer_rows, key=lambda row: row["gain"], default=None),
        "worst_decision": max(bench_mistakes, key=lambda row: row["cost"], default=None),
        "transfers": transfer_rows,
        "selected_players": selected,
    }


def add_running_totals(report, managers, events, gameweek):
    """Add month-to-date and season-to-date tables to a weekly report."""
    event_by_id = {event["id"]: event for event in events}
    current_event = event_by_id[gameweek]
    current_month = current_event["deadline_time"][:7]
    manager_totals = {}

    for manager in managers:
        month_points = 0
        season_points = 0
        previous_points = 0
        for row in manager.get("history", []):
            event_id = row.get("event")
            event = event_by_id.get(event_id)
            if not event or event_id > gameweek:
                continue
            points = row.get("points", 0)
            season_points += points
            if event_id < gameweek:
                previous_points += points
            if event["deadline_time"].startswith(current_month):
                month_points += points
        manager_totals[manager["entry_id"]] = {
            "month_points": month_points,
            "season_points": season_points,
            "previous_points": previous_points,
        }

    previous_order = sorted(
        managers,
        key=lambda manager: (-manager_totals[manager["entry_id"]]["previous_points"], manager["team"]),
    )
    previous_positions = {manager["entry_id"]: index for index, manager in enumerate(previous_order, 1)}

    individuals = []
    overall_individuals = []
    group_gameweek = defaultdict(int)
    group_month = defaultdict(int)
    group_season = defaultdict(int)
    for row in report["standings"]:
        totals = manager_totals[row["entry_id"]]
        individuals.append({**row, "gameweek_points": row["points"], "month_points": totals["month_points"]})
        overall_individuals.append(
            {
                **row,
                "season_points": totals["season_points"],
                "previous_position": previous_positions[row["entry_id"]],
            }
        )
        group_gameweek[row["group"]] += row["points"]
        group_month[row["group"]] += totals["month_points"]
        group_season[row["group"]] += totals["season_points"]

    report["individual_standings"] = sorted(
        individuals, key=lambda row: (-row["gameweek_points"], row["team"])
    )
    report["bacon_standings"] = sorted(
        (
            {"group": group, "gameweek_points": group_gameweek[group], "month_points": points}
            for group, points in group_month.items()
        ),
        key=lambda row: (-row["month_points"], row["group"]),
    )
    overall_individuals = sorted(
        overall_individuals, key=lambda row: (-row["season_points"], row["team"])
    )
    leader_points = overall_individuals[0]["season_points"] if overall_individuals else 0
    for position, row in enumerate(overall_individuals, 1):
        row["position"] = position
        row["position_change"] = row["previous_position"] - position
        row["gap_to_leader"] = leader_points - row["season_points"]
    report["overall_individual_standings"] = overall_individuals
    report["overall_team_standings"] = sorted(
        ({"group": group, "season_points": points} for group, points in group_season.items()),
        key=lambda row: (-row["season_points"], row["group"]),
    )
    report["dinner_buyer"] = report["overall_team_standings"][-1] if report["overall_team_standings"] else None
    report["month"] = current_month
    return report


def analyse_month(weekly_reports, month):
    """Aggregate completed weekly reports into a calendar-month report."""
    manager_totals = defaultdict(lambda: {"points": 0})
    group_totals = defaultdict(int)
    transfers = []
    decisions = []
    player_totals = defaultdict(lambda: {"points": 0, "minutes": 0})

    for report in weekly_reports:
        for row in report["standings"]:
            total = manager_totals[row["entry_id"]]
            total.update({key: row[key] for key in ("entry_id", "manager", "team", "group")})
            total["points"] += row["points"]
        for row in report["group_standings"]:
            group_totals[row["group"]] += row["points"]
        transfers.extend(report["transfers"])
        if report["worst_decision"]:
            decisions.append(report["worst_decision"])
        for player in report.get("selected_players", []):
            total = player_totals[(player["name"], player["manager"])]
            total.update({key: player[key] for key in ("name", "manager", "team")})
            total["points"] += player["points"]
            total["minutes"] += player["minutes"]

    standings = sorted(manager_totals.values(), key=lambda row: (-row["points"], row["team"]))
    groups = sorted(
        ({"group": group, "points": points} for group, points in group_totals.items()),
        key=lambda row: (-row["points"], row["group"]),
    )
    players = list(player_totals.values())
    return {
        "period": "monthly",
        "month": month,
        "gameweeks": [report["gameweek"] for report in weekly_reports],
        "standings": standings,
        "group_standings": groups,
        "best_manager": standings[0] if standings else None,
        "worst_manager": standings[-1] if standings else None,
        "bacon_buyer": groups[-1] if groups else None,
        "best_player": max(players, key=lambda player: player["points"], default=None),
        "worst_player": min(players, key=lambda player: player["points"], default=None),
        "best_transfer": max(transfers, key=lambda row: row["gain"], default=None),
        "worst_transfer": min(transfers, key=lambda row: row["gain"], default=None),
        "worst_decision": max(decisions, key=lambda row: row["cost"], default=None),
        "transfers": transfers,
        "selected_players": players,
    }
