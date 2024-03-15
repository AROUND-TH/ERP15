from odoo import models, fields, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    short_name = fields.Char(
        string='Short Name',
        required=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "short_name_unique",
            "unique(short_name)",
            _("Short name are already exist !")
        )
    ]
