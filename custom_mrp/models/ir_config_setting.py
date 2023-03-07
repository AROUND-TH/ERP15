from odoo import models,fields,api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    middleware_api_uri = fields.Char("Middleware URI",config_parameter='middleware_api_uri')
    middleware_api_username = fields.Char("UserName",config_parameter='middleware_api_username')
    middleware_api_password = fields.Char("Password",config_parameter='middleware_api_password')