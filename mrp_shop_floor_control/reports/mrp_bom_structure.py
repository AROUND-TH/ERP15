# -*- coding: utf-8 -*-

from odoo import api, models, fields, _


class ReportBomStructureAll(models.AbstractModel):
    _name = 'report.mrp_shop_floor_control.bom_structure_all'
    _description = "Report Bom All Structure"

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms, 'get_children': self.get_children}

    def get_children(self, bomobject):
        childDict = {}
        outcome = []

        def _create_bom_lines(bom, level=0, factor=1):
            level += 1
            for line in bom.bom_line_ids:
                childDict = {
                    'level': level,
                    'pqty': line.product_qty * factor,
                    'product_name': line.product_id.product_tmpl_id.name,
                    'uom_name': line.product_uom_id.name,
                }
                outcome.append(childDict)
                boms = line.product_id.bom_ids
                if boms:
                    line_qty = line.product_uom_id._compute_quantity(line.product_qty, boms[0].product_uom_id)
                    new_factor = factor * line_qty / boms[0].product_qty
                    _create_bom_lines(boms[0], level, new_factor)

        _create_bom_lines(bomobject)
        return outcome


class ReportBomStructureOne(models.AbstractModel):
    _name = 'report.mrp_shop_floor_control.bom_structure_one'
    _description = 'Report Bom Structure'

    @api.model
    def _get_report_values(self, docids, data=None):
        boms = self.env['mrp.bom'].browse(docids)
        return {'docs': boms, 'get_children': self.get_children}

    def get_children(self, bomobject):
        childDict = {}
        outcome = []
        for line in bomobject.bom_line_ids:
            childDict = {
                'level': 1,
                'pqty': line.product_qty,
                'product_name': line.product_id.product_tmpl_id.name,
                'uom_name': line.product_uom_id.name,
            }
            outcome.append(childDict)
        return outcome
