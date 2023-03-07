import logging
import requests

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class TruckscaleItem(models.TransientModel):
    _name = 'wizard.truckscale.item'
    _description = "Wizard Truckscale Item"
    _rec_name = 'ts_trans_id'

    picking_id = fields.Many2one('stock.picking', string='Transfer', readonly=True, ondelete="cascade")
    ts_id = fields.Integer(string='Truckscale ID')
    ts_trans_id = fields.Char(string='TransId')
    ts_car_code = fields.Char(string='CarCode')
    ts_car_prov = fields.Char(string='CarProv')
    ts_car_code2 = fields.Char(string='CarCode2')
    ts_car_prov2 = fields.Char(string='CarProv2')
    ts_driver = fields.Char(string='DriverName')
    ts_driver_id = fields.Char(string='DriverIdCard')
    ts_barcode = fields.Char(string='Barcode')
    ts_ingred_code = fields.Char(string='IngredCode')
    ts_vendor_code = fields.Char(string='VendorCode')
    ts_trans_wt = fields.Float(string='TransWeight')
    ts_car_wt = fields.Float(string='CarWeight')
    ts_actual_wt = fields.Float(string='ActualWeight')

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ir_config = self.env['ir.config_parameter'].sudo()
        middleware_uri = ir_config.get_param('middleware_api_uri')
        middleware_username = ir_config.get_param('middleware_api_username')
        middleware_password = ir_config.get_param('middleware_api_password')
        try:
            if self.env.context.get('search_more'):
                limit_result = self.env.context.get('limit_result')
                picking_id = self.env.context.get('picking_id')
                item_ids = self.search([('picking_id', '=', picking_id)])
                item_ids.unlink()
                auth_url = middleware_uri + "/api/TokenAuth/Authenticate"
                data = {
                    "UserNameOrEmailAddress": middleware_username,
                    "Password": middleware_password
                }
                res = requests.post(auth_url, json=data)
                auth_response = res.json()
                if auth_response.get("error"):
                    raise ValueError("MiddleWare Authenticate error.")
                url = middleware_uri + "/api/services/app/Truckscales/GetAll"
                headers = {
                    'Authorization': 'Bearer %s' % auth_response.get("result", {}).get("accessToken")
                }
                res = requests.get(url, headers=headers)
                response = res.json()
                if response.get('error'):
                    raise ValueError("MiddleWare /app/Truckscales/GetAll error.")
                vals = list()
                i = 0
                for item in response.get("result", {}).get("items"):
                    i += 1
                    data = item.get("truckscale", {})
                    vals.append(
                        {
                            'picking_id': picking_id,
                            'ts_id': data.get("id"),
                            'ts_trans_id': data.get("transId"),
                            'ts_car_code': data.get("carCode"),
                            'ts_car_prov': data.get("carProv"),
                            'ts_car_code2': data.get("carCode2"),
                            'ts_car_prov2': data.get("carProv2"),
                            'ts_driver': data.get("driveName"),
                            'ts_driver_id': data.get('driveIdcard'),
                            'ts_barcode': data.get('barcode'),
                            'ts_ingred_code': data.get('ingredCode'),
                            'ts_vendor_code': data.get('vendorCode'),
                            'ts_trans_wt': data.get('transWeight'),
                            'ts_car_wt': data.get('carWeight'),
                            'ts_actual_wt': data.get('actualWeight')
                        }
                    )
                    if limit_result and i >= limit_result:
                        break

                self.env['wizard.truckscale.item'].create(vals)

        except Exception as e:
            _logger.error('Error: Call API for list truckscale data')
            _logger.error('Truckscale API connection error: %s', e)
            raise ValidationError("Truckscale Error. Please contact your administrator.")

        return super().name_search(name, args, operator, limit)
