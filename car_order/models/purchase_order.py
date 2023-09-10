from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def get_domain_partner(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        vendor_group_id = ir_config.get_param('car_order_vendor_group_car')
        domain = ['|', ('company_id', '=', False), ('company_id', '=', self.env.user.company_id.id)]
        if self._context.get('filter_vendor_group'):
            domain.append(('vendor_group_id', '=', int(vendor_group_id)))
        else:
            domain.append(('vendor_group_id', '!=', int(vendor_group_id)))
        return domain

    partner_id = fields.Many2one('res.partner', domain=get_domain_partner)
