# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    custom_vehicle_id = fields.Many2one(
    	'fleet.vehicle', 
    	string="Vehicle", 
    )
    custom_model_id = fields.Many2one(
    	'fleet.vehicle.model', 
    	string='Model',
    )
    custom_license_plate = fields.Char(
        string='License Plate',
    )
    custom_fleet_ok = fields.Boolean(
    	string="Is Fleet"
    )

    #@api.multi
    def action_view_fleet(self):
        self.ensure_one()
        action = self.env.ref('fleet.fleet_vehicle_action').read()[0]
        action['domain'] = str([('custom_product_id', 'in', self.ids)])
        return action
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
