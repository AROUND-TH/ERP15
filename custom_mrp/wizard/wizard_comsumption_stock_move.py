from odoo import models,fields,api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class WizardConsumptionStockMove(models.TransientModel):
    _name = 'wizard.consumption.stock.move'
    _description = 'WizardConsumptionStockMove'

    doc_id = fields.Integer()
    mrp_production_id = fields.Many2one('mrp.production')
    name = fields.Char()
    consumption_stock_move_line_ids = fields.Many2many('wizard.consumption.stock.move.line',relation="wz_consumption_move_rel",String="Move Line")

    def action_confirm(self):
        stock_move_env = self.env['stock.move']
        stock_move_line_env = self.env['stock.move.line']
        
        move_line_ids = []
        now = datetime.strftime(fields.Datetime.context_timestamp(self,datetime.now()),"%Y-%m-%d %H:%M:%S")
        for rec in self:
            mrp_production_rec = self.env['mrp.production'].search([('id','=',rec.doc_id)])
            if rec.consumption_stock_move_line_ids:
                for move in rec.consumption_stock_move_line_ids:
                    stock_move_line_rec = stock_move_line_env.search(['&',('move_id','=',move.move_id.id),('product_id','=',move.product_id.id)])
                    for stock_move_line in stock_move_line_rec:
                        stock_move_line.unlink()
                for move in rec.consumption_stock_move_line_ids:
                    stock_move_id = stock_move_env.search([('id','=',move.move_id.id)])
                    if move.product_id and move.lot_id:
                        move_line_ids.append((0,0,{
                            'production_id':mrp_production_rec.id,
                            'reference':mrp_production_rec.name,
                            'product_id':move.product_id.id,
                            'location_id':move.location_id.id,
                            'location_dest_id':move.location_dest_id.id,
                            'lot_id':move.lot_id.id,
                            'qty_done':move.product_uom_qty,
                            'product_uom_id':move.product_uom.id,
                            'description_picking':'From Consumption Function',
                            'date':now,
                        }))
                    else:
                        move_line_ids.append((0,0,{
                            'production_id':mrp_production_rec.id,
                            'reference':mrp_production_rec.name,
                            'product_id':move.product_id.id,
                            'location_id':move.location_id.id,
                            'location_dest_id':move.location_dest_id.id,
                            'qty_done':move.product_uom_qty,
                            'product_uom_id':move.product_uom.id,
                            'description_picking':'From Consumption Function',
                            'date':now,
                        }))
                    stock_move_id.write({
                        "move_line_ids":move_line_ids
                    })
                    move_line_ids = []


class WizardConsumptionStockMove(models.TransientModel):
    _name = 'wizard.consumption.stock.move.line'
    _description = 'WizardConsumptionStockMove'

    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one('product.product',string="Product")
    product_uom_qty = fields.Float(string="To Consume")
    location_id = fields.Many2one('stock.location',string="From")
    location_dest_id = fields.Many2one('stock.location',string="To")
    lot_id = fields.Many2one('stock.production.lot',string="Lot/Serial Number",domain="[('product_id','=',product_id)]")
    quantity_done = fields.Float(string="Done")
    product_uom = fields.Many2one('uom.uom',string="Unit of measure")
    tracking = fields.Char("Tracking")