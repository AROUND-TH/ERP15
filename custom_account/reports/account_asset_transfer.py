# -*- coding: utf-8 -*-

from odoo import models, fields, api

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


class ReportAccountAssetTransfer(models.AbstractModel):
    _name = 'report.custom_account.account_asset_transfer'
    _description = "Report Asset Transfer"


    def _get_report_values(self, docids, data=None):
        if docids:
            account_assets = self.env['account.asset'].browse(docids)
        else:
            account_assets = self.env['account.asset'].browse(data.get("docids"))
        transfer = self.get_transfer(data)

        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.asset',
            'docs': account_assets,
            'document_number': data.get("document_number"),
            'create_user': data.get("employee_name") or self.env.user.name,
            'transfer': transfer,
        }
        return docargs


    def get_transfer(self, data):
        if data:
            if data.get("transfer_date"):
                transfer_date = datetime.strptime(data.get("transfer_date"), DEFAULT_SERVER_DATE_FORMAT).strftime('%d/%m/%Y')
            else:
                transfer_date = ""

            if data.get("account_analytic_id"):
                account_analytic_id = data.get("account_analytic_id")[1]
            else:
                account_analytic_id = ""

            if data.get("transfer_account_analytic_id"):
                transfer_account_analytic_id = data.get("transfer_account_analytic_id")[1]
            else:
                transfer_account_analytic_id = ""

            return {
                'quantity': data.get("quantity") or 1,
                'transfer_date': transfer_date,
                'account_analytic_id': account_analytic_id,
                'transfer_account_analytic_id': transfer_account_analytic_id,
            }
        else:
            return {
                'quantity': 0,
                'transfer_date': "",
                'account_analytic_id': None,
                'transfer_account_analytic_id': None,
            }

