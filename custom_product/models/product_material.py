from odoo import api, fields, models, _


class ProductMaterial(models.Model):
    _name = "product.material"
    _order = "name"
    _description = "Product Material"

    name = fields.Char(required=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', _("This 'Name' are already exist !"))
    ]


class ProductMaterialSub1(models.Model):
    _name = "product.material.sub1"
    _order = "name"
    _description = "Product Material Sub Category 1"

    name = fields.Char(required=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', _("This 'Name' are already exist !"))
    ]


class ProductMaterialSub2(models.Model):
    _name = "product.material.sub2"
    _order = "name"
    _description = "Product Material Sub Category 2"

    name = fields.Char(required=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', _("This 'Name' are already exist !"))
    ]
