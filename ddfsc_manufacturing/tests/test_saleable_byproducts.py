from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleableByproducts(TransactionCase):

    def test_pasta_breakage_posts_to_its_own_temp_location(self):
        """A Pasta MO must create saleable breakage stock, not generic scrap."""
        pasta = self.env.ref('ddfsc_manufacturing.product_pasta_long').product_variant_id
        breakage = self.env.ref('ddfsc_manufacturing.product_pasta_breakage').product_variant_id
        line = self.env.ref('ddfsc_manufacturing.wc_pasta')
        location = self.env.ref('ddfsc_manufacturing.loc_pasta_byproduct')
        production = self.env['mrp.production'].create({
            'product_id': pasta.id,
            'product_uom_id': pasta.uom_id.id,
            'product_qty': 1,
            'ddfsc_line_id': line.id,
        })

        production._ddfsc_post_saleable_byproduct(breakage, 3)

        move = self.env['stock.move'].search([
            ('origin', '=', production.name),
            ('product_id', '=', breakage.id),
            ('location_dest_id', '=', location.id),
            ('state', '=', 'done'),
        ])
        self.assertEqual(len(move), 1)
        self.assertEqual(move.quantity, 3)
        self.assertTrue(breakage.sale_ok)

    def test_finished_goods_button_state_finds_existing_transfer(self):
        pasta = self.env.ref('ddfsc_manufacturing.product_pasta_long').product_variant_id
        line = self.env.ref('ddfsc_manufacturing.wc_pasta')
        production = self.env['mrp.production'].create({
            'product_id': pasta.id,
            'product_uom_id': pasta.uom_id.id,
            'product_qty': 1,
            'ddfsc_line_id': line.id,
        })
        request = self.env['ddfsc.store.request'].create({
            'production_id': production.id,
            'ddfsc_department': 'pasta',
            'request_type': 'finished_goods',
        })

        production._compute_ddfsc_fg_request()

        self.assertEqual(production.ddfsc_fg_request_id, request)
        self.assertEqual(production.ddfsc_fg_request_state, 'draft')
