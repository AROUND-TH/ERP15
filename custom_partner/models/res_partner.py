from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    street3 = fields.Char()
    incoterm_id = fields.Many2one('account.incoterms', 'Incoterm')
    transportation = fields.Char(string="Transportation")
    port_of_loading = fields.Char(string="Port of Loading")
    port_of_destination = fields.Char(string="Port of Destination")
    shipping_note = fields.Char(string="Shipping Note")
    is_customer = fields.Boolean('Is a Customer')
    is_vender = fields.Boolean('Is a Vender')

    @api.model
    def _address_fields(self):
        address_fields = super()._address_fields()
        return address_fields + ['street3']

    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(street3)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"

    @api.model
    def _get_address_format(self):
        # just for odoo.sh rebuild       
        return self._get_default_address_format()
