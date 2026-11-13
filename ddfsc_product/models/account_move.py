# -*- coding: utf-8 -*-
from odoo import api, fields, models
from .res_company import merge_analytic_distribution


class AccountMove(models.Model):
    _inherit = 'account.move'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse / Branch',
        check_company=True,
        readonly=False,
        help="Warehouse/Branch linked to this invoice. Invoice lines will automatically inherit its Analytic Account for reporting.",
    )

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id_analytics(self):
        branch_account = self.warehouse_id.analytic_account_id if self.warehouse_id else False
        branch_plan = self.company_id.get_branch_analytic_plan()
        for line in self.invoice_line_ids:
            if not line.display_type or line.display_type == 'product':
                line.analytic_distribution = merge_analytic_distribution(
                    line.analytic_distribution,
                    branch_account,
                    plan=branch_plan,
                    remove_plan=not bool(branch_account),
                )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            branch_account = move.warehouse_id.analytic_account_id if move.warehouse_id else False
            branch_plan = move.company_id.get_branch_analytic_plan()
            for line in move.invoice_line_ids:
                if not line.display_type or line.display_type == 'product':
                    dist = line.analytic_distribution or {}
                    if branch_account:
                        dist = merge_analytic_distribution(dist, branch_account, plan=branch_plan)
                    if line.product_id and line.product_id.analytic_account_id:
                        dist = merge_analytic_distribution(dist, line.product_id.analytic_account_id)
                    if dist:
                        line.analytic_distribution = dist
        return moves

    @api.onchange('partner_id')
    def _onchange_partner_id_update_prices(self):
        for line in self.invoice_line_ids:
            if line.product_id:
                line._compute_price_unit()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('product_id')
    def _onchange_product_id_warehouse_analytics(self):
        dist = self.analytic_distribution or {}
        branch_account = self.move_id.warehouse_id.analytic_account_id if self.move_id.warehouse_id else False
        if branch_account:
            dist = merge_analytic_distribution(dist, branch_account, plan=self.move_id.company_id.get_branch_analytic_plan())
        if self.product_id and self.product_id.analytic_account_id:
            dist = merge_analytic_distribution(dist, self.product_id.analytic_account_id)
        self.analytic_distribution = dist

    @api.depends('product_id', 'product_uom_id', 'move_id.partner_id.customer_type')
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_subsection', 'line_note') or line.is_imported:
                continue
            if line.move_id.is_sale_document(include_receipts=True):
                partner = line.move_id.partner_id.commercial_partner_id or line.move_id.partner_id
                if partner and partner.customer_type == 'wholesaler' and line.product_id.wholesale_price > 0:
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.move_id.company_id,
                        line.move_id.currency_id,
                        line.move_id.date,
                        'sale',
                        fiscal_position=line.move_id.fiscal_position_id,
                        product_uom=line.product_uom_id,
                        product_price_unit=line.product_id.wholesale_price,
                    )
