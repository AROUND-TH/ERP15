# -*- coding: utf-8 -*-

from odoo import models


class ReportPayBillingVendor(models.AbstractModel):
    _name = 'report.custom_account.pay_billing_vendor'
    _description = "Report Pay Vendor Bill"


    def _get_report_values(self, docids, data=None):
        if docids:
            pay_billing = self.env['pay.billing.vendor'].browse(docids)
        else:
            pay_billing = self.env['pay.billing.vendor'].browse(data.get("docids"))
        data = self.get_data(data)

        docargs = {
            'doc_ids': docids,
            'doc_model': 'pay.billing.vendor',
            'docs': pay_billing,
            'data': data,
        }
        return docargs


    def get_data(self, data):
        return {}

