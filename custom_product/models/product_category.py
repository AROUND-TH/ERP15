from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = "product.category"

    material_id = fields.Many2one('product.material', string="Material Category", required=True)
    material_sub1_id = fields.Many2one('product.material.sub1', string="Sub Category1")
    material_sub2_id = fields.Many2one('product.material.sub2', string="Sub Category2")
    running_digit = fields.Integer(string="Running No.", required=True)
    running_prefix = fields.Char(compute="_compute_running_prefix", store=True)

    @api.constrains('running_digit')
    def _validate_running_digit(self):
        for rec in self:
            if rec.running_digit < 1:
                raise ValidationError(_('Running No must be greater than 0.'))

    @api.onchange('material_sub1_id')
    def _onchange_material_sub1_id(self):
        if not self.material_sub1_id:
            self.material_sub2_id = False

    @api.depends('material_id', 'material_sub1_id', 'material_sub2_id')
    def _compute_running_prefix(self):
        for rec in self:
            if not rec.material_id or rec.running_digit <= 0:
                continue
            prefix = rec.material_id.name
            if rec.material_sub1_id:
                prefix += rec.material_sub1_id.name
                if rec.material_sub2_id:
                    prefix += rec.material_sub2_id.name
            rec.running_prefix = prefix

    @api.model
    def _get_sequence(self):
        code = self.running_prefix
        sequence = self.env['ir.sequence'].sudo().next_by_code(code)
        if not sequence:
            sequence_id = self.env['ir.sequence'].sudo().create({
                'company_id': self.env.company.id,
                'name': f'Product Material {code}',
                'code':code,
                'prefix': code,
                'padding': self.running_digit,
            })
            sequence = sequence_id.get(code)
        return sequence

    def write(self, vals):
        if 'running_digit' not in vals:
            return super().write(vals)
        # update padding in sequence
        result = super().write(vals)
        sequence_id = self.env['ir.sequence'].sudo().search([('code', '=', self.running_prefix)])
        if sequence_id:
            sequence_id.padding = self.running_digit
        return result
