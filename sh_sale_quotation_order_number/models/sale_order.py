# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    quotation_no = fields.Char("Quotation Number", readonly=True)

    @api.model
    def create(self, vals):
        if vals.get("name", _("New")) == _("New"):

            if "company_id" in vals:
                sale_seq = self.env["ir.sequence"].with_context(
                    force_company=vals["company_id"]).next_by_code("sale.quotation") or _("New")
                vals["name"] = sale_seq
                vals["quotation_no"] = sale_seq
            else:
                sale_seq = self.env["ir.sequence"].next_by_code(
                    "sale.quotation") or _("New")
                vals["name"] = sale_seq
                vals["quotation_no"] = sale_seq

        res = super(SaleOrder, self).create(vals)
        return res

    def _action_confirm(self):

        res = super(SaleOrder, self)._action_confirm()
        if self:
            for data in self:
                if data.company_id:
                    sale_no = data.env["ir.sequence"].with_context(
                        force_company=data.company_id.id).next_by_code("sale.order")
                    return data.write({"name": sale_no})

                else:
                    sale_no = data.env["ir.sequence"].next_by_code(
                        "sale.order")
                    return data.write({"name": sale_no})

            return res
