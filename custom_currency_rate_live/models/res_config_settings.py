# -*- coding: utf-8 -*-

import datetime
from lxml import etree
from dateutil.relativedelta import relativedelta
import logging
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


DATE_FORMAT = '%Y-%m-%d' #YYYY-MM-DD
COOKIE = 'incap_ses_1460_1778672=8Hf+S9t7Gk4UTQsShfZCFIKRj2IAAAAAKB8PSJEFF72HXpTnuNgaCA==; visid_incap_1778672=UBCfcWXcQASWe98tPG0RRoGRj2IAAAAAQUIPAAAAAACAmIWzg5wpj+75J336IPK8'

class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(
        selection_add=[('bot', 'Bank of Thailand (BOT)')],
        default='ecb', string='Service Provider')

    client_id = fields.Char(string='Client ID')
    
    def _parse_bot_data(self, available_currencies):

        if not self.client_id:
            raise UserError(_("Your Client-Id is incorrect or is not available, Please check your Client-Id."))

        if self.currency_id.name != 'THB':
            raise UserError(_("Please setup currency default 'THB'"))

        available_currency_names = available_currencies.mapped('name')
        date_now = datetime.datetime.now()
        today = date_now.strftime(DATE_FORMAT)
        rates_dict = {}

        for currency_code in available_currency_names:

            if currency_code not in ['THB', 'USD']:
                result = self.get_daily_avg_exg_rate(today, today, currency_code)
                mid_rate, last_updated = self._get_latest_rate(result)

                if mid_rate:
                    rates_dict[currency_code] = (float(mid_rate), fields.Date.today())
                else:
                    result = self.get_daily_avg_exg_rate(last_updated, last_updated, currency_code)
                    mid_rate, last_updated = self._get_latest_rate(result)

                    rates_dict[currency_code] = (float(mid_rate), last_updated)

            elif currency_code == 'USD':
                result = self.get_daily_avg_exg_rate(today, today, currency_code)
                mid_rate, last_updated = self._get_latest_rate(result)

                if mid_rate:
                    rates_dict[currency_code] = ((1/float(mid_rate)), fields.Date.today())
                else:
                    result = self.get_daily_avg_exg_rate(last_updated, last_updated, currency_code)
                    mid_rate, last_updated = self._get_latest_rate(result)

                    rates_dict[currency_code] = ((1/float(mid_rate)), last_updated)
                    
            else:
                rates_dict[currency_code] = (1.0, fields.Date.today())

        return rates_dict

    def _get_latest_rate(self, result):
        data = result['data']
        data_detail = data['data_detail']
        data_header = data['data_header']

        last_updated = data_header['last_updated']
        mid_rate = data_detail[0]['mid_rate']

        return mid_rate, last_updated

    def get_daily_avg_exg_rate(self, start_period, end_period, currency):

        url = "https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE/?start_period=%s&end_period=%s&currency=%s" %(start_period, end_period, currency)

        payload={}
        headers = {
            'X-IBM-Client-Id': self.client_id,
            'Cookie': COOKIE
        }

        try:
            response = requests.request("GET", url, headers=headers, data=payload)
        except:
            return False


        return response.json()['result']

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    client_id = fields.Char(related="company_id.client_id", readonly=False)
