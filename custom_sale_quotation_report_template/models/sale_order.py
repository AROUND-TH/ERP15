from odoo import models,fields,api
import math

class SaleOrder(models.Model):
  _inherit="sale.order"


  def ceil(self,number1,number2):
        return math.ceil(number1/number2)

  def action_print_quotation_th(self):
    return self.env.ref('custom_sale_quotation_report_template.quotation_bluefalo_report_th').report_action(self)

  def action_print_quotation_en(self):
    return self.env.ref('custom_sale_quotation_report_template.quotation_bluefalo_report_en').report_action(self)

  def action_print_quotation_sale_order_thai(self):
    return self.env.ref('custom_sale_quotation_report_template.sale_report_quotation').report_action(self)
  
  def action_quotation_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        template_id = self._find_mail_template()
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if self.partner_id.lang == 'en_US':
          report_template = self.env.ref('custom_sale_quotation_report_template.quotation_bluefalo_report_en')
        elif self.partner_id.lang == 'th_TH':
          report_template = self.env.ref('custom_sale_quotation_report_template.quotation_bluefalo_report_th')
        else:
          report_template = self.env.ref('custom_sale_quotation_report_template.quotation_bluefalo_report_en')
        template.write(
          {
            'report_template':report_template,
          })
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }