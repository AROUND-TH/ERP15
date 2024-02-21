# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProductMaterial(models.Model):
    _name = "product.material"
    _order = "name"
    _description = "Product Material"

    name = fields.Char(required=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', _("This 'Name' are already exist !"))
    ]

