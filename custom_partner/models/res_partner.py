# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean('Is a Customer')
    is_vendor = fields.Boolean('Is a Vendor')

    internal_code = fields.Char(
        string='Internal Code',
        copy=False,
    )
    fax = fields.Char('Fax')

    vendor_group_id = fields.Many2one('vendor.group', 
        string='Vendor Group', 
    )

    generate_number = fields.Char(
        string='Generate No.', 
        copy=False,
    )


    @api.model_create_multi
    def create(self, vals_list):
        partners = super(ResPartner, self).create(vals_list)
        for partner in partners:
            if partner.vendor_group_id:
                partner.generate_number = partner.vendor_group_id._get_sequence_next()
                if not partner.internal_code:
                    partner.internal_code = partner.generate_number
        return partners


    def write(self, vals):
        change_sequence = False
        if vals.get('vendor_group_id') and not vals.get('internal_code'):
            change_sequence = True

        result = super(ResPartner, self).write(vals)
        if change_sequence:
            sequence = self.vendor_group_id._get_sequence_next()
            if sequence:
                self.update(
                    {
                        "generate_number": sequence,
                        "internal_code": sequence,
                    }
                )
        elif not self.internal_code and self.vendor_group_id:
            if not self.generate_number:
                sequence = self.vendor_group_id._get_sequence_next()
                if sequence:
                    self.update(
                        {
                            "generate_number": sequence,
                            "internal_code": sequence,
                        }
                    )
            else:
                self.update({"internal_code": self.generate_number})

        return result

