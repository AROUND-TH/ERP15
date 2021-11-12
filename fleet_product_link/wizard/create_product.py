 # -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt. Ltd. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _

class CreateProduct(models.TransientModel):
    _name = "create.product"
    _description = 'Create Product'

    custom_categ_id = fields.Many2one(
        'product.category', 
        string='Product Category',
        required=True,
    )
    custom_uom_id = fields.Many2one(
        'uom.uom', 
        string='Unit of Measure',
        required=True
    )
    custom_uom_po_id = fields.Many2one(
        'uom.uom', 
        'Purchase Unit of Measure',
        required=True
    )
    name = fields.Char(
        string="Product Name",
        required=True
    )
    newc_custom_type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')], 
        string='Product Type', 
        default='consu', 
        required=True,
        copy=False,
    )

    #@api.multi
    def action_create_product(self):
        active_ids = self._context.get('active_ids')
        fleet_id = self.env['fleet.vehicle'].browse(self._context.get('active_ids'))
        vals = {
            'name':self.name,
            'categ_id':self.custom_categ_id.id,
            'uom_id':self.custom_uom_id.id,
            'uom_po_id':self.custom_uom_po_id.id,
            'type':'service',
            'custom_vehicle_id':fleet_id.id,
            #'image_medium':fleet_id.image_medium,
            'image_1920':fleet_id.image_128,
            'custom_model_id':fleet_id.model_id.id,
            'custom_license_plate':fleet_id.license_plate,
            'company_id':fleet_id.company_id.id,
            'default_code':fleet_id.license_plate,
            'type':self.newc_custom_type,
            'custom_fleet_ok':True
        }
        templete = self.env['product.template'].create(vals)
        fleet_id.write({'custom_product_id':templete.id})
        action = self.env.ref('fleet_product_link.action_product_link_all_fleet').read()[0]
        action['domain'] = str([('id', '=',templete.id )])
        return action

    @api.onchange('custom_uom_id')
    def _onchange_uom_po_id(self):
        for rec in self:
            rec.custom_uom_po_id = rec.custom_uom_id
