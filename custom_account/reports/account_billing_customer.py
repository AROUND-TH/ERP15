# -*- coding: utf-8 -*-

from odoo import models


class ReportAccountBillingCustomer(models.AbstractModel):
    _name = 'report.custom_account.account_billing_customer'
    _description = "Report Billing Note"


    def _get_report_values(self, docids, data=None):
        if docids:
            account_billing = self.env['account.billing.customer'].browse(docids)
        else:
            account_billing = self.env['account.billing.customer'].browse(data.get("docids"))
        data = self.get_data(data)

        docargs = {
            'doc_ids': docids,
            'doc_model': 'account.billing.customer',
            'docs': account_billing,
            'data': data,
        }
        return docargs


    def get_data(self, data):
        return {}

