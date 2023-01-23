# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @tools.ormcache()
    def _get_default_category_id(self):
        # Deletion forbidden (at least through unlink)
        return self.env.ref('product.product_category_all')


    # @Override field default_code to set tracking
    default_code = fields.Char('Internal Reference', 
        compute='_compute_default_code',
        inverse='_set_default_code',
        tracking=True,
        store=True
    )

    # @Override field categ_id to set tracking
    categ_id = fields.Many2one(
        'product.category', 'Product Category',
        change_default=True, default=_get_default_category_id,
        group_expand='_read_group_categ_id',
        required=True,
        tracking=True,
        help="Select category for the current product"
    )

    generate_number = fields.Char(
        string='Generate No.', 
        copy=False,
    )

    # _sql_constraints = [
    #     (
    #         "default_code_unique",
    #         "unique(default_code)",
    #         _("This 'Internal Reference' are already exist !")
    #     )
    # ]

    @api.constrains('default_code')
    def _check_code(self):
        for template in self:
            if template.default_code:
                values = self.env['product.template'].search([('default_code', '=', template.default_code)])
                for data in values:
                    if data.id != template.id:
                        raise ValidationError(_("This 'Internal Reference' are already exist !"))


    # @Override odoo core method create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('categ_id') and not vals.get('default_code'):
                categ_id = self.env['product.category'].browse(vals.get('categ_id'))
                sequence = categ_id._get_sequence_next()
                if sequence:
                    vals.update(
                        {
                            "generate_number": sequence,
                            "default_code": sequence,
                        }
                    )

        templates = super(ProductTemplate, self).create(vals_list)

        # # This is needed to set given values to first variant after creation
        # for template, vals in zip(templates, vals_list):
        #     related_vals = {}
        #     if vals.get('external_code'):
        #         related_vals['external_code'] = vals['external_code']
        #     if related_vals:
        #         template.write(related_vals)

        return templates

    # @Override odoo core method write
    def write(self, vals):
        change_sequence = False
        if vals.get('categ_id'):
            vals['generate_number'] = False
            if not vals.get('default_code'):
                change_sequence = True

        result = super(ProductTemplate, self).write(vals)
        if change_sequence:
            sequence = self.categ_id._get_sequence_next()
            if sequence:
                self.update(
                    {
                        "generate_number": sequence,
                        "default_code": sequence,
                    }
                )
        elif not self.default_code and self.categ_id:
            if not self.generate_number:
                sequence = self.categ_id._get_sequence_next()
                if sequence:
                    self.update(
                        {
                            "generate_number": sequence,
                            "default_code": sequence,
                        }
                    )
            else:
                self.update({"default_code": self.generate_number})

        return result

