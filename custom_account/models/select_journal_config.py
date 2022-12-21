# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SelectJournalConfig(models.Model):
    _name = "select.journal.config"
    _description = "Select Journal Config"
    _order = "form_select, set_default desc, journal_id"


    name = fields.Char('Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))

    form_select = fields.Selection(
        selection=[
            ('receipt_billing_customer', 'Receipt Customer Bill'),
            ('pay_billing_vendor', 'Pay Vendor Bill'),
            ('withholding_tax_cert', 'Withholding Tax Certificate'),
        ], 
        string='Use with Form',
        index=True,
        required=True,
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        index=True,
        required=True,
    )

    set_default = fields.Boolean(
        string='Default',
        default=False
    )

    _sql_constraints = [
        ('key_unique', 'UNIQUE(form_select, journal_id)', _("This 'Use with Form' and 'Journal' are already exist !")),
    ]

    @api.constrains('form_select', 'set_default')
    def _check_set_default(self):
        for rec in self:
            if rec.set_default:
                count = self.search_count(
                    [('form_select', '=', rec.form_select), ('set_default', '=', True)])
                if count > 1:
                    form_select = dict(self._fields['form_select'].selection).get(rec.form_select)
                    raise ValidationError(_("This '{}' config already set default. (Can only has one default per 'Use with Form')").format(form_select))


    @api.model
    def create(self, values):
        if values.get('name', _('New')) == _('New'):
            form_select = dict(self._fields['form_select'].selection).get(values['form_select'])
            journal_id = self.env['account.journal'].browse(values['journal_id'])
            values['name'] = str(form_select) + ' - ' + str(journal_id.name)

        return super(SelectJournalConfig, self).create(values)

    def write(self, values):
        if values.get('form_select') or values.get('journal_id'):
            form_select = dict(self._fields['form_select'].selection).get(values.get('form_select', self.form_select))
            journal_id = self.env['account.journal'].browse(values.get('journal_id', self.journal_id.id))
            values['name'] = str(form_select) + ' - ' + str(journal_id.name)

        return super(SelectJournalConfig, self).write(values)

