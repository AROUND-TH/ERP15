# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VendorGroup(models.Model):
    _name = "vendor.group"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Vendor Group"
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

    vendor_code = fields.Char(
        string='Vendor Code', 
        tracking=True,
        # required=True,
    )

    running_prefix = fields.Char(
        string="Vendor (BP Group)", 
        related='vendor_code',
        store=True,
        readonly=False,
    )
    running_digit = fields.Integer(
        string="Running No.",
        default=8,
    )

    # @api.constrains('running_prefix', 'running_digit')
    # def _check_running_sequence(self):
    #     for rec in self:
    #         if rec.running_digit > 0 and not rec.running_prefix:
    #             raise ValidationError(_("Vendor (BP Group) cannot be empty, If Running No was set."))
    #         elif rec.running_prefix and rec.running_digit <= 0:
    #             raise ValidationError(_("Running No must greater than 0, If Vendor (BP Group) was set."))


    @api.onchange('running_prefix')
    def _onchange_running_prefix(self):
        if self.running_prefix:
            self.running_prefix = self.running_prefix.upper()
            if self.running_digit <= 0:
                self.running_digit = 8
        else:
            self.running_digit = 0


    @api.model
    def _get_sequence_next(self):
        if self.running_prefix and (self.running_digit > 0):
            code = f"res.partner.vendor.{self.running_prefix}"
            sequence_next = self.env['ir.sequence'].sudo().next_by_code(code)

            if not sequence_next:
                sequence = self.env['ir.sequence'].sudo().create({
                    'company_id': self.env.company.id,
                    'name': f'Vendor (BP Group) {self.running_prefix}',
                    'code': code,
                    'prefix': self.running_prefix,
                    'padding': self.running_digit,
                })
                sequence_next = sequence.sudo().next_by_code(code)

            return sequence_next
        else:
            return False

    def write(self, vals):
        change_sequence = False
        if vals.get('running_prefix') or vals.get('running_digit'):
            change_sequence = True

        result = super(VendorGroup, self).write(vals)
        if change_sequence:
            for rec in self:
                if rec.running_prefix and rec.running_digit > 0:
                    # update running_digit in VendorGroup Model
                    models = self.env['vendor.group'].search([
                            ('running_prefix', '=', rec.running_prefix),
                            ('running_digit', '!=', rec.running_digit),
                        ])
                    if models:
                        models.update({"running_digit": rec.running_digit})

                    # update padding in Sequence
                    code = f"res.partner.vendor.{rec.running_prefix}"
                    sequence = self.env['ir.sequence'].sudo().search([
                            ('code', '=', code),
                            ('padding', '!=', rec.running_digit),
                        ])
                    if sequence:
                        sequence.update({"padding": rec.running_digit})
        return result

