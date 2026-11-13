from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVeraCoA(TransactionCase):
    def test_vera_accounts_and_dimensions(self):
        accounts = self.env["account.account"].search([
            ("code", "in", ["1010", "1100", "2000", "4010", "5100", "6010", "8010"])
        ])
        self.assertEqual(len(accounts), 7)
        self.assertEqual(accounts.filtered(lambda a: a.code == "1100").account_type, "asset_receivable")
        self.assertTrue(accounts.filtered(lambda a: a.code == "1100").reconcile)
        self.assertEqual(accounts.filtered(lambda a: a.code == "2000").account_type, "liability_payable")
        self.assertTrue(accounts.filtered(lambda a: a.code == "2000").reconcile)
        plans = self.env["account.analytic.plan"].search([
            ("name", "in", ["Product Line", "Department / Cost Center", "Branch / Location"])
        ])
        self.assertEqual(len(plans), 3)
        analytics = self.env["account.analytic.account"].search([("plan_id", "in", plans.ids)])
        self.assertEqual(len(analytics), 20)
        legacy_draft_lines = self.env["account.move.line"].search_count([
            ("move_id.state", "=", "draft"),
            ("account_id.code", "in", ["121000", "400000"]),
        ])
        self.assertEqual(legacy_draft_lines, 0)
