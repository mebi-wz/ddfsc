# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    branch_analytic_plan_id = fields.Many2one(
        related='company_id.branch_analytic_plan_id',
        readonly=False,
        string="Branch Analytic Plan",
    )
    product_analytic_plan_id = fields.Many2one(
        related='company_id.product_analytic_plan_id',
        readonly=False,
        string="Product Analytic Plan",
    )
    cost_center_analytic_plan_id = fields.Many2one(
        related='company_id.cost_center_analytic_plan_id',
        readonly=False,
        string="Cost Center Analytic Plan",
    )

