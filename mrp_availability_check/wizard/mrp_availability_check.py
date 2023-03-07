# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date


class MrpAvailabilityCheck(models.TransientModel):
    _name = "mrp.availability.check"
    _description = 'MRP Availability Check'

    bom_id = fields.Many2one("mrp.bom", 'Bill of Materials', required=True)
    product_id = fields.Many2one('product.product', 'Product', domain="[('type', '=', 'product')]", required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    requested_qty = fields.Float("Quantity", default=1.0, digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one("uom.uom", "UoM", related="product_id.uom_id")
    warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse', required=True)
    line_ids = fields.One2many('mrp.bom.line.check', 'explosion_id')
    sum_line_ids = fields.One2many('mrp.bom.line.check.summarized', 'explosion_id')
    type = fields.Selection(related="bom_id.type")
    lt = fields.Float("LT (days)", related="bom_id.lt")
    dlt = fields.Float("DLT (days)", related="bom_id.dlt")
    clt = fields.Float("CLT (days)", related="bom_id.clt")
    name = fields.Char('Name', default="BoM Availability Check")


    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            if record.product_id:
                domain = self.env['mrp.bom']._bom_find_domain(products=record.product_id, company_id=record.warehouse_id.company_id.id)
                record.bom_id = self.env['mrp.bom'].search(domain, order='sequence, product_id, id', limit=1)

    def bom_explosion(self):
        self.ensure_one()

        def _create_bom_lines(bom, level=0, factor=self.requested_qty):
            level += 1
            for line in bom.bom_line_ids:
                line_id = self.env['mrp.bom.line.check'].create({
                    'product_id': line.product_id.id,
                    'bom_line': line.id,
                    'bom_level': level,
                    'product_qty': line.product_qty * factor,
                    'product_uom_id': line.product_uom_id.id,
                    'warehouse_id': self.warehouse_id.id,
                    'explosion_id': self.id,
                })
                line_id._compute_is_stock_buffered()
                boms = line.product_id.bom_ids
                if boms:
                    line_qty = line.product_uom_id._compute_quantity(line.product_qty, boms[0].product_uom_id)
                    new_factor = factor * line_qty / boms[0].product_qty
                    _create_bom_lines(boms[0], level, new_factor)

        _create_bom_lines(self.bom_id)

    def do_bom_explosion(self):
        self.bom_explosion()
        boms_lines = self.env['mrp.bom.line.check'].search([])
        domain = [('explosion_id', '=', self.id),('product_type', '=', 'product')]
        summarized_bom_lines = boms_lines.read_group(domain, ['product_id', 'product_qty'], ['product_id'], lazy=True)
        for line in summarized_bom_lines:
            self.env['mrp.bom.line.check.summarized'].create({
                'product_id': line['product_id'][0],
                'product_qty': line['product_qty'],
                'warehouse_id': self.warehouse_id.id,
                'explosion_id': self.id,
            })
        self.compute_critical_path()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Availability Check'),
            'auto_search': True,
            'res_model': 'mrp.availability.check',
            'target': 'current',
            'views': [(self.env.ref('mrp_availability_check.mrp_availability_check_view_form2').id, "form")],
            'res_id': self.id,
        }

    #def do_close_action(self):
    #    return {
    #        'type': 'ir.actions.act_window',
    #        'name': _('BoM Availability Check'),
    #        'auto_search': True,
    #        'res_model': 'mrp.availability.check',
    #        'target': 'new',
    #        'views': [(self.env.ref('mrp_availability_check.mrp_availability_check_view_form').id, "form")],
    #        'res_id': self.id,
    #    }

    def compute_critical_path(self):
        self.ensure_one()

        def _compute_critical_path(bom, level=0):
            level += 1
            lines = self.env['mrp.bom.line.check'].search([
                ('bom_level', '=', level),
                ('explosion_id', '=', self.id),
                ('is_stock', '=', False),
                ('bom_id', '=', bom.id)])
            dlt_max = max(lines.mapped('dlt'))
            lines_max = lines.filtered(lambda r: r.dlt == dlt_max)
            lines_max.write({'critical_path': True})
            for bom_line in bom.bom_line_ids:
                boms = bom_line.product_id.bom_ids
                critical_path = self.env['mrp.bom.line.check'].search([
                    ('bom_level', '=', level),
                    ('explosion_id', '=', self.id),
                    ('is_stock', '=', False),
                    ('product_id', '=', bom_line.product_id.id),
                    ('bom_id', '=', bom.id)], limit=1).critical_path
                if boms and critical_path:
                    _compute_critical_path(boms[0], level)

        _compute_critical_path(self.bom_id)


class BomLineCheck(models.TransientModel):
    _name = "mrp.bom.line.check"
    _description = 'MRP Availability Check Bom Line'

    explosion_id = fields.Many2one('mrp.availability.check', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    bom_level = fields.Integer('BoM Level', readonly=True)
    product_qty = fields.Float('Requested Qty', readonly=True, digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', 'UoM', readonly=True)
    bom_line = fields.Many2one("mrp.bom.line", "BoM line", readonly=True)
    bom_id = fields.Many2one("mrp.bom", "BoM", related='bom_line.bom_id', readonly=True)
    produce_delay = fields.Float('Manufacturing Lead Time', related='product_id.produce_delay', readonly=True)
    product_type = fields.Selection(string='Product_type', related='product_id.type', readonly=True)
    purchase_delay = fields.Float('Purchase Lead Time', compute="_get_purchase_delay", readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse', readonly=True)
    make = fields.Boolean("Make", compute="_check_make", readonly=True)
    mto = fields.Boolean("MTO", compute="_check_mto", readonly=True)
    buy = fields.Boolean("Buy", compute="_check_buy", readonly=True)
    sub = fields.Boolean("Sub", compute="_check_buy", readonly=True)
    is_stock = fields.Boolean("Reorder Point", readonly=True)
    lt = fields.Float("LT (days)", related="bom_line.lt", readonly=True)
    dlt = fields.Float("DLT (days)", related="bom_line.dlt", readonly=True, store=True)
    clt = fields.Float("CLT (days)", related="bom_line.clt", readonly=True)
    critical_path = fields.Boolean('Critical Path')


    def _get_purchase_delay(self):
        today = date.today()
        for record in self:
            record.purchase_delay = 0.0
            supplier = self.env["product.supplierinfo"].search([
                ('product_id', '=', record.product_id.id),
                ('date_start', '<=', today),
                ('date_end', '>', today)], limit=1)
            if supplier:
                record.purchase_delay = supplier.delay
                continue
            supplier = self.env["product.supplierinfo"].search([
                ('product_id', '=', record.product_id.id)], limit=1)
            if supplier:
                record.purchase_delay = supplier.delay
                continue
            supplier = self.env["product.supplierinfo"].search([
                ('product_tmpl_id', '=', record.product_id.product_tmpl_id.id),
                ('date_start', '<=', today),
                ('date_end', '>', today)], limit=1)
            if supplier:
                record.purchase_delay = supplier.delay
                continue
            supplier = self.env["product.supplierinfo"].search([
                ('product_tmpl_id', '=', record.product_id.product_tmpl_id.id)], limit=1)
            if supplier:
                record.purchase_delay = supplier.delay
        return True

    def _get_search_stock_buffer_domain(self):
        location_ids = self.bom_id._get_locations()
        domain = [("product_id", "=", self.product_id.id),("location_id", "in", location_ids.ids)]
        return domain

    def _compute_is_stock_buffered(self):
        for record in self:
            domain = record._get_search_stock_buffer_domain()
            reorder_points = self.env["stock.warehouse.orderpoint"].search(domain, limit=1)
            record.is_stock = True if reorder_points else False
        return True

    def _check_make(self):
        for record in self:
            product_routes = record.product_id.route_ids + record.product_id.categ_id.total_route_ids
            check_make = False
            warehouse_id = record.warehouse_id
            wh_make_route = warehouse_id.manufacture_pull_id.route_id
            if wh_make_route and wh_make_route <= product_routes:
                check_make = True
            else:
                make_route = False
                try:
                    make_route = self.env['stock.warehouse']._find_global_route('mrp.route_warehouse0_manufacture', _('Manufacture'))
                except UserError:
                    pass
                if make_route and make_route in product_routes:
                    check_make = True
            record.make = check_make
        return True

    def _check_mto(self):
        for record in self:
            product_routes = record.product_id.route_ids + record.product_id.categ_id.total_route_ids
            check_mto = False
            warehouse_id = record.warehouse_id
            wh_mto_route = warehouse_id.mto_pull_id.route_id
            if wh_mto_route and wh_mto_route <= product_routes:
                check_mto = True
            else:
                mto_route = False
                try:
                    mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Make To Order'))
                except UserError:
                    pass
                if mto_route and mto_route in product_routes:
                    check_mto = True
            record.mto = check_mto
        return True

    def _check_buy(self):
        for record in self:
            product_routes = record.product_id.route_ids + record.product_id.categ_id.total_route_ids
            check_buy = False
            check_sub = False
            warehouse_id = record.warehouse_id
            wh_buy_route = warehouse_id.buy_pull_id.route_id
            if wh_buy_route and wh_buy_route <= product_routes:
                check_buy = True
            else:
                buy_route = False
                try:
                    buy_route = self.env['stock.warehouse']._find_global_route('purchase_stock.route_warehouse0_buy', _('Buy'))
                except UserError:
                    pass
                if buy_route and buy_route in product_routes:
                    check_buy = True
            suppliers = record.product_id._prepare_sellers()
            if suppliers:
                domain = self.env['mrp.bom']._bom_find_domain(products=record.product_id, company_id=warehouse_id.company_id.id, bom_type='subcontract')
                bom = self.env['mrp.bom'].search(domain, order='sequence, product_id, id', limit=1)
                if bom:
                    check_sub = True
            record.buy = check_buy
            record.sub = check_sub
        return True


class BomLineSummarize(models.TransientModel):
    _name = "mrp.bom.line.check.summarized"
    _description = 'MRP Availability Check Bom Line Summarized'

    explosion_id = fields.Many2one('mrp.availability.check', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_qty = fields.Float('Product Qty', readonly=True, digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', 'UoM', related='product_id.uom_id', readonly=True)
    product_type = fields.Selection(string='Product_type', related='product_id.type', readonly=True)
    warehouse_id = fields.Many2one("stock.warehouse", 'Warehouse', readonly=True)
    qty_available = fields.Float("On Hand Qty", compute="_compute_qty_in_source_loc")
    qty_virtual = fields.Float("Available Qty", compute="_compute_qty_in_source_loc")
    qty_incoming = fields.Float("Incoming Qty", compute="_compute_qty_in_source_loc")
    qty_outgoing = fields.Float("Outgoing Qty", compute="_compute_qty_in_source_loc")
    free_qty = fields.Float("Free To Use Qty", compute="_compute_qty_in_source_loc")
    qty_delta = fields.Float("Forecast Qty", compute="_compute_net_qty", readonly=True)
    available = fields.Boolean("Available", compute="_compute_net_qty", readonly=True, default=False)

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        #action['target'] = 'new'
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            'warehouse': self.warehouse_id.id
        }
        return action


    def _compute_qty_in_source_loc(self):
        for record in self:
            if record.product_id.type == "product":
                product = record.product_id
                record.qty_available = product.with_context(warehouse=record.warehouse_id.id).qty_available
                record.qty_virtual = product.with_context(warehouse=record.warehouse_id.id).virtual_available
                record.qty_incoming = product.with_context(warehouse=record.warehouse_id.id).incoming_qty
                record.qty_outgoing = product.with_context(warehouse=record.warehouse_id.id).outgoing_qty
                record.free_qty = product.with_context(warehouse=record.warehouse_id.id).free_qty
            else:
                record.qty_available = False
                record.qty_virtual = False
                record.qty_incoming = False
                record.qty_outgoing = False
                record.free_qty = False
        return True

    @api.onchange('product_qty', 'free_qty')
    def _compute_net_qty(self):
        for record in self:
            record.available = False
            record.qty_delta = False
            if record.product_id.type == "product":
                record.qty_delta = record.free_qty - record.product_qty
            if record.qty_delta >= 0.0 or record.product_id.type != "product":
                record.available = True
        return True

