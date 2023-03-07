# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, timedelta
from odoo.exceptions import UserError, ValidationError

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'


    compare_pricelist_base_id = fields.Many2one(
        'product.pricelist',
        string='Base Pricelist for compare (ราคาประกาศ)',
        copy=False,
    )

    # @TODO validate check 
    # if compare_pricelist_base_id not null: compare_pricelist_gp_id must not null
    # if compare_pricelist_gp_id not null: compare_pricelist_base_id must not null

    @api.constrains('compare_pricelist_base_id', 'item_ids')
    def _validate_data(self):
        message = ''
        message_template = ''
        isError = False
        isLogger = False
        for line in self:

            item_obj = {}
            for item in line.item_ids:
                message_template += 'รายการสินค้า "%s %s" \n' %(item.product_tmpl_id.default_code, item.product_tmpl_id.name)

                if item.date_start and item.date_end:
                    key = str(item.product_tmpl_id.id) + str(item.date_start.date()) + str(item.date_end.date())
                
                    if key in item_obj:
                        isError = True
                        isLogger = True
                        message_template += ' - วันที่ Start Date กับ End Date ห้ามซ้ำกัน \n'
                    else:
                        item_obj[key] = {
                            'date_start': item.date_start,
                            'date_end': item.date_end,
                        }

                    if item.date_end < item.date_start:
                        isError = True
                        isLogger = True
                        message_template += ' - วันที่ End Date ห้ามน้อยกว่า Start Date \n'

                if item.compute_price == 'fixed' and item.fixed_price == 0:
                    isError = True
                    isLogger = True
                    message_template += ' - ราคาขายต้องใส่มากกว่า 0 บาท \n'

                if message_template and isLogger:
                    message += '%s\n' %(message_template)
                    message_template = ''
                    isLogger = False
                else:
                    message_template = ''

            if message and isError:
                raise UserError(_(message))

class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.onchange('date_start', 'date_end')
    def _change_start_date_end_date(self):
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise UserError(_("You can't use end date date less than start date."))