import argparse
import json
import os
from pathlib import Path

from reports.analysis import add_running_totals, analyse_month, analyse_week
from reports.email_delivery import parse_recipients, send_report
from reports.fpl_client import FPLDraftClient, load_week
from reports.generate import sample_week
from reports.render import ai_narrative, render_html


def read_state(path):
    if not path.exists():
        return {"weekly": [], "monthly": []}
    state = json.loads(path.read_text(encoding="utf-8"))
    state.setdefault("weekly", [])
    state.setdefault("monthly", [])
    return state


def write_state(path, state):
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def delivery_recipients(mode):
    if mode == "test":
        return parse_recipients(os.getenv("TEST_RECIPIENT"))
    if mode == "live":
        return parse_recipients(os.getenv("REPORT_RECIPIENTS"))
    return []


def validate_delivery(mode, sample):
    if sample and mode == "live":
        raise ValueError("Sample reports cannot use live delivery mode")


def send_or_preview(report, output_dir, mode, banter_level, label, sample=False):
    narrative, used_ai = ai_narrative(report, banter_level=banter_level)
    html_body = render_html(report, narrative, sample=sample)
    html_path = output_dir / f"{label}.html"
    json_path = output_dir / f"{label}.json"
    html_path.write_text(html_body, encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if mode != "dry-run":
        recipients = delivery_recipients(mode)
        prefix = "[SAMPLE] " if sample else ("[TEST] " if mode == "test" else "")
        period = f"Gameweek {report['gameweek']}" if report["period"] == "weekly" else report["month"]
        send_report(
            f"{prefix}FSG Fantasy Draft — {period} Report",
            html_body,
            narrative,
            os.getenv("GMAIL_USERNAME"),
            os.getenv("GMAIL_APP_PASSWORD"),
            recipients,
        )
    print(f"Generated {label} ({'AI' if used_ai else 'fallback'} narrative, mode={mode})")


def build_week(client, league_id, event, events):
    managers, players, transactions, _ = load_week(client, league_id, event["id"])
    report = analyse_week(managers, players, transactions, event["id"])
    return add_running_totals(report, managers, events, event["id"])


def main():
    parser = argparse.ArgumentParser(description="Generate and optionally email completed FPL Draft reports")
    parser.add_argument("--league", type=int, default=9292)
    parser.add_argument("--mode", choices=("dry-run", "test", "live"), default="dry-run")
    parser.add_argument("--banter-level", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--state", type=Path, default=Path("report-state.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("report-output"))
    parser.add_argument("--sample", action="store_true", help="Send or render a labelled sample without updating state")
    parser.add_argument(
        "--force-gameweek",
        type=int,
        help="Resend one completed gameweek even when it is already recorded as sent",
    )
    args = parser.parse_args()
    try:
        validate_delivery(args.mode, args.sample)
    except ValueError as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    state = read_state(args.state)
    client = FPLDraftClient()
    events = client.bootstrap()["events"]
    if args.sample:
        entries = client.league(args.league)["league_entries"]
        report, managers = sample_week(entries, 1)
        report = add_running_totals(report, managers, events, 1)
        send_or_preview(report, args.output_dir, args.mode, args.banter_level, "sample-gameweek-1", sample=True)
        return
    completed = sorted(
        (event for event in events if event.get("finished") and event.get("data_checked")),
        key=lambda event: event["id"],
    )
    completed_ids = {event["id"] for event in completed}
    if not completed:
        print("No finished and data-checked gameweeks are available; nothing to send.")
        return
    if args.force_gameweek and args.force_gameweek not in completed_ids:
        parser.error(f"Gameweek {args.force_gameweek} is not finished and data-checked")

    weekly_cache = {}
    for event in completed:
        key = str(event["id"])
        if key in state["weekly"] and event["id"] != args.force_gameweek:
            continue
        report = build_week(client, args.league, event, events)
        weekly_cache[event["id"]] = report
        send_or_preview(report, args.output_dir, args.mode, args.banter_level, f"gameweek-{event['id']}")
        if args.mode != "dry-run" and key not in state["weekly"]:
            state["weekly"].append(key)
            write_state(args.state, state)

    months = sorted({event["deadline_time"][:7] for event in completed})
    for month in months:
        if month in state["monthly"]:
            continue
        month_events = [event for event in events if event["deadline_time"].startswith(month)]
        if not month_events or any(event["id"] not in completed_ids for event in month_events):
            continue
        weekly_reports = []
        for event in month_events:
            report = weekly_cache.get(event["id"]) or build_week(client, args.league, event, events)
            weekly_reports.append(report)
        monthly = analyse_month(weekly_reports, month)
        latest = weekly_reports[-1]
        for key in ("overall_individual_standings", "overall_team_standings", "dinner_buyer"):
            monthly[key] = latest.get(key)
        send_or_preview(monthly, args.output_dir, args.mode, args.banter_level, f"month-{month}")
        if args.mode != "dry-run":
            state["monthly"].append(month)
            write_state(args.state, state)


if __name__ == "__main__":
    main()
