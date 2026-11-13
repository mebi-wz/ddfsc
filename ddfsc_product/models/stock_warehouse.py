# -*- coding: utf-8 -*-
from odoo import fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_main_warehouse = fields.Boolean(
        string='Is Main Warehouse',
        default=False,
        help="Designate this warehouse as the central/main warehouse. Its inventory will be visible (view-only) to all branch and shop users.",
    )
    branch_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Branch Plan',
        compute='_compute_branch_plan_id',
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Branch',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('plan_id', '=?', branch_plan_id)]",
        check_company=True,
        help="Branch / Analytic Account linked to this warehouse.",
    )

    def _compute_branch_plan_id(self):
        plan = self.env.company.get_branch_analytic_plan()
        for wh in self:
            wh.branch_plan_id = plan

    def _get_sequence_values(self, name=False, code=False):
        vals = super()._get_sequence_values(name=name, code=code)
        if 'int_type_id' in vals:
            vals['int_type_id']['prefix'] = 'STR/'
        return vals
