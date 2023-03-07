# -*- coding: utf-8 -*-

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp

class MaterialPurchaseRequisitionLine(models.Model):
    _name = "material.purchase.requisition.line"
    _description = 'Material Purchase Requisition Lines'

    
    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisitions', 
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
#     layout_category_id = fields.Many2one(
#         'sale.layout_category',
#         string='Section',
#     )
    description = fields.Char(
        string='Description',
        required=True,
    )
    qty = fields.Float(
        string='Quantity',
        default=1,
        required=True,
    )
    uom = fields.Many2one(
        'uom.uom',#product.uom in odoo11
        string='Unit of Measure',
        required=True,
    )
    partner_id = fields.Many2many(
        'res.partner',
        string='Vendors',
    )
    requisition_type = fields.Selection(
        selection=[
                    ('internal','Internal Picking'),
                    ('purchase','Purchase Order'),
        ],
        string='Requisition Action',
        default='purchase',
        required=True,
    )
    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.name
            rec.uom = rec.product_id.uom_id.id

    @api.onchange('requisition_type')
    def _onchange_requisition_type(self):
        if self.requisition_type == "purchase":
            id_partner = self.env['ir.config_parameter'].sudo().get_param('default_requisitions_vendor')
            self.partner_id = [(4, int(id_partner))]
        else:
            self.partner_id = False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
