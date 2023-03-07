from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Cost calculation fields
    update_standard_price = fields.Boolean(
        string='Cost Updated',
        help="""Is set if standard_price (Cost) was update by Manufacturing process 
        and will not re-write by Compute Price from BoM.""")
    basic_cost = fields.Float(
        string='Basic Cost',
        company_dependent=True,
        digits='Product Price',
        groups="base.group_user",
        help="Basic Cost for use as base calculate in Manufacturing Orders.")

    _sql_constraints = [
        (
            "default_code_uniq",
            "unique(default_code)",
            "The Internal Reference already exists.",
        )
    ]

    gross_weight = fields.Float(string='Gross Weight', digits='Stock Weight')

