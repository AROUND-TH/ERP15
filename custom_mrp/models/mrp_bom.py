# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def name_get(self):
        return [(bom.id, '%s%s' % (bom.code and '%s: ' % bom.code or '', bom.product_tmpl_id.display_name)) for bom in self]


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    convertion_quantity = fields.Float('Convertion Quantity')

    def name_get(self):
        return [(line.id, '%s%s' % (line.bom_id.code and '%s: ' % line.bom_id.code or '', line.product_tmpl_id.display_name)) for line in self]


