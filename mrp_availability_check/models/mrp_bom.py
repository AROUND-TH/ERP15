# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date



class MrpBom(models.Model):
    _inherit = "mrp.bom"

    is_stock = fields.Boolean("Stock Buffered", compute="_compute_is_stock_buffered")
    lt = fields.Float("LT (days)", compute="_compute_lead_times")
    dlt = fields.Float("DLT (days)", compute="_compute_lead_times")
    clt = fields.Float("CLT (days)", compute="_compute_lead_times")

    def _get_locations(self):
        domain = [('usage', '=', 'internal')]
        for record in self:
            if record.picking_type_id:
                domain += [('id', 'child_of', record.picking_type_id.warehouse_id.view_location_id.id)]
            domain += ['|', ('company_id', '=', False), ('company_id', '=', record.company_id.id)]
            location_ids = self.env['stock.location'].search(domain)
            location_ids |= record.company_id.subcontracting_location_id
        return location_ids

    def _get_search_stock_buffer_domain(self):
        location_ids = self._get_locations()
        domain = [("location_id", "in", location_ids.ids)]
        if self.product_id:
            domain += [("product_id", "=", self.product_id.id)]
        else:
            domain += [("product_id", "in", self.product_tmpl_id.product_variant_id.ids)]
        return domain

    def _compute_is_stock_buffered(self):
        for record in self:
            domain = record._get_search_stock_buffer_domain()
            reorder_points = self.env["stock.warehouse.orderpoint"].search(domain, limit=1)
            record.is_stock = True if reorder_points else False
        return True

    def _get_decoupled_lead_time(self):
        if not self.bom_line_ids:
            return 0.0
        paths = [0] * len(self.bom_line_ids)
        i = 0
        for line in self.bom_line_ids:
            if line.is_stock:
                i += 1
            elif line.product_id.bom_ids:
                bom = line.product_id.bom_ids[0]
                if bom and bom.type == "normal":
                    paths[i] += bom.product_id.produce_delay or bom.product_tmpl_id.produce_delay or 0.0
                    paths[i] += bom._get_decoupled_lead_time()
                elif bom and bom.type == "subcontract":
                    subcontractors = bom.subcontractor_ids
                    subs = bom.product_id.seller_ids.filtered(lambda sub: sub.name in subcontractors) or bom.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractors)
                    if subs:
                        paths[i] += subs[0].delay or 0.0
                    paths[i] += bom._get_decoupled_lead_time()
                i += 1
            else:
                if line.product_id.seller_ids:
                    paths[i] = line.product_id.seller_ids[0].delay
                i += 1
        return max(paths)

    def _get_comulative_lead_time(self):
        if not self.bom_line_ids:
            return 0.0
        paths = [0] * len(self.bom_line_ids)
        i = 0
        for line in self.bom_line_ids:
            if line.product_id.bom_ids:
                bom = line.product_id.bom_ids[0]
                if bom and bom.type == "normal":
                    paths[i] += bom.product_id.produce_delay or bom.product_tmpl_id.produce_delay or 0.0
                    paths[i] += bom._get_comulative_lead_time()
                elif bom and bom.type == "subcontract":
                    subcontractors = bom.subcontractor_ids
                    subs = bom.product_id.seller_ids.filtered(lambda sub: sub.name in subcontractors) or bom.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractors)
                    if subs:
                        paths[i] += subs[0].delay or 0.0
                    paths[i] += bom._get_comulative_lead_time()
                i += 1
            else:
                if line.product_id.seller_ids:
                    paths[i] = line.product_id.seller_ids[0].delay
                i += 1
        return max(paths)

    def _compute_lead_times(self):
        for record in self:
            dlt = lt = clt= 0.0
            if record.type == "normal":
                lt = record.product_id.produce_delay or record.product_tmpl_id.produce_delay
                dlt = lt + record._get_decoupled_lead_time()
                clt = lt + record._get_comulative_lead_time()
            elif record.type == "subcontract":
                subcontractors = record.subcontractor_ids
                subs = record.product_id.seller_ids.filtered(lambda sub: sub.name in subcontractors) or record.product_tmpl_id.seller_ids.filtered(lambda sub: sub.name in subcontractors)
                if subs:
                    lt = subs[0].delay
                dlt = lt + record._get_decoupled_lead_time()
                clt = lt + record._get_comulative_lead_time()
            record.lt = lt
            record.dlt = dlt
            record.clt = clt
        return True


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    is_stock = fields.Boolean("Stock Buffered", compute="_compute_is_stock_buffered")
    lt = fields.Float("LT (days)", compute="_compute_lead_times")
    dlt = fields.Float("DLT (days)", compute="_compute_lead_times")
    clt = fields.Float("CLT (days)", compute="_compute_lead_times")


    def _get_search_stock_buffer_domain(self):
        location_ids = self.bom_id._get_locations()
        domain = [("location_id", "in", location_ids.ids)]
        product = self.product_id or self.product_tmpl_id.product_variant_ids[0]
        if product:
            domain += [("product_id", "=", product.id)]
        return domain

    def _compute_is_stock_buffered(self):
        for line in self:
            domain = line._get_search_stock_buffer_domain()
            reorder_points = self.env["stock.warehouse.orderpoint"].search(domain, limit=1)
            line.is_stock = True if reorder_points else False
        return True

    @api.depends("product_id")
    def _compute_lead_times(self):
        for record in self:
            if record.product_id.bom_ids:
                record.dlt = record.product_id.bom_ids[0].dlt
                record.clt = record.product_id.bom_ids[0].clt
                record.lt = record.product_id.bom_ids[0].lt
            else:
                #seller_ids = record.product_id.seller_ids.filtered(lambda seller: not seller.is_subcontractor) or record.product_tmpl_id.seller_ids.filtered(lambda seller: not seller.is_subcontractor)
                #record.lt = record.dlt = record.clt = seller_ids and seller_ids[0].delay or 0.0
                record.lt = record.dlt = record.clt = record._get_purchase_lt()
        return True

    def _get_purchase_lt(self):
        today = date.today()
        purchase_lt = 0.0
        for record in self:
            supplier = self.env["product.supplierinfo"].search([
                ('product_id', '=', record.product_id.id),
                ('date_start', '<=', today),
                ('date_end', '>', today)], limit=1)
            if supplier:
                purchase_lt = supplier.delay
                continue
            supplier = self.env["product.supplierinfo"].search([
                ('product_id', '=', record.product_id.id)], limit=1)
            if supplier:
                purchase_lt = supplier.delay
                continue
            supplier = self.env["product.supplierinfo"].search([
                ('product_tmpl_id', '=', record.product_id.product_tmpl_id.id),
                ('date_start', '<=', today),
                ('date_end', '>', today)], limit=1)
            if supplier:
                purchase_lt = supplier.delay
                continue
            supplier = self.env["product.supplierinfo"].search([
                ('product_tmpl_id', '=', record.product_id.product_tmpl_id.id)], limit=1)
            if supplier:
                purchase_lt = supplier.delay
        return purchase_lt
