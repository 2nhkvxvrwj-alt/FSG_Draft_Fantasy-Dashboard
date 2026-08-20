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
                    "content": "Write a lively fantasy-football newsletter recap in 5-8 short paragraphs. Open with a punchy headline-style line, use exact scores naturally, and make the jokes specific to the supplied team names, results, transfers and bench decisions. Cover the period awards, overall manager battle (leader, bottom manager, gaps and notable position changes), and end-of-season dinner-buyer battle (including the current lowest Bacon group). Avoid corporate or formal language. Never invent scores, players, transfers or events. " + banter_instructions(banter_level),
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
        detail = "No qualifying victim this time"
        return f"<li><strong>{html.escape(label)}</strong><span>{detail}</span></li>"
    if "player_in" in value:
        detail = f"{value['manager']}: {value['player_in']} for {value['player_out']} ({value['gain']:+d} pts)"
    elif "benched" in value:
        detail = f"{value['manager']} benched {value['benched']['name']} ({value['benched']['points']}) for {value['started']['name']} ({value['started']['points']})"
    elif "name" in value:
        detail = f"{value['name']} — {value['points']} pts ({value['manager']})"
    else:
        detail = f"{value.get('manager', value.get('group'))} — {value['points']} pts"
    return f"<li><strong>{html.escape(label)}</strong><span>{html.escape(detail)}</span></li>"


def _rank(index):
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(index, str(index))


def _movement(value):
    if value > 0:
        return f"▲ {value}"
    if value < 0:
        return f"▼ {abs(value)}"
    return "—"


