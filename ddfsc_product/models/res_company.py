# -*- coding: utf-8 -*-
from odoo import api, fields, models


def merge_analytic_distribution(existing, account_to_set=None, plan=None, remove_plan=False, env=None):
    """
    Safely merges or replaces an analytic account in a distribution dictionary:
    - If account_to_set is provided: replaces any existing account from account_to_set.plan_id with account_to_set at 100.0%.
    - If remove_plan is True and plan is provided: removes any account from that plan.
    - Preserves accounts from all other plans.
    """
    res = dict(existing) if existing and isinstance(existing, dict) else {}
    if not env and account_to_set:
        env = account_to_set.env
    elif not env and plan:
        env = plan.env

    target_plan = plan or (account_to_set.plan_id if account_to_set else False)
    if target_plan and env:
        plan_acc_ids = set(env['account.analytic.account'].search([('plan_id', '=', target_plan.id)]).ids)
        res = {k: v for k, v in res.items() if (int(k) if str(k).isdigit() else k) not in plan_acc_ids}

    if account_to_set and not remove_plan:
        res[str(account_to_set.id)] = 100.0

    return res if res else False


class ResCompany(models.Model):
    _inherit = 'res.company'

    branch_analytic_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Branch / Location Analytic Plan',
        help="Analytic plan representing Branches / Locations (e.g. Branch / Location).",
    )
    product_analytic_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Product Analytic Plan',
        help="Analytic plan representing Products / Product Lines (e.g. Product Line).",
    )
    cost_center_analytic_plan_id = fields.Many2one(
        'account.analytic.plan',
        string='Cost Center Analytic Plan',
        help="Analytic plan representing Cost Centers / Departments (e.g. Department / Cost Center).",
    )

    def get_branch_analytic_plan(self):
        self.ensure_one()
        if self.branch_analytic_plan_id:
            return self.branch_analytic_plan_id
        plan = self.env['account.analytic.plan'].search([
            '|', ('name', 'ilike', 'Branch'), ('name', 'ilike', 'Location')
        ], limit=1)
        if plan:
            self.sudo().branch_analytic_plan_id = plan
        return plan

    def get_product_analytic_plan(self):
        self.ensure_one()
        if self.product_analytic_plan_id:
            return self.product_analytic_plan_id
        plan = self.env['account.analytic.plan'].search([
            '|', ('name', 'ilike', 'Product Line'), ('name', 'ilike', 'Product')
        ], limit=1)
        if plan:
            self.sudo().product_analytic_plan_id = plan
        return plan

    def get_cost_center_analytic_plan(self):
        self.ensure_one()
        if self.cost_center_analytic_plan_id:
            return self.cost_center_analytic_plan_id
        plan = self.env['account.analytic.plan'].search([
            '|', ('name', 'ilike', 'Cost Center'), ('name', 'ilike', 'Department')
        ], limit=1)
        if plan:
            self.sudo().cost_center_analytic_plan_id = plan
        return plan
