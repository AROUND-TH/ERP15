# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = "product.category"

    material_id = fields.Many2one('product.material', string="Material Category", required=True)

    running_prefix = fields.Char(
        string="Product (Material Category)", 
        compute="_compute_running_prefix",
        store=True,
        readonly=False,
    )
    running_digit = fields.Integer(
        string="Running No.",
        default=4,
    )

    @api.constrains('running_digit')
    def _validate_running_digit(self):
        for rec in self:
            if rec.running_digit <= 0:
                raise ValidationError(_("Running No must be greater than 0."))

    @api.depends('material_id')
    def _compute_running_prefix(self):
        for rec in self:
            if not rec.material_id or rec.running_digit <= 0:
                rec.running_prefix = False
            else:
                prefix = rec.material_id.name.upper()
                prefix += "%(y)s"
                rec.running_prefix = prefix


    @api.onchange('running_prefix')
    def _onchange_running_prefix(self):
        if self.running_prefix:
            if self.running_digit <= 0:
                self.running_digit = 4
        else:
            self.running_digit = 0


    @api.model
    def _get_sequence_next(self):
        if self.running_prefix and (self.running_digit > 0):
            code = f"product.{self.running_prefix}"
            sequence_next = self.env['ir.sequence'].sudo().next_by_code(code)

            if not sequence_next:
                sequence = self.env['ir.sequence'].sudo().create({
                    'company_id': self.env.company.id,
                    'name': f'Product (Material Category) {self.running_prefix}',
                    'code': code,
                    'prefix': self.running_prefix,
                    'padding': self.running_digit,
                    'use_date_range': True,
                    'range_reset': 'yearly',
                })
                sequence_next = sequence.sudo().next_by_code(code)

            return sequence_next
        else:
            return False

    def write(self, vals):
        change_sequence = False
        if vals.get('running_prefix') or vals.get('running_digit'):
            change_sequence = True

        result = super(ProductCategory, self).write(vals)
        if change_sequence:
            for rec in self:
                if rec.running_prefix and rec.running_digit > 0:
                    # update running_digit in ProductCategory Model
                    models = self.env['product.category'].search([
                            ('running_prefix', '=', rec.running_prefix),
                            ('running_digit', '!=', rec.running_digit),
                        ])
                    if models:
                        models.update({"running_digit": rec.running_digit})

                    # update padding in Sequence
                    code = f"product.{rec.running_prefix}"
                    sequence = self.env['ir.sequence'].sudo().search([
                            ('code', '=', code),
                            ('padding', '!=', rec.running_digit),
                        ])
                    if sequence:
                        sequence.update({"padding": rec.running_digit})
        return result

