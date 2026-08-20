# Automated reports

The reporting package calculates facts deterministically from the public FPL Draft endpoints, uses the OpenAI Responses API to write the recap and sends HTML email through Gmail.

## Award rules

- Best and worst manager use official gameweek points.
- Best and worst player consider starting players who recorded minutes. Zero-minute players are excluded.
- Best and worst transfer compare the incoming player's points with the outgoing player's points for the period. Only accepted waivers and free-agent moves count.
- Worst bench decision is the largest positive points gap between a player left on the bench and an eligible starter.
- The monthly Bacon buyer is the group with the lowest accumulated points in gameweeks whose deadlines fall in that calendar month.
- Weekly emails show gameweek and month-to-date points together. Manager rows are ordered by gameweek points; Bacon-group rows are ordered by month-to-date points.
- Weekly emails also show overall manager standings, rank movement and overall Bacon-group dinner-buyer standings. Dinner standings run highest-to-lowest; the lowest group at the bottom is the current buyer.
- AI commentary must cover the overall manager leader, bottom manager, notable rank/gap changes and the current end-of-season dinner-buyer battle.

The FPL Draft API is undocumented, so the live integration should be checked after the first completed gameweek before email delivery is enabled.

## Local previews

Generate a clearly labelled sample weekly report using the real league manager/team names:

```powershell
.\venv\Scripts\python.exe -m reports.generate --sample --period weekly --league 9292 --gameweek 1 --output report-preview-weekly.html
```

Generate a sample monthly report:

```powershell
.\venv\Scripts\python.exe -m reports.generate --sample --period monthly --league 9292 --month 2026-08 --output report-preview-monthly.html
```

Remove `--sample` after the requested period is finished and data-checked. The live command deliberately refuses unfinished gameweeks.

If `OPENAI_API_KEY` is present, the generator uses `gpt-5.6-luna` for the humorous recap. Without a key, it uses a deterministic fallback paragraph. API keys must be stored in GitHub Actions secrets and never committed.

## Delivery modes

- `dry-run` writes HTML/JSON previews and never sends or updates report state.
- `test` sends only to `TEST_RECIPIENT` and records the report as sent.
- `live` sends via BCC to `REPORT_RECIPIENTS` and records the report as sent.

Scheduled GitHub Actions runs default to `test`. This guarantees the first completed gameweek goes only to the test recipient until the repository variable `REPORT_MODE` is deliberately changed to `live`.

## Banter dial

Set the repository variable `BANTER_LEVEL` from `1` to `5`, or select a level when manually running the workflow:

1. Gentle
2. Light teasing
3. Competitive pub banter
4. Sharp roast
5. Full fantasy-football roast

Every level remains limited to fantasy results and decisions. Personal, sensitive or protected characteristics are always excluded.

## GitHub configuration

In **Settings → Secrets and variables → Actions**, create these repository secrets:

- `OPENAI_API_KEY`
- `GMAIL_USERNAME`
- `GMAIL_APP_PASSWORD`
- `TEST_RECIPIENT`
- `REPORT_RECIPIENTS` (comma-separated; not used while in test mode)

Create these repository variables:

- `REPORT_MODE` = `test`
- `BANTER_LEVEL` = `3` (or the preferred level)

Enable Gmail two-step verification and create a dedicated app password. Never use or store the normal Gmail password.

The scheduled workflow checks at 17 and 47 minutes past each hour. It sends only after FPL marks a gameweek finished and data-checked. Sent periods are stored in `report-state.json`, preventing duplicates. The monthly report sends only when every gameweek whose deadline belongs to that month is complete.

Before enabling live delivery:

1. Run **Fantasy reports** manually in `dry-run` mode and inspect its artifact.
2. Run it in `test` mode and inspect the email sent only to `TEST_RECIPIENT`.
3. Leave `REPORT_MODE=test` for Gameweek 1.
4. After approving that email, change `REPORT_MODE` to `live` for subsequent weeks.

The manual workflow's **sample** checkbox uses labelled sample scores to test OpenAI and Gmail before a gameweek is complete. Samples cannot use live delivery and never modify `report-state.json`.

## Tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
