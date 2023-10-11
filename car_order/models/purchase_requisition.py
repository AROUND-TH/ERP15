from odoo import models, fields


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    def get_domain_vendor(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        vendor_group_id = ir_config.get_param('car_order_vendor_group_car')
        return ['|', ('company_id', '=', False), ('company_id', '=', self.env.user.company_id.id),
                ('vendor_group_id', '!=', int(vendor_group_id))]

    vendor_id = fields.Many2one('res.partner', domain=get_domain_vendor)
