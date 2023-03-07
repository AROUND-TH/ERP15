from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class MRPBom(models.Model):
    _inherit = 'mrp.bom'

    production_type = fields.Selection([
        ("PACKING", "PACKING"),
        ("MIXING", "MIXING"),
        ("EXTRUSION", "EXTRUSION"),
        ("PREMIX", "PREMIX"),
        ("DIGEST", "DIGEST"),
        ("MIXSHAPE", "MIXSHAPE")], string="Production Type", default="MIXING")
    bom_status = fields.Selection([
        ("Active", "Active"),
        ("Inactive", "Inactive")], string="Bom Status", default="Active")
    ecm_no = fields.Char("ECM No.")
    ecm_date = fields.Date("ECM Date")
