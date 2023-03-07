# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection([('wait_for_approve','Wait For Approve'),
        ('not_approve','Not Approve'),
        ('draft',"Quotation"),
        ('sent','Quotation Sent'),
        ('sale','Sales Order'),
        ('done','Locked'),
        ('cancel','Cancelled')],readonly=False,copy=False,index=True,track_visibility='onchange',default='draft')

    compare_pricelist_base_id = fields.Many2one(
        'product.pricelist', string='Compare Base Pricelist', 
        related='pricelist_id.compare_pricelist_base_id',
        required=False, 
        readonly=True, 
        # states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        # check_company=True,  # Unrequired company
        # domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", 
        help="If you change base pricelist for compare, only newly added lines will be affected.")


    amount_base = fields.Monetary(string='Base Total', store=True, readonly=True, compute='_amount_all')
    price_list_need_approve = fields.Boolean("Need Approve Price List",default=True)
    approver_id = fields.Many2one('sale.authentication')
    approver_login_user = fields.Many2one('res.users')
    is_approver_id = fields.Boolean(compute="_compute_is_approver_id",default=False)
    login_user_id = fields.Integer(compute="_compute_user_id")
    approver_user_id = fields.Integer(compute="_compute_approver_user_id")
    approver_partner_id = fields.Integer(compute="_compute_approver_partner_id")
    approver_confirm = fields.Boolean(default=False)
    quotation_link = fields.Char("Link",compute="_compute_quotation_link")

    def _compute_quotation_link(self):
        ir_config_env = self.env['ir.config_parameter'].sudo()
        id = self.id
        ir_config_id = ir_config_env.search([('key','=','web.base.url')],limit=1)
        quotation_link = str(ir_config_id.value)+"/web#id="+str(id)+"&model=sale.order&view_mode=form&"
        self.quotation_link = quotation_link


    @api.model
    def create(self,vals):
        sale_authentication_rec = self.env['sale.authentication'].sudo().search([],limit=1)
        sale_order_line_approved_list = []
        if not vals.get('approver_id'):
            vals['approver_id'] = sale_authentication_rec.id
        
        if vals.get('order_line') and len(vals.get('order_line')) > 0:
            for line in vals['order_line']:
                unit_price = line[2]['price_unit']-((line[2]['price_unit']*line[2]['discount'])/100)
                if line[2]['compare_baseprice_unit'] > 0 and line[2]['compare_baseprice_unit'] > unit_price:
                    sale_order_line_approved_list.append(line)
                else:
                    next
            if len(sale_order_line_approved_list) > 0 :
                vals['price_list_need_approve'] = True
                vals['state'] = "wait_for_approve"
            else:
                vals['price_list_need_approve'] = False
                vals['state'] = "draft"
        else:
            next
        res = super(SaleOrder,self).create(vals)
        if vals.get('price_list_need_approve') and vals.get('state') == 'wait_for_approve':
            res.action_send_email_state_wait_for_approve()
        return res

    # @api.onchange('state')
    # def check_state_wait_for_approve_for_send_email(self):
    #     for rec in self:
    #         if rec.state == 'wait_for_approve' and rec.approver_id:
    #             self.action_send_email_state_wait_for_approve()
    
    def action_send_email_state_wait_for_approve(self):
        template_id = self.env.ref('custom_sale_pricelist.email_template_wait_for_approve').id
        template = self.env['mail.template'].browse(template_id)
        quotation_rec = ""
        for rec in self:
            if rec.state == 'wait_for_approve' and rec.approver_id:
                quotation_rec = rec.name
            else:
                quotation_rec = self.name
        # _logger.info(self.name)
        quotation_id = self.env['sale.order'].search([('name','=',quotation_rec)],limit=1)
        template.send_mail(quotation_id.id,force_send=True)

    def action_update_state_draft(self):
        for rec in self:
            if rec.price_list_need_approve and rec.is_approver_id:
                self.state = "draft"
                self.is_approver_id = True
                self.price_list_need_approve = False
                self.approver_confirm = True
            template_id = self.env.ref('custom_sale_pricelist.email_template_approve').id
            template = self.env['mail.template'].browse(template_id)
            template.send_mail(self.id,force_send=True)
    
    def action_update_state_not_approve(self):
        for rec in self:
            if rec.price_list_need_approve and rec.is_approver_id:
                self.state = "not_approve"
                self.is_approver_id = True
                self.price_list_need_approve = True
                self.approver_confirm = True
            template_id = self.env.ref('custom_sale_pricelist.email_template_not_approve').id
            template = self.env['mail.template'].browse(template_id)
            template.send_mail(self.id,force_send=True)


    def action_update_state_wait_for_approve(self):
        self.state = "wait_for_approve"
        self.price_list_need_approve = True
        self.write({
            "state":"wait_for_approve",
            "price_list_need_approve":True,
        })


    @api.depends("approver_id")
    def _compute_is_approver_id(self):
        for rec in self:
            if rec.approver_id:
                hr_employee_rec = self.env['hr.employee'].search([('id','=',rec.approver_id.user_approve_id.id)])
                current_user_id = self.env.user.id
                current_approver_id = hr_employee_rec.user_id.id
                if current_user_id == current_approver_id:
                    self.is_approver_id = True
                else:
                    self.is_approver_id = False
            else:
                self.is_approver_id = False

    @api.depends("approver_id")
    def _compute_user_id(self):
        for rec in self:
            if rec.approver_id:
                self.login_user_id = self.env.user.id
            else:
                self.login_user_id = 0
    
    @api.depends("approver_id")
    def _compute_approver_user_id(self):
        for rec in self:
            if rec.approver_id:
                hr_employee_rec = self.env['hr.employee'].search([('id','=',rec.approver_id.user_approve_id.id)])
                self.approver_user_id = hr_employee_rec.user_id.id
                self.approver_login_user = hr_employee_rec.user_id.id
            else:
                self.approver_user_id = 1

    @api.depends("approver_id")
    def _compute_approver_partner_id(self):
        for rec in self:
            if rec.approver_id:
                hr_employee_rec = self.env['hr.employee'].search([('id','=',rec.approver_id.user_approve_id.id)])
                self.approver_partner_id = hr_employee_rec.user_partner_id.id
            else:
                self.approver_partner_id = 1

    @api.onchange('order_line','pricelist_id')
    def compute_approve_price_list(self):
        sale_order_line_approved_list = []
        price_list_need_approve = False
        state = 'draft'
        for rec in self:
            if len(rec.order_line) == 1: 
                for line in self.order_line:
                    if line.compare_baseprice_unit > 0 and line.compare_baseprice_unit > (line.price_subtotal/line.product_uom_qty):
                        price_list_need_approve = True
                        state = "wait_for_approve"
                    else:
                        price_list_need_approve = False
                        state = "draft"
            elif len(rec.order_line) > 1: 
                for line in rec.order_line:
                    if line.compare_baseprice_unit > 0 and line.compare_baseprice_unit > (line.price_subtotal/line.product_uom_qty):
                        sale_order_line_approved_list.append(line)
                    else:
                        next
                if len(sale_order_line_approved_list) > 0:
                    price_list_need_approve = True
                    state = "wait_for_approve"
                else:
                    price_list_need_approve = False
                    state = "draft"
            self.price_list_need_approve = price_list_need_approve
            self.state = state

    @api.depends('order_line','pricelist_id','approver_confirm')
    def compute_approve_price_list_with_confirm(self):
        sale_order_line_approved_list = []
        for rec in self:
            if not rec.approver_confirm:
                if len(rec.order_line) == 1: 
                    for line in self.order_line:
                        if line.compare_baseprice_unit > 0 and line.compare_baseprice_unit > (line.price_subtotal/line.product_uom_qty):
                            price_list_need_approve = True
                            state = "wait_for_approve"
                        else:
                            price_list_need_approve = False
                            state = "draft"
                elif len(rec.order_line) > 1: 
                    for line in rec.order_line:
                        if line.compare_baseprice_unit > 0 and line.compare_baseprice_unit > (line.price_subtotal/line.product_uom_qty):
                            sale_order_line_approved_list.append(line)
                        else:
                            next
                    if len(sale_order_line_approved_list) > 0:
                        price_list_need_approve = True
                        state = "wait_for_approve"
                    else:
                        price_list_need_approve = False
                        state = "draft"
                else:
                    return
                self.price_list_need_approve = price_list_need_approve
                self.state = state



    # @Override core method update_prices
    def update_prices(self):
        self.ensure_one()
        lines_to_update = []
        for line in self.order_line.filtered(lambda line: not line.display_type):

            product = line.product_id.with_context(
                partner=self.partner_id,
                quantity=line.product_uom_qty,
                date=self.date_order,
                pricelist=self.pricelist_id.id,
                uom=line.product_uom.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                line._get_display_price(product), line.product_id.taxes_id, line.tax_id, line.company_id)

            if self.compare_pricelist_base_id:
                # @Add get product with compare_pricelist_base_id
                product_compare_base = line.product_id.with_context(
                    partner=self.partner_id,
                    quantity=line.product_uom_qty,
                    date=self.date_order,
                    pricelist=self.compare_pricelist_base_id.id,
                    uom=line.product_uom.id
                )
                # @Set compare_baseprice_unit data
                compare_baseprice_unit = self.env['account.tax']._fix_tax_included_price_company(
                    line._get_display_compare_baseprice(product_compare_base), line.product_id.taxes_id, line.tax_id, line.company_id)
            else:
                # @Set to compare itself (compare_baseprice_unit = price_unit)
                # compare_baseprice_unit = price_unit
                # @Set compare_baseprice_unit = 0.0
                compare_baseprice_unit = 0.0


            if self.pricelist_id.discount_policy == 'without_discount' and price_unit:
                price_discount_unrounded = self.pricelist_id.get_product_price(product, line.product_uom_qty, self.partner_id, self.date_order, line.product_uom.id)
                discount = max(0, (price_unit - price_discount_unrounded) * 100 / price_unit)
            else:
                discount = 0

            # @Add append compare_baseprice_unit, compare_gpprice_unit
            lines_to_update.append((1, line.id, {'price_unit': price_unit, 'discount': discount, 'compare_baseprice_unit': compare_baseprice_unit}))
        self.update({'order_line': lines_to_update})
        self.show_update_pricelist = False
        self.message_post(body=_("Product prices have been recomputed according to pricelist <b>%s<b> ", self.pricelist_id.display_name))

