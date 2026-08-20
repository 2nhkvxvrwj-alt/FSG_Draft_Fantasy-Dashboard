import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from reports.analysis import add_running_totals, analyse_month, analyse_week
from reports.email_delivery import parse_recipients, send_report
from reports.fpl_client import normalize_live_elements
from reports.render import banter_instructions, render_html
from reports.runner import read_state, validate_delivery, write_state


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

        rendered = render_html(report, "Opening joke.\n\nSecond paragraph.", sample=True)
        self.assertIn("Matchday Gossip", rendered)
        self.assertIn("Who's Buying Dinner?", rendered)
        self.assertIn("NO REAL REPUTATIONS WERE HARMED", rendered)

    def test_banter_level_is_bounded_and_safety_rules_remain(self):
        self.assertIn("level 1/5", banter_instructions(0).lower())
        self.assertIn("level 5/5", banter_instructions(99).lower())
        self.assertIn("protected characteristics", banter_instructions(5))

    def test_recipient_list_accepts_commas_semicolons_and_lines(self):
        result = parse_recipients("one@example.com, two@example.com;three@example.com\nfour@example.com")
        self.assertEqual(len(result), 4)

    def test_report_state_round_trip(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            self.assertEqual(read_state(path), {"weekly": [], "monthly": []})
            write_state(path, {"weekly": ["1"], "monthly": []})
            self.assertEqual(read_state(path)["weekly"], ["1"])

    def test_sample_live_delivery_is_not_a_valid_runner_combination(self):
        with self.assertRaises(ValueError):
            validate_delivery("live", True)

    @patch("reports.email_delivery.smtplib.SMTP_SSL")
    def test_email_uses_bcc_and_undisclosed_to_header(self, smtp_class):
        smtp = smtp_class.return_value.__enter__.return_value
        send_report("Subject", "<p>HTML</p>", "Text", "sender@gmail.com", "app-password", ["test@example.com"])
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], "undisclosed-recipients:;")
        self.assertEqual(message["Bcc"], "test@example.com")


if __name__ == "__main__":
    unittest.main()
