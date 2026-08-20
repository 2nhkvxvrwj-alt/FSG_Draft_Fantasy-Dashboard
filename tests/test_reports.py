import unittest

from reports.analysis import add_running_totals, analyse_month, analyse_week
from reports.fpl_client import normalize_live_elements


class ReportAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.players = {
            1: {"name": "Starter Star", "points": 12, "minutes": 90},
            2: {"name": "Starter Flop", "points": -1, "minutes": 90},
            3: {"name": "Did Not Play", "points": 0, "minutes": 0},
            4: {"name": "Bench Hero", "points": 10, "minutes": 90},
            5: {"name": "Outgoing", "points": 2, "minutes": 90},
        }
        self.managers = [
            {"entry_id": 10, "manager": "Manager A", "team": "Team A", "group": "Group A", "points": 21, "picks": [{"element": 1, "position": 1}, {"element": 2, "position": 2}, {"element": 3, "position": 3}, {"element": 4, "position": 12}]},
            {"entry_id": 20, "manager": "Manager B", "team": "Team B", "group": "Group B", "points": 9, "picks": [{"element": 5, "position": 1}]},
        ]

    def test_weekly_awards_and_zero_minute_exclusion(self):
        transactions = [{"event": 1, "result": "a", "kind": "w", "entry": 10, "element_in": 1, "element_out": 5}]
        report = analyse_week(self.managers, self.players, transactions, 1)
        self.assertEqual(report["best_manager"]["manager"], "Manager A")
        self.assertEqual(report["worst_player"]["name"], "Starter Flop")
        self.assertEqual(report["best_transfer"]["gain"], 10)
        self.assertEqual(report["worst_decision"]["cost"], 11)

    def test_denied_transfer_is_ignored(self):
        report = analyse_week(self.managers, self.players, [{"event": 1, "result": "di", "entry": 10, "element_in": 1, "element_out": 5}], 1)
        self.assertIsNone(report["best_transfer"])

    def test_monthly_bacon_buyer_is_lowest_group(self):
        week = analyse_week(self.managers, self.players, [], 1)
        month = analyse_month([week], "Aug 2026")
        self.assertEqual(month["bacon_buyer"]["group"], "Group B")

    def test_monthly_player_points_are_aggregated(self):
        week = analyse_week(self.managers, self.players, [], 1)
        month = analyse_month([week, week], "Aug 2026")
        self.assertEqual(month["best_player"]["name"], "Starter Star")
        self.assertEqual(month["best_player"]["points"], 24)

    def test_draft_live_element_dictionary_is_normalized(self):
        result = normalize_live_elements({"elements": {"42": {"stats": {"total_points": 7}}}})
        self.assertEqual(result[0]["id"], 42)
        self.assertEqual(result[0]["stats"]["total_points"], 7)

    def test_weekly_running_tables_use_requested_sort_orders(self):
        self.managers[0]["history"] = [{"event": 1, "points": 5}, {"event": 2, "points": 21}]
        self.managers[1]["history"] = [{"event": 1, "points": 30}, {"event": 2, "points": 9}]
        report = analyse_week(self.managers, self.players, [], 2)
        events = [
            {"id": 1, "deadline_time": "2026-08-01T12:00:00Z"},
            {"id": 2, "deadline_time": "2026-08-08T12:00:00Z"},
        ]
        report = add_running_totals(report, self.managers, events, 2)
        self.assertEqual(report["individual_standings"][0]["manager"], "Manager A")
        self.assertEqual(report["bacon_standings"][0]["group"], "Group B")
        self.assertEqual(report["overall_team_standings"][0]["group"], "Group B")
        self.assertEqual(report["dinner_buyer"]["group"], "Group A")
        self.assertIn("position_change", report["overall_individual_standings"][0])


if __name__ == "__main__":
    unittest.main()
