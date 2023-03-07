# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MrpBomItem1(models.TransientModel):
    _name = "mrp.bom.item1"
    _description = "MRP BoM Item 1 Comparison"

    compare_id = fields.Many2one('mrp.compare.bom', 'Comparison ID')
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float("Quantity")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    bom_product_template_attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Apply on Variants")


class MrpBomItem2(models.TransientModel):
    _name = "mrp.bom.item2"
    _description = "MRP BoM Item 1 Comparison"

    compare_id = fields.Many2one('mrp.compare.bom', 'Comparison ID')
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float("Quantity")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    bom_product_template_attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Apply on Variants")


class MrpComparegBom(models.TransientModel):
    _name = "mrp.compare.bom"
    _description = "MRP BoM Comparison"


    bom_id1 = fields.Many2one('mrp.bom', 'BoM 1', required=True)
    type_id1 = fields.Selection(related="bom_id1.type", string='BoM Type')
    product_tmpl_id1 = fields.Many2one(related='bom_id1.product_tmpl_id')
    product_id1 = fields.Many2one(related='bom_id1.product_id')
    bom_id2 = fields.Many2one('mrp.bom', 'BoM 2', required=True)
    type_id2 = fields.Selection(related="bom_id2.type", string='BoM Type')
    product_tmpl_id2 = fields.Many2one(related='bom_id2.product_tmpl_id')
    product_id2 = fields.Many2one(related='bom_id2.product_id')
    item1notin2 = fields.One2many('mrp.bom.item1', 'compare_id')
    item2notin1 = fields.One2many('mrp.bom.item2', 'compare_id')


    def action_compare_boms(self):
        bom1NewItems = []
        bom2NewItems = []
        bom1Dict = self._get_bom_lines(self.bom_id1)
        bom2Dict = self._get_bom_lines(self.bom_id2)
        bom1NewItems, bom2NewItems = self.compute_differences(bom1Dict, bom2Dict)
        self.write({'item1notin2': [(6, 0, bom1NewItems)], 'item2notin1': [(6, 0, bom2NewItems)]})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Differences in BoMs'),
            'res_model': 'mrp.compare.bom',
            'target': 'new',
            'views': [(self.env.ref('mrp_shop_floor_control.mrp_bom_differences_form').id, "form")],
            'res_id': self.id,
        }

    @api.model
    def _get_bom_lines(self, bom):
        bomDict = {}
        for bom_line in bom.bom_line_ids:
            createVals = {'product_id': bom_line.product_id.id,
                          'product_qty': bom_line.product_qty,
                          'bom_line_id': bom_line.id,
                          'product_uom_id': bom_line.product_uom_id.id,
                          'compare_id': self.id,
                          'bom_product_template_attribute_value_ids': bom_line.bom_product_template_attribute_value_ids,
                          }
            key = '%s_%s' % (bom_line.product_id.id, bom_line.product_qty)
            if key not in bomDict:
                bomDict[key] = [createVals]
        return bomDict

    def compute_differences(self, bom1Dict, bom2Dict):
        leftItems = []
        rightItems = []
        key1 = set(bom1Dict.keys())
        key2 = set(bom2Dict.keys())
        right = key1 - key2
        left = key2 - key1
        for key in right:
            for toCreateVals in bom1Dict[key]:
                rightItems.append(self.getLeftBom(toCreateVals))
        for key in left:
            for toCreateVals in bom2Dict[key]:
                leftItems.append(self.getRightBom(toCreateVals))
        return rightItems, leftItems

    def getLeftBom(self, toCreateVals):
        if 'product_id' in toCreateVals:
            del toCreateVals['product_id']
        return self.env['mrp.bom.item1'].create(toCreateVals).id

    def getRightBom(self, toCreateVals):
        if 'product_id' in toCreateVals:
            del toCreateVals['product_id']
        return self.env['mrp.bom.item2'].create(toCreateVals).id

    def action_close(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('BoM Comparison'),
            'res_model': 'mrp.compare.bom',
            'target': 'new',
            'views': [(self.env.ref('mrp_shop_floor_control.view_mrp_compare_bom_form').id, "form")],
            'res_id': self.id,
        }