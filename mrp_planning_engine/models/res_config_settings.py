# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'


    #FIRMING_TYPE = [
    #    ("0", "Do Not Firm"),
    #    ("1", "Firm in Frozen Period and new proposals out of the Frozen Period"),
    #    ("2", "Firm in Frozen Period and no new proposals in the Frozen Period"),
    #]

    forward_planning = fields.Boolean('Forward Planning')
    #roll_forward_period = fields.Integer('Roll Forward Period', default=0)
    #firming_type = fields.Selection(FIRMING_TYPE, 'Firming Type', default="0", required=True)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"


    forward_planning = fields.Boolean(related="company_id.forward_planning", readonly=False)
    #roll_forward_period = fields.Integer(related="company_id.roll_forward_period", readonly=False)
    #firming_type = fields.Selection(related="company_id.firming_type", readonly=False)
