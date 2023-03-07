from odoo import models,fields,api
import logging

_logger = logging.getLogger(__name__)

class MRPBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    bom_line_type = fields.Char("Type")