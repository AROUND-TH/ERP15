from odoo import models, api, _
from odoo.exceptions import ValidationError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.constrains('ecm_no', 'code', 'product_tmpl_id')
    def _validate_ecm(self):
        for rec in self:
            if rec.ecm_no != rec.code:
                raise ValidationError(_('ECM No and Reference must be the same.'))
            bom_id = self.search([
                ('id', '!=', rec.id),
                ('product_tmpl_id', '=', rec.product_tmpl_id.id),
                ('ecm_no', '=', rec.ecm_no),
                ('code', '=', rec.code)])
            if bom_id:
                raise ValidationError(_('Product with ECM No already exists.'))
