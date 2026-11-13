from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestIncomingLotAssignment(TransactionCase):

    def _incoming_picking(self, product):
        picking_type = self.env.ref('stock.picking_type_in')
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        })
        self.env['stock.move'].create({
            'picking_id': picking.id,
            'product_id': product.id,
            'product_uom_qty': 10,
            'product_uom': product.uom_id.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
        })
        picking.action_confirm()
        picking.action_assign()
        return picking

    def test_assigns_a_lot_to_an_incoming_lot_tracked_product(self):
        product = self.env['product.product'].create({
            'name': 'Auto Lot Receipt Test', 'default_code': 'AUTO-LOT-TEST',
            'is_storable': True, 'tracking': 'lot',
        })
        picking = self._incoming_picking(product)

        picking._ddfsc_assign_incoming_lots()

        self.assertTrue(picking.move_line_ids.lot_id)
        self.assertTrue(picking.move_line_ids.lot_id.name.startswith('REC-%s-' % picking.name.replace('/', '-')))

    def test_keeps_a_supplier_lot_entered_before_validation(self):
        product = self.env['product.product'].create({
            'name': 'Supplier Lot Receipt Test', 'default_code': 'SUPPLIER-LOT-TEST',
            'is_storable': True, 'tracking': 'lot',
        })
        picking = self._incoming_picking(product)
        supplier_lot = self.env['stock.lot'].create({
            'name': 'SUPPLIER-BATCH-001', 'product_id': product.id,
        })
        picking.move_line_ids.lot_id = supplier_lot

        picking._ddfsc_assign_incoming_lots()

        self.assertEqual(picking.move_line_ids.lot_id, supplier_lot)
