# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    custom_product_id = fields.Many2one(
        'product.template', 
        string='Product',
        copy=False
    )

    #@api.multi
    def _qty_count(self):
        for product in self:
            product.custom_qty_available = product.custom_product_id.qty_available

    custom_qty_available = fields.Float(
        compute='_qty_count', 
        string='Quantity On Hand',
        copy=False
    )
    custom_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')], 
        string='Product Type', 
        default='consu', 
        required=False,
        copy=False,
        related='custom_product_id.type',
    )
    rental = fields.Boolean('Can be Rent')

    def custom_action_open_quants(self):
        products = self.custom_product_id.mapped('product_variant_ids')
        #action = self.env.ref('stock.product_open_quants').read()[0]
        # action = self.env.ref('stock.product_template_open_quants').read()[0]
        action = self.env.ref('stock.dashboard_open_quants').read()[0]
        
        action['domain'] = [('product_id', 'in', products.ids)]
        action['context'] = {'search_default_internal_loc': 1}
        return action

    def custom_action_view_stock_move_lines(self):
        self.ensure_one()
        action = self.env.ref('stock.stock_move_line_action').read()[0]
        action['domain'] = [('product_id.product_tmpl_id', 'in', self.custom_product_id.ids)]
        return action

    #@api.multi
    def action_create_product_templete(self):
        action = self.env.ref('fleet_product_link.action_create_product_add_custom').read()[0]
        if self.license_plate:
            action['context'] = {
                'default_name':self.model_id.name + ' (' +  self.license_plate + ')'
            }
        else:
             action['context'] = {
                'default_name':self.model_id.name
            }
        return action

    #@api.multi
    def action_view_product(self):
        self.ensure_one()
        action = self.env.ref('fleet_product_link.action_product_link_all_fleet').read()[0]
        action['domain'] = str([('custom_vehicle_id', 'in', self.ids)])
        return action


    # @Override odoo core method create
    @api.model
    def create(self, vals):
        vehicle = super(FleetVehicle, self).create(vals)
        vehicle.action_sync_products()
        return vehicle

    # @Override odoo core method write
    def write(self, vals):
        result = super(FleetVehicle, self).write(vals)
        if vals.get('custom_product_id'):
            self.action_sync_products()
        return result

    def action_sync_products(self):
        for record in self:
            if record.custom_product_id:
                record.custom_product_id.custom_vehicle_id = record.id

