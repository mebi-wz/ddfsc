from odoo import api, models

from ..hooks import LEGACY_TO_VERA, _find_account


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _ddfsc_migrate_vera_draft_lines(self):
        """Move unposted journal items to the Vera accounts during install/upgrade."""
        for company in self.env["res.company"].sudo().search([]):
            line_model = self.sudo().with_company(company).with_context(
                allowed_company_ids=company.ids,
                check_move_validity=False,
            )
            for old_code, new_code in LEGACY_TO_VERA.items():
                old_account = _find_account(self.env, company, old_code)
                new_account = _find_account(self.env, company, new_code)
                if not old_account or not new_account:
                    continue
                draft_lines = line_model.search([
                    ("company_id", "=", company.id),
                    ("move_id.state", "=", "draft"),
                    ("account_id", "=", old_account.id),
                ])
                if draft_lines:
                    draft_lines.write({"account_id": new_account.id})
                if not line_model.search_count([("account_id", "=", old_account.id)]):
                    old_account.write({"active": False})
        return True
