# -*- coding: utf-8 -*-

from odoo import models


class ReportAccountBillingVendor(models.AbstractModel):
    _name = 'report.custom_account.account_billing_vendor'
    _description = "Report Bill Acceptance"


    def _get_report_values(self, docids, data=None):
        if docids:
            account_billing = self.env['account.billing.vendor'].browse(docids)
        else:
            account_billing = self.env['account.billing.vendor'].browse(data.get("docids"))
        data = self.get_data(data)

        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.billing.vendor',
            'docs': account_billing,
            'data': data,
        }
        return docargs


    def get_data(self, data):
        return {}

