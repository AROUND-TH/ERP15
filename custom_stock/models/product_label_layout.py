from odoo import models,fields

class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    print_format = fields.Selection([
        ('dymo', 'Dymo'),
        ('2x7xprice', '2 x 7'),
        ('4x7xprice', '4 x 7'),
        ('4x12', '4 x 12'),
        ('4x12xprice', '4 x 12 (2)')], string="Format", default='2x7xprice', required=True)