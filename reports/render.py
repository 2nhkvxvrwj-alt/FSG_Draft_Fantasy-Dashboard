import html
import json
import os

import requests


def banter_instructions(level):
    level = max(1, min(5, int(level)))
    descriptions = {
        1: "Warm and mostly complimentary, with only very gentle teasing.",
        2: "Light-hearted teasing with a few playful jokes.",
        3: "Competitive pub-level banter with memorable but friendly jokes.",
        4: "A sharp roast with sustained jokes, while remaining good-natured.",
        5: "A full comedic roast: savage about fantasy decisions but never cruel or personal.",
    }
    return (
        f"Banter level {level}/5. {descriptions[level]} "
        "Joke only about fantasy football results and decisions. Do not target protected characteristics, appearance, health, family, employment, private life or other sensitive personal matters. Do not use threats, slurs or genuinely degrading language."
    )


def fallback_narrative(report):
    best = report.get("best_manager")
    worst = report.get("worst_manager")
    if not best:
        return "No completed scores are available yet. The banter department remains on standby."
    narrative = (
        f"{best['manager']} stormed the period with {best['points']} points, while "
        f"{worst['manager']} collected {worst['points']} and an urgent invitation to inspect the bench."
    )
    if report.get("overall_individual_standings"):
        leader = report["overall_individual_standings"][0]
        bottom = report["overall_individual_standings"][-1]
        dinner = report.get("dinner_buyer")
        narrative += f" Overall, {leader['manager']} leads on {leader['season_points']}, with {bottom['manager']} bottom on {bottom['season_points']}."
        if dinner:
            narrative += f" {dinner['group']} currently occupy the end-of-season dinner-buying seat on {dinner['season_points']} points."
    return narrative


def ai_narrative(report, model="gpt-5.6-luna", banter_level=3):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_narrative(report), False
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "reasoning": {"effort": "low"},
            "input": [
                {
                    "role": "developer",
                    "content": "Write a detailed, humorous and competitive fantasy football recap using only the supplied facts. Cover the period awards, the overall manager battle (leader, bottom manager, gaps and notable position changes), and the end-of-season dinner-buyer battle (including the current lowest Bacon group). Never invent scores, players, transfers or events. " + banter_instructions(banter_level),
                },
                {"role": "user", "content": json.dumps(report)},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    text = "".join(
        part.get("text", "")
        for item in data.get("output", [])
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    ).strip()
    return text or fallback_narrative(report), True


def _award(label, value):
    if not value:
        return f"<li><strong>{html.escape(label)}:</strong> No qualifying result</li>"
    if "player_in" in value:
        detail = f"{value['manager']}: {value['player_in']} for {value['player_out']} ({value['gain']:+d} pts)"
    elif "benched" in value:
        detail = f"{value['manager']} benched {value['benched']['name']} ({value['benched']['points']}) for {value['started']['name']} ({value['started']['points']})"
    elif "name" in value:
        detail = f"{value['name']} — {value['points']} pts ({value['manager']})"
    else:
        detail = f"{value.get('manager', value.get('group'))} — {value['points']} pts"
    return f"<li><strong>{html.escape(label)}:</strong> {html.escape(detail)}</li>"


def render_html(report, narrative, sample=False):
    title = f"Gameweek {report['gameweek']} Report" if report["period"] == "weekly" else f"{report['month']} Monthly Report"
    if report["period"] == "weekly":
        rows = "".join(
            f"<tr><td>{index}</td><td>{html.escape(row['team'])}</td><td>{html.escape(row['manager'])}</td><td>{row['gameweek_points']}</td><td>{row['month_points']}</td></tr>"
            for index, row in enumerate(report["individual_standings"], 1)
        )
        group_rows = "".join(
            f"<tr><td>{index}</td><td>{html.escape(row['group'])}</td><td>{row['gameweek_points']}</td><td>{row['month_points']}</td></tr>"
            for index, row in enumerate(report["bacon_standings"], 1)
        )
        overall_individual_rows = "".join(
            f"<tr><td>{index}</td><td>{html.escape(row['team'])}</td><td>{html.escape(row['manager'])}</td><td>{row['season_points']}</td><td>{row['position_change']:+d}</td></tr>"
            for index, row in enumerate(report["overall_individual_standings"], 1)
        )
        overall_team_rows = "".join(
            f"<tr><td>{index}</td><td>{html.escape(row['group'])}</td><td>{row['season_points']}</td></tr>"
            for index, row in enumerate(report["overall_team_standings"], 1)
        )
        tables = f"""
<h2>Manager standings</h2><table><thead><tr><th>#</th><th>Team</th><th>Manager</th><th>GW</th><th>Month</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Bacon standings</h2><table><thead><tr><th>#</th><th>Group</th><th>GW</th><th>Month</th></tr></thead><tbody>{group_rows}</tbody></table>
<h2>Overall manager standings</h2><table><thead><tr><th>#</th><th>Team</th><th>Manager</th><th>Season</th><th>Move</th></tr></thead><tbody>{overall_individual_rows}</tbody></table>
<h2>Dinner buyer standings</h2><p>The lowest-scoring Bacon group at the bottom buys the end-of-season dinner.</p><table><thead><tr><th>#</th><th>Group</th><th>Season</th></tr></thead><tbody>{overall_team_rows}</tbody></table>"""
    else:
        rows = "".join(
            f"<tr><td>{index}</td><td>{html.escape(row['team'])}</td><td>{html.escape(row['manager'])}</td><td>{row['points']}</td></tr>"
            for index, row in enumerate(report["standings"], 1)
        )
        group_rows = "".join(
            f"<tr><td>{index}</td><td>{html.escape(row['group'])}</td><td>{row['points']}</td></tr>"
            for index, row in enumerate(report["group_standings"], 1)
        )
        tables = f"""
<h2>Monthly manager standings</h2><table><thead><tr><th>#</th><th>Team</th><th>Manager</th><th>Points</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Monthly Bacon standings</h2><table><thead><tr><th>#</th><th>Group</th><th>Points</th></tr></thead><tbody>{group_rows}</tbody></table>"""
    sample_banner = "<p class='sample'>SAMPLE DATA — THIS REPORT HAS NOT BEEN EMAILED</p>" if sample else ""
    bacon = _award("Bacon buyer", report.get("bacon_buyer")) if report["period"] == "monthly" else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>body{{font-family:Arial,sans-serif;background:#f5f5f5;color:#222;margin:0}}main{{max-width:760px;margin:24px auto;background:white;padding:28px;border-radius:12px}}h1{{color:#5b163f}}table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.sample{{background:#fff3cd;padding:10px;font-weight:bold}}li{{margin:8px 0}}</style></head>
<body><main>{sample_banner}<h1>{html.escape(title)}</h1><p>{html.escape(narrative)}</p>
<h2>Awards</h2><ul>
{_award('Best manager', report.get('best_manager'))}
{_award('Worst manager', report.get('worst_manager'))}
{_award('Best player', report.get('best_player'))}
{_award('Worst player (played minutes)', report.get('worst_player'))}
{_award('Best transfer', report.get('best_transfer'))}
{_award('Worst transfer', report.get('worst_transfer'))}
{_award('Worst bench decision', report.get('worst_decision'))}
{bacon}</ul>
{tables}
</main></body></html>"""
