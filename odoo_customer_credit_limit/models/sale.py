# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     for rec in self:
    #         # rec.credit_limit = rec.partner_id.credit_limit
    #         rec.credit = rec.partner_id.credit
    #     return super(Sale, self).onchange_partner_id()
        
    
    is_website_order = fields.Boolean(
        string='Is Website Order',
        copy=False,
    )
    is_skip_credit_limit = fields.Boolean(
        string='Skip Credit Limit Validation',
        copy=True,
    )

    is_credit_manager = fields.Boolean(
        string='Credit Manager',
        compute='_compute_credit_manager'
    )

    @api.model
    def create(self, vals):
        if self._context.get('website_id'):
            vals.update({'is_website_order':True,})
        return super(SaleOrder, self).create(vals)

    def _compute_credit_manager(self):
        if self.user_has_groups('odoo_customer_credit_limit.group_sale_credit_control'):
            self.is_credit_manager = True
        else:
            self.is_credit_manager = False

    def action_confirm(self):
        if not self.is_website_order:
            if not self.is_skip_credit_limit:
                self._partner_credit_limit()
        
        return super(SaleOrder, self).action_confirm()
    
    def _partner_credit_limit(self):
        for order in self:
            if order.partner_id.credit_rule_id:

                language_id = self.env['res.lang']._lang_get(self.env.user.lang)
                message_obj = self.env['credit.message.error']

                if order.partner_id.credit_rule_id.credit_type == 'customer':
                    message_id = message_obj.search([('error_type', '=', 'customer')])
                    if not message_id:
                        raise ValidationError(_('Please setup the message on menu "Configuration > Set Message Error"'))

                    message_error = message_id.message_th if language_id.iso_code == 'th' else message_id.message_en
                    if order.partner_id.credit_limit <= order.partner_id.credit:
                        raise ValidationError(_(message_error))
                    elif order.partner_id.credit == 0.0 and order.partner_id.credit_limit <= order.amount_untaxed:
                        raise ValidationError(_(message_error))
                    elif order.partner_id.credit_limit <= order.partner_id.credit + order.amount_untaxed:
                        raise ValidationError(_(message_error))
                else:
                    message_id = message_obj.search([('error_type', '=', 'days')])
                    if not message_id:
                        raise ValidationError(_('Please setup the message on menu "Configuration > Set Message Error"'))

                    message_error = message_id.message_th if language_id.iso_code == 'th' else message_id.message_en
                    days = order.partner_id.credit_rule_id.credit_days
                    domain = [
                        ('account_id.user_type_id.type', 'in', ['receivable','payable']),
                        ('reconciled', '=', False),
                        ('display_type', 'not in', ['line_section', 'line_note']),
                        ('parent_state', '!=', 'cancel'),
                        ('company_id', '=', self.company_id.id),
                        ('partner_id', 'in', order.partner_id.commercial_partner_id.ids),
                    ]

                    move_line_ids = self.env['account.move.line'].search(domain)
                    today = datetime.date.today()
                    amount_residual = 0
                    for line in move_line_ids:

                        diff = today - line.date
                        if diff.days > days:
                            print('IF')
                            raise ValidationError(_(message_error))
                    
                    # current_date = fields.Date.today()
                    # first_date = datetime.datetime.strptime(str(current_date), "%Y-%m-%d") + timedelta(days)
                    tables, where_clause, where_params = self.env['account.move.line']._query_get()
                    # where_params = [tuple(rec.partner_id.ids)] + [first_date] + where_params
                    where_params = [tuple(order.partner_id.commercial_partner_id.ids)] + where_params
                    if where_clause:
                        where_clause = 'AND ' + where_clause
                        
                    self._cr.execute("""SELECT account_move_line.partner_id, act.type, SUM(account_move_line.amount_residual)
                                      FROM """ + tables + """
                                      LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
                                      LEFT JOIN account_account_type act ON (a.user_type_id=act.id)
                                      WHERE act.type IN ('receivable','payable')
                                      AND account_move_line.partner_id IN %s
                                      AND account_move_line.reconciled IS FALSE
                                      """ + where_clause + """
                                      GROUP BY account_move_line.partner_id, act.type
                                      """, where_params)
                                      
                    move_line = self._cr.fetchall()
                    credit = 0.0
                    for pid, type, val in move_line:
                        partner = self.browse(pid)
                        if type == 'receivable':
                            credit = val

                    line_lst=[]
                    compute_credit_amt_limit = 0.0
                    credit_amt_limit = 0.0
                    if not (order.partner_id.credit_rule_id.categ_ids and order.partner_id.credit_rule_id.product_tmpl_ids):
                            credit_amt_limit += sum(line.price_subtotal for line in order.order_line)
                    else:
                        for line in order.order_line:
                            if order.partner_id.credit_rule_id.categ_ids:
                                if line.product_id.categ_id in order.partner_id.credit_rule_id.categ_ids:
                                    if line not in line_lst:
                                        line_lst.append(line)
                                        
                            if order.partner_id.credit_rule_id.product_tmpl_ids:
                                if line.product_id.product_tmpl_id in order.partner_id.credit_rule_id.product_tmpl_ids:
                                    if line not in line_lst:
                                        line_lst.append(line)
                    
                        credit_amt_limit += sum(line.price_subtotal for line in line_lst)

                    if order.partner_id.credit_rule_id.currency_id != order.pricelist_id.currency_id:
                        #compute_credit_amt_limit +=  rec.partner_id.credit_rule_id.currency_id.compute(credit_amt_limit, rec.pricelist_id.currency_id)
                        compute_credit_amt_limit +=  order.partner_id.credit_rule_id.currency_id._convert(credit_amt_limit, order.pricelist_id.currency_id, order.company_id, order.date_order)

                    else:
                        compute_credit_amt_limit += credit_amt_limit

                    compute_credit_amt_limit += credit
                    if order.partner_id.credit_limit <= compute_credit_amt_limit:
                        message_id = message_obj.search([('error_type', '=', 'customer')])
                        if not message_id:
                            raise ValidationError(_('Please setup the message on menu "Configuration > Set Message Error"'))
                            
                        message_error = message_id.message_th if language_id.iso_code == 'th' else message_id.message_en
                        raise UserError(_(message_error))

        # return True
        
    # @api.multi
