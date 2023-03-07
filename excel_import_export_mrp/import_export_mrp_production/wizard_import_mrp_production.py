# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import xlrd

from datetime import datetime,timedelta
from odoo import fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class WizardImportMRPProduction(models.TransientModel):
    _name = "wizard.import.mrp.production"
    _description = 'WizardImportMRPProduction'

    upload = fields.Binary('Import File (*.xlsx)')

    def get_mrp_production_template(self):
        return {
            'type':'ir.actions.act_url',
            'name':'mrp_production_template',
            'target':'new',
            'url':'/excel_import_export_mrp/static/templates/mrp_production_bluefalo.xlsx',
        }



    def action_upload(self):
        record_data = base64.b64decode(self.upload)
        cols_bom_id = 0
        cols_plan_start_date = 1
        cols_quantity_to_produce = 2
        cols_product_unit = 3

        mrp_production_obj = self.env['mrp.production']
        mrp_bom_obj = self.env['mrp.bom']
        product_product_obj = self.env['product.product']
        uom_obj = self.env['uom.uom']
        procurement_group_obj = self.env['procurement.group']
        stock_move_obj = self.env['stock.move']
        picking_type_obj = self.env['stock.picking.type']
        mrp_production_location_id = self.env['stock.location'].search([('name','=','Production'),('usage','=','production')])
        wb = xlrd.open_workbook(file_contents=record_data)
        vals = []
        errors_cols_bom_id = []
        errors_cols_product_unit = []
        mrp_production_list = []
        for sheet in wb.sheets():
            if not sheet:
                raise UserError(_('Format ไม่ถูกต้อง กรุณาตรวจสอบข้อมูล หรือดาวน์โหลด Template ตัวอย่างจากในระบบ'))
            for row in range(sheet.nrows):
                if row > 0 and row < sheet.nrows + 1:
                    cols_bom_id_data = sheet.cell(row,cols_bom_id).value
                    # product_code = cols_bom_id_data[cols_bom_id_data.find('[')+1:cols_bom_id_data.find(']')]
                    product_code = cols_bom_id_data
                    mrp_bom_id = mrp_bom_obj.search([('product_tmpl_id.default_code', '=', product_code)], limit=1)
                    if not mrp_bom_id:
                        message_mrp_bom_id = "ไม่พบ MRP BOM รหัส {} แถวที่ {} ในระบบ กรุณาสร้างข้อมูลก่อนสร้าง Manufacturing Orders".format(sheet.cell(row, cols_bom_id).value,str(row+1))
                        errors_cols_bom_id.append(message_mrp_bom_id)
                    product_id = product_product_obj.search([('product_tmpl_id','=',mrp_bom_id.product_tmpl_id.id)])
                    date_planned_start_pivot = sheet.cell(row,cols_plan_start_date).value
                    date_planned_start_pivot = date_planned_start_pivot.replace("`","")
                    date_planned_start_pivot = date_planned_start_pivot
                    date_planned_start_utc = datetime.strptime(date_planned_start_pivot,'%d/%m/%Y %H:%M:%S')+timedelta(hours=-7)
                    qty_producing = float(sheet.cell(row,cols_quantity_to_produce).value)
                    uom = sheet.cell(row,cols_product_unit).value
                    uom_id = uom_obj.search([("name","=",uom)])
                    picking_type_id = picking_type_obj.search([('id','=',mrp_bom_id.picking_type_id.id)],limit=1)
                    if not uom_id:
                        message_uom = "ไม่พบ หน่วย {} แถวที่ {} กรุณากำหนดหน่วยสินค้าให้ตรงกับ MRP Planning Parameter".format(sheet.cell(row, cols_product_unit).value,str(row+1),'\n')
                        errors_cols_product_unit.append(message_uom)
                    bomlines = [(5,0,0)]
                    workorders = [(5,0,0)]
                    for bomline in mrp_bom_id.bom_line_ids:
                        bomline_vals = {
                            "name":"",
                            "product_id":bomline.product_id.id,
                            "product_uom_qty":bomline.product_qty * qty_producing,
                            "product_uom":bomline.product_uom_id.id,
                            "location_id":mrp_bom_id.picking_type_id.default_location_src_id.id,
                            "location_dest_id":mrp_bom_id.picking_type_id.default_location_dest_id.id,
                        }
                        bomlines.append((0,0,bomline_vals))
                    
                    for workorder in mrp_bom_id.operation_ids:
                        workorder_vals = {
                            "operation_id":workorder.id,
                            "workcenter_id":workorder.workcenter_id.id,
                            "name":workorder.name,
                            "duration_expected":workorder.time_cycle_manual,
                            "milestone":workorder.milestone,
                            "product_uom_id":mrp_bom_id.product_uom_id.id,
                            "date_planned_start_wo":date_planned_start_utc,
                            "qty_output_wo":0.00,
                        }
                        workorders.append((0,0,workorder_vals))


                    value = {
                        "bom_id":mrp_bom_id.id,
                        "product_id":product_id.id,
                        "date_planned_start_pivot": date_planned_start_utc,
                        "date_planned_finished_pivot": date_planned_start_utc,
                        "planning_mode":"F",
                        "date_deadline":date_planned_start_utc,
                        "propagate_cancel":False,
                        "is_scheduled":False,
                        "user_id": self.env.user.id,
                        "qty_producing": 0.000,
                        "product_qty": qty_producing,
                        "product_uom_id":uom_id.id,
                        "picking_type_id":picking_type_id.id,
                        "location_src_id":picking_type_id.default_location_src_id.id,
                        "location_dest_id":picking_type_id.default_location_dest_id.id,
                        "move_raw_ids":bomlines,
                        "workorder_ids":workorders,
                        "excel_imported":True,
                    }
                    vals.append(value)
            if len(errors_cols_bom_id) > 0:
                raise UserError(_("%s"%"\n".join(errors_cols_bom_id)))
            elif len(errors_cols_product_unit) > 0:
                raise UserError(_("%s"%"\n".join(errors_cols_product_unit)))
            else:
                for mrp_production in vals:
                    mrp_production_id = mrp_production_obj.create(mrp_production)
                    uom_production_id = uom_obj.search([("id","=",mrp_production_id.product_uom_id.id)])
                    if mrp_production_id:
                        procurement_vals = {
                            "name":mrp_production_id.name,
                            "move_type":"direct"
                        }
                        procurement_id = procurement_group_obj.create(procurement_vals)
                        mrp_production_id.write({
                            "procurement_group_id":procurement_id.id,
                            "qty_producing":0.000,
                        })
                    _logger.info(uom_production_id.name)
                    _logger.info(uom_id.name)
                    stock_move_id = stock_move_obj.create({
                        "name":"New",
                        "sequence":10,
                        "date":date_planned_start_utc,
                        "date_deadline":date_planned_start_utc,
                        "product_id":mrp_production_id.product_id.id,
                        "product_uom_qty":qty_producing,
                        "product_uom":uom_production_id.id,
                        "quantity_done":qty_producing,
                        "picking_type_id":picking_type_id.id,
                        "location_id":mrp_production_location_id.id,
                        "location_dest_id":picking_type_id.default_location_dest_id.id,
                        "state":"confirmed",
                        "origin":mrp_production_id.name,
                        "procure_method":"make_to_stock",
                        "group_id":procurement_id.id,
                        "reference":mrp_production_id.name,
                        "propagate_cancel":False,
                        "warehouse_id":picking_type_id.warehouse_id.id,
                        "production_id":mrp_production_id.id,
                        "unit_factor":1,
                    })
                    mrp_production_rec_name = mrp_production_id.name
                    mrp_production_list.append(mrp_production_rec_name)
            
        wizard_message_id = self.env['wizard.success.message'].create({'message':'Import Manufacturing completed.\n'+str(mrp_production_list)})
        return {
            'name':'Success',
            'type':'ir.actions.act_window',
            'view_mode':'form',
            'res_model':'wizard.success.message',
            'res_id': wizard_message_id.id,
            'target': 'new'
        }
