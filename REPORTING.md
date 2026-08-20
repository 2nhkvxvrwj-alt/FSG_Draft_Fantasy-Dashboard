# Automated reports

The reporting package calculates facts deterministically from the public FPL Draft endpoints and can optionally use the OpenAI Responses API to write the recap. It does not send email yet.

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

## Tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
