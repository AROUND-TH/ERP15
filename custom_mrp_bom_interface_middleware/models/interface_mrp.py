import requests
import logging

from odoo import models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MrpBom(models.AbstractModel):
    _name = 'middleware.mrp'

    def get_middleware_url(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        return ir_config.get_param('middleware_api_uri')

    def get_middleware_token(self):
        ir_config = self.env['ir.config_parameter'].sudo()
        middleware_uri = self.get_middleware_url()
        middleware_username = ir_config.get_param('middleware_api_username')
        middleware_password = ir_config.get_param('middleware_api_password')
        try:
            auth_url = middleware_uri + "/api/TokenAuth/Authenticate"
            data = {
                "UserNameOrEmailAddress": middleware_username,
                "Password": middleware_password
            }
            res = requests.post(auth_url, json=data)
            auth_response = res.json()
            if auth_response.get("error"):
                raise ValueError("MiddleWare Authenticate error.")
            return auth_response.get("result", {}).get("accessToken")
        except Exception as e:
            _logger.error('Authenticate MiddleWare API connection error: %s', e)
            raise ValidationError("Authenticate MiddleWare Error. Please contact your administrator.")

    def bom_headers_get_all(self, query=None, access_token=None):
        middleware_uri = self.get_middleware_url()
        if not access_token:
            access_token = self.get_middleware_token()
        url = f"{middleware_uri}/api/services/app/BomHeaders/GetAll"
        if query:
            url += f"?{query}"
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json',
        }
        try:
            response = requests.get(url, headers=headers)
            response = response.json()
            if response.get("error"):
                raise ValidationError("MiddleWare BomHeaders/GetAll error.")
            return response
        except Exception as e:
            _logger.error('BomHeaders/GetAll API connection error: %s', e)
            raise ValidationError("MiddleWare Error. Please contact your administrator.")

    def bom_headers_create_or_edit(self, payload, access_token=None):
        middleware_uri = self.get_middleware_url()
        if not access_token:
            access_token = self.get_middleware_token()
        url = f"{middleware_uri}/api/services/app/BomHeaders/CreateOrEdit"
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json',
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response = response.json()
            if response.get("error"):
                raise ValidationError("MiddleWare BomHeaders/CreateOrEdit error.")
            return response
        except Exception as e:
            _logger.error('BomHeaders/CreateOrEdit API connection error: %s', e)
            raise ValidationError("MiddleWare Error. Please contact your administrator.")

    def bom_items_get_all(self, query=None, access_token=None):
        middleware_uri = self.get_middleware_url()
        if not access_token:
            access_token = self.get_middleware_token()
        url = f"{middleware_uri}/api/services/app/BomItems/GetAll"
        if query:
            url += f"?{query}"
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json',
        }
        try:
            response = requests.get(url, headers=headers)
            response = response.json()
            if response.get("error"):
                raise ValidationError("MiddleWare BomItems/GetAll error.")
            return response
        except Exception as e:
            _logger.error('BomItems/GetAll API connection error: %s', e)
            raise ValidationError("MiddleWare Error. Please contact your administrator.")

    def bom_items_create_or_edit(self, payload, access_token=None):
        middleware_uri = self.get_middleware_url()
        if not access_token:
            access_token = self.get_middleware_token()
        url = f"{middleware_uri}/api/services/app/BomItems/CreateOrEdit"
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'Content-Type': 'application/json',
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response = response.json()
            if response.get("error"):
                raise ValidationError("MiddleWare BomItems/CreateOrEdit error.")
            return response
        except Exception as e:
            _logger.error('BomItems/CreateOrEdit API connection error: %s', e)
            raise ValidationError("MiddleWare Error. Please contact your administrator.")
