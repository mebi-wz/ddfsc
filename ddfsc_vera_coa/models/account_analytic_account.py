import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    @api.model
    def _ddfsc_share_product_line_dimension(self):
        """Make Product Line values company-neutral and merge duplicates."""
        plan = self.env["account.analytic.plan"].sudo().search([
            ("name", "=", "Product Line"),
            ("parent_id", "=", False),
        ], limit=1)
        if not plan:
            return True

        analytics = self.sudo().with_context(active_test=False).search([
            ("plan_id", "=", plan.id),
        ], order="code, company_id, id")
        for code in sorted(set(analytics.mapped("code"))):
            matches = analytics.filtered(lambda account: account.code == code)
            master = matches.filtered(lambda account: not account.company_id)[:1] or matches[:1]
            duplicates = matches - master
            if master.company_id:
                master.write({"company_id": False, "active": True})
            for duplicate in duplicates:
                self._ddfsc_replace_analytic_references(duplicate, master)
                duplicate.write({"active": False})
        return True

    @api.model
    def _ddfsc_replace_analytic_references(self, old, new):
        fields = self.env["ir.model.fields"].sudo().search([
            ("relation", "=", "account.analytic.account"),
            ("ttype", "=", "many2one"),
            ("store", "=", True),
        ])
        for field in fields:
            if field.model not in self.env:
                continue
            model = self.env[field.model].sudo().with_context(active_test=False)
            if not model._auto or field.name not in model._fields:
                continue
            try:
                records = model.search([(field.name, "=", old.id)])
                if records:
                    records.write({field.name: new.id})
            except Exception:
                _logger.warning(
                    "Could not replace analytic reference %s.%s from %s to %s",
                    field.model, field.name, old.id, new.id, exc_info=True,
                )

        for model_name in (
            "account.analytic.distribution.model",
            "account.move.line",
            "account.reconcile.model.line",
            "mrp.workcenter",
            "purchase.order.line",
            "sale.order.line",
        ):
            if model_name not in self.env or "analytic_distribution" not in self.env[model_name]._fields:
                continue
            records = self.env[model_name].sudo().search([("analytic_distribution", "!=", False)])
            for record in records:
                distribution = record.analytic_distribution or {}
                changed = False
                replacement = {}
                for key, percentage in distribution.items():
                    ids = key.split(",")
                    mapped = [str(new.id) if item == str(old.id) else item for item in ids]
                    new_key = ",".join(mapped)
                    changed = changed or new_key != key
                    replacement[new_key] = replacement.get(new_key, 0) + percentage
                if changed:
                    record.with_context(check_move_validity=False).write({
                        "analytic_distribution": replacement,
                    })
