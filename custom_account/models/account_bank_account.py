# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountBankAccount(models.Model):
    _name = 'account.bank.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Bank Account"
    _order = 'sequence asc, id asc'


    sequence = fields.Integer(
        string='Sequence',
    )
    name = fields.Char(
        string='Name', 
        tracking=True,
        required=True,
    )
    active = fields.Boolean(
        string='Active', 
        default=True
    )

    bank_name = fields.Char(
        string='Bank Name', 
        tracking=True,
    )
    bank_account = fields.Char(
        string='Account Number', 
        tracking=True,
    )

    account_code = fields.Many2one('account.account', 
        string='Account Code',
        tracking=True,
        ondelete='set null',
    )
    suspense_account_code = fields.Many2one('account.account', 
        string='Suspense Account',
        tracking=True,
        ondelete='set null',
    )

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', _("This 'Name' are already exist !")),
        ('key_unique', 'UNIQUE(bank_name, bank_account)', _("This 'Bank Name' and 'Account Number' are already exist !")),
    ]


    def copy(self, default={}):
        copied_count = self.search_count(
            [('name', '=like', _("Copy of {}%").format(self.name))])
        if not copied_count:
            new_name = _("Copy of {}").format(self.name)
        else:
            new_name = _("Copy of {} ({})").format(self.name, copied_count)
        default['name'] = new_name

        if self.bank_name:
            copied_count = self.search_count(
                [('bank_name', '=like', _("Copy of {}%").format(self.bank_name))])
            if not copied_count:
                new_bank_name = _("Copy of {}").format(self.bank_name)
            else:
                new_bank_name = _("Copy of {} ({})").format(self.bank_name, copied_count)
            default['bank_name'] = new_bank_name

        default['bank_account'] = False
        return super(AccountBankAccount, self).copy(default)