def _narrative_html(narrative):
    paragraphs = [paragraph.strip() for paragraph in narrative.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        paragraphs = [narrative]
    return "".join(f"<p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>" for paragraph in paragraphs)


def render_html(report, narrative, sample=False):
    title = f"Gameweek {report['gameweek']} Report" if report["period"] == "weekly" else f"{report['month']} Monthly Report"
    if report["period"] == "weekly":
        rows = "".join(
            f"<tr><td class='rank'>{_rank(index)}</td><td><strong>{html.escape(row['team'])}</strong></td><td>{html.escape(row['manager'])}</td><td class='score'>{row['gameweek_points']}</td><td class='score'>{row['month_points']}</td></tr>"
            for index, row in enumerate(report["individual_standings"], 1)
        )
        group_rows = "".join(
            f"<tr><td class='rank'>{_rank(index)}</td><td><strong>{html.escape(row['group'])}</strong></td><td class='score'>{row['gameweek_points']}</td><td class='score'>{row['month_points']}</td></tr>"
            for index, row in enumerate(report["bacon_standings"], 1)
        )
        overall_individual_rows = "".join(
            f"<tr><td class='rank'>{_rank(index)}</td><td><strong>{html.escape(row['team'])}</strong></td><td>{html.escape(row['manager'])}</td><td class='score'>{row['season_points']}</td><td>{_movement(row['position_change'])}</td></tr>"
            for index, row in enumerate(report["overall_individual_standings"], 1)
        )
        overall_team_rows = "".join(
            f"<tr><td class='rank'>{_rank(index)}</td><td><strong>{html.escape(row['group'])}</strong>{' 🍽️' if index == len(report['overall_team_standings']) else ''}</td><td class='score'>{row['season_points']}</td></tr>"
            for index, row in enumerate(report["overall_team_standings"], 1)
        )
        tables = f"""
<h2>⚡ This Week's Damage</h2><p class="section-note">Managers ranked by gameweek points.</p><table><thead><tr><th>#</th><th>Team</th><th>Manager</th><th>GW</th><th>Month</th></tr></thead><tbody>{rows}</tbody></table>
<h2>🥓 The Bacon Battle</h2><p class="section-note">Groups ranked by month-to-date points.</p><table><thead><tr><th>#</th><th>Group</th><th>GW</th><th>Month</th></tr></thead><tbody>{group_rows}</tbody></table>
<h2>🏆 The Long Game</h2><p class="section-note">Overall manager standings and movement.</p><table><thead><tr><th>#</th><th>Team</th><th>Manager</th><th>Season</th><th>Move</th></tr></thead><tbody>{overall_individual_rows}</tbody></table>
<h2>🍽️ Who's Buying Dinner?</h2><p class="section-note">The group wearing the plate-and-cutlery badge at the bottom is currently picking up the bill.</p><table><thead><tr><th>#</th><th>Group</th><th>Season</th></tr></thead><tbody>{overall_team_rows}</tbody></table>"""
    else:
        rows = "".join(
            f"<tr><td class='rank'>{_rank(index)}</td><td><strong>{html.escape(row['team'])}</strong></td><td>{html.escape(row['manager'])}</td><td class='score'>{row['points']}</td></tr>"
            for index, row in enumerate(report["standings"], 1)
        )
        group_rows = "".join(
            f"<tr><td class='rank'>{_rank(index)}</td><td><strong>{html.escape(row['group'])}</strong></td><td class='score'>{row['points']}</td></tr>"
            for index, row in enumerate(report["group_standings"], 1)
        )
        tables = f"""
<h2>📈 Monthly Manager Mayhem</h2><table><thead><tr><th>#</th><th>Team</th><th>Manager</th><th>Points</th></tr></thead><tbody>{rows}</tbody></table>
<h2>🥓 Monthly Bacon Battle</h2><table><thead><tr><th>#</th><th>Group</th><th>Points</th></tr></thead><tbody>{group_rows}</tbody></table>"""
    sample_banner = "<div class='sample'>🧪 SAMPLE DATA — NO REAL REPUTATIONS WERE HARMED</div>" if sample else ""
    bacon = _award("Bacon buyer", report.get("bacon_buyer")) if report["period"] == "monthly" else ""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;background:#160d23;color:#24182d;margin:0;padding:0}}main{{max-width:760px;margin:0 auto;background:#fffaf2}}.hero{{background:#5b163f;color:white;padding:34px 30px 28px;border-bottom:8px solid #ffb000}}.kicker{{color:#ffcf57;font-size:13px;font-weight:bold;letter-spacing:2px;text-transform:uppercase}}h1{{font-size:34px;line-height:1.05;margin:8px 0 0}}.content{{padding:26px 28px 38px}}h2{{color:#5b163f;font-size:23px;margin:32px 0 7px;border-bottom:3px solid #ffb000;padding-bottom:7px}}.sample{{background:#ffcf57;color:#3b1730;padding:11px 16px;font-weight:bold;text-align:center}}.gossip{{background:#fff0cf;border-left:7px solid #ff8a00;padding:15px 18px;border-radius:5px}}.gossip p{{font-size:16px;line-height:1.55;margin:8px 0}}.awards{{list-style:none;padding:0;margin:10px 0}}.awards li{{background:#f4e8f0;border-left:5px solid #8f2d63;margin:9px 0;padding:11px 14px;border-radius:4px}}.awards strong{{display:block;color:#701d4c;font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px}}.awards span{{font-size:15px}}table{{border-collapse:separate;border-spacing:0;width:100%;margin:8px 0 25px;border:1px solid #ead9cf;border-radius:7px;overflow:hidden}}th{{background:#3b1730;color:white;font-size:12px;text-transform:uppercase;letter-spacing:.4px}}th,td{{padding:10px 9px;text-align:left}}tbody tr:nth-child(even){{background:#fff3df}}tbody tr:first-child{{background:#ffe19a}}td{{border-bottom:1px solid #eee0d6}}tbody tr:last-child td{{border-bottom:0}}.rank{{font-size:16px;width:30px}}.score{{font-size:17px;font-weight:bold;color:#6c1f4d}}.section-note{{color:#735f6b;font-size:13px;margin:0 0 8px}}@media(max-width:600px){{h1{{font-size:28px}}.content{{padding:20px 12px}}th,td{{padding:8px 5px;font-size:12px}}}}
</style></head>
<body><main>{sample_banner}<div class="hero"><div class="kicker">FSG Draft Dispatch</div><h1>{html.escape(title)} ⚽</h1></div><div class="content">
<h2>🗣️ Matchday Gossip</h2><div class="gossip">{_narrative_html(narrative)}</div>
<h2>🎭 Heroes, Villains & Questionable Choices</h2><ul class="awards">
{_award('Best manager', report.get('best_manager'))}
{_award('Worst manager', report.get('worst_manager'))}
{_award('Best player', report.get('best_player'))}
{_award('Worst player (played minutes)', report.get('worst_player'))}
{_award('Best transfer', report.get('best_transfer'))}
{_award('Worst transfer', report.get('worst_transfer'))}
{_award('Worst bench decision', report.get('worst_decision'))}
{bacon}</ul>
{tables}
</div></main></body></html>"""
