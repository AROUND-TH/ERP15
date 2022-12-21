# -*- coding: utf-8 -*-

from odoo import models


class ReportReceiptBillingCustomer(models.AbstractModel):
    _name = 'report.custom_account.receipt_billing_customer'
    _description = "Report Receipt Customer Bill"


    def _get_report_values(self, docids, data=None):
        if docids:
            receipt_billing = self.env['receipt.billing.customer'].browse(docids)
        else:
            receipt_billing = self.env['receipt.billing.customer'].browse(data.get("docids"))
        data = self.get_data(data)

        docargs = {
            'doc_ids': docids,
            'doc_model': 'receipt.billing.customer',
            'docs': receipt_billing,
            'data': data,
        }
        return docargs


    def get_data(self, data):
        return {}

