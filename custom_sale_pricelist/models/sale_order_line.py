# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang, get_lang
import logging
_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'


    compare_baseprice_unit = fields.Float('Compare Base Unit Price', required=True, digits='Product Price', default=0.0)

    price_subtotal_nodiscount = fields.Monetary(compute='_compute_compare_subtotal', string='Subtotal Without Discount', readonly=True, store=True)

    baseprice_subtotal = fields.Monetary(compute='_compute_compare_subtotal', string='Base Price Subtotal', readonly=True, store=True)


    # @Add _compute_compare_subtotal for compute field gp_subtotal, freight_subtotal
    # @api.depends('product_uom_qty', 'price_unit', 'compare_baseprice_unit', 'compare_gpprice_unit', 'tax_id', 'discount')
    @api.depends('product_uom_qty', 'price_unit', 'compare_baseprice_unit', 'tax_id')
    def _compute_compare_subtotal(self):
        """
        Compute the compare subtotal of the SO line.
        """
        for line in self:
            # @Calculate without discount %
            # price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

            # discount = line.price_unit * ((line.discount or 0.0) / 100.0)
            # taxes_compare = line.tax_id.compute_all(line.compare_price_unit - discount, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)


            taxes_nodiscount = line.tax_id.compute_all(line.price_unit, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            
            # @Check condition compare_baseprice_unit, compare_gpprice_unit 
            # if value <= 0 then set relate data = 0.0
            if (line.compare_baseprice_unit <= 0) :
                line.update({
                    'compare_baseprice_unit': 0.0,
                    'price_subtotal_nodiscount': taxes_nodiscount['total_excluded'],
                    'baseprice_subtotal': 0.0,
                })

            else:
                taxes_baseprice = line.tax_id.compute_all(line.compare_baseprice_unit, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)


                line.update({
                    'price_subtotal_nodiscount': taxes_nodiscount['total_excluded'],
                    'baseprice_subtotal': taxes_baseprice['total_excluded'],
                })
            # _logger.info("####")
            # _logger.info(line.compare_baseprice_unit)


    # @Override core method product_id_change
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        valid_values = self.product_id.product_tmpl_id.valid_product_template_attribute_line_ids.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )
        vals.update(name=self.get_sale_order_line_multiline_description_sale(product))
        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)

            if self.order_id.compare_pricelist_base_id:
                # @Add get product with compare_pricelist_base_id
                product_compare_base = self.product_id.with_context(
                    lang=get_lang(self.env, self.order_id.partner_id.lang).code,
                    partner=self.order_id.partner_id,
                    quantity=vals.get('product_uom_qty') or self.product_uom_qty,
                    date=self.order_id.date_order,
                    pricelist=self.order_id.compare_pricelist_base_id.id,
                    uom=self.product_uom.id
                )
                # @Set compare_baseprice_unit data
                vals['compare_baseprice_unit'] = self.env['account.tax']._fix_tax_included_price_company(self._get_display_compare_baseprice(product_compare_base), product_compare_base.taxes_id, self.tax_id, self.company_id)
            else:
                # @Set to compare itself (compare_baseprice_unit = price_unit)
                # vals['compare_baseprice_unit'] = vals['price_unit']
                # @Set compare_baseprice_unit = 0.0
                vals['compare_baseprice_unit'] = 0.0

        self.update(vals)

        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s", product.name)
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False

        return result


    # @Override core method product_uom_change
    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            # @Set compare_baseprice_unit, compare_gpprice_unit
            self.compare_baseprice_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)

            if self.order_id.compare_pricelist_base_id:
                # @Add get product with compare_pricelist_base_id
                product_compare_base = self.product_id.with_context(
                    lang=self.order_id.partner_id.lang,
                    partner=self.order_id.partner_id,
                    quantity=self.product_uom_qty,
                    date=self.order_id.date_order,
                    pricelist=self.order_id.compare_pricelist_base_id.id,
                    uom=self.product_uom.id,
                    fiscal_position=self.env.context.get('fiscal_position')
                )
                # @Set compare_baseprice_unit data
                self.compare_baseprice_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_compare_baseprice(product_compare_base), product_compare_base.taxes_id, self.tax_id, self.company_id)
            else:
                # @Set to compare itself (compare_baseprice_unit = price_unit)
                # self.compare_baseprice_unit = self.price_unit
                # @Set compare_baseprice_unit = 0.0
                self.compare_baseprice_unit = 0.0


    # @TODO Add new _get_display_compare_baseprice for compare_pricelist_base_id
    def _get_display_compare_baseprice(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        # awa: don't know if it's still the case since we need the "product_no_variant_attribute_value_ids" field now
        # to be able to compute the full price

        # it is possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        no_variant_attributes_price_extra = [
            ptav.price_extra for ptav in self.product_no_variant_attribute_value_ids.filtered(
                lambda ptav:
                    ptav.price_extra and
                    ptav not in product.product_template_attribute_value_ids
            )
        ]
        if no_variant_attributes_price_extra:
            product = product.with_context(
                no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra)
            )

        if self.order_id.compare_pricelist_base_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.order_id.compare_pricelist_base_id.id, uom=self.product_uom.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)

        final_price, rule_id = self.order_id.compare_pricelist_base_id.with_context(product_context).get_product_price_rule(product or self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.order_id.compare_pricelist_base_id.id)
        if currency != self.order_id.compare_pricelist_base_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.compare_pricelist_base_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

