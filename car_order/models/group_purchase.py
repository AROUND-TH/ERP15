from odoo import models


class FilterGroupPurchase(models.AbstractModel):
    _name = 'filter.vendor_group.abstract'
    _description = "filter.vendor_group.abstract"

    def _get_domain_filter_group_purchase(self, domain, field):
        ir_config = self.env['ir.config_parameter'].sudo()
        vendor_group_id = ir_config.get_param('car_order_vendor_group_car')
        purchase_general = self.env.user.has_group('car_order.purchase_general')
        purchase_car = self.env.user.has_group('car_order.purchase_car')
        if purchase_general != purchase_car:
            _domain = [field, '=', int(vendor_group_id)] if purchase_car else [
                field, 'not in', [int(vendor_group_id), False]]
            domain.insert(0, _domain)
        return domain
