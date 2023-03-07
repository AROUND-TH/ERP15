# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import xlrd

from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError

class WizardImportMRPPlannedOrders(models.TransientModel):
    _name = "wizard.import.mrp.planned.orders"
    _description = 'WizardImportMRPPlannedOrders'

    upload = fields.Binary('Import File (*.xlsx)')

    def get_mrp_planned_orders_template(self):
        return {
            'type':'ir.actions.act_url',
            'name':'mrp_planned_template',
            'target':'new',
            'url':'/excel_import_export_mrp/static/templates/template_mrp_planned_orders.xlsx',
        }



    def action_upload(self):
        record_data = base64.b64decode(self.upload)
        cols_product_internal_code = 0
        cols_warehouse = 1
        cols_due_date = 2
        cols_quantity = 3
        cols_uom = 4

        mrp_planned_orders_obj = self.env['mrp.planned.order']
        mrp_parameter_obj = self.env['mrp.parameter']
        warehouse_obj = self.env['stock.warehouse']
        uom_obj = self.env['uom.uom']
        wb = xlrd.open_workbook(file_contents=record_data)
        vals = []
        errors_cols_parameter_id = []
        errors_cols_warehouse = []
        errors_cols_uom = []
        for sheet in wb.sheets():
            if not sheet:
                raise UserError(_('Format ไม่ถูกต้อง กรุณาตรวจสอบข้อมูล หรือดาวน์โหลด Template ตัวอย่างจากในระบบ'))
            for row in range(sheet.nrows):
                if row > 0 and row < sheet.nrows + 1:
                    product_code = sheet.cell(row,cols_product_internal_code).value
                    mrp_parameter_id = mrp_parameter_obj.search([('product_id.default_code', '=', product_code)], limit=1)
                    if not mrp_parameter_id:
                        message_mrp_parameter_id = "ไม่พบ MRP Planning Parameters รหัส {} แถวที่ {} ในระบบ กรุณาสร้างข้อมูลก่อนสร้าง Plan Order".format(sheet.cell(row, cols_product_internal_code).value,str(row+1))
                        errors_cols_parameter_id.append(message_mrp_parameter_id)
                    warehouse = sheet.cell(row,cols_warehouse).value
                    warehouse_id = warehouse_obj.search([("name",'=',warehouse)])
                    if not warehouse_id:
                        message_warehouse = "ไม่พบ Warehouse รหัส {} แถวที่ {} ในระบบ กรุณาสร้างข้อมูลก่อนสร้าง Plan Order".format(sheet.cell(row, cols_warehouse).value,str(row+1))
                        errors_cols_warehouse.append(message_warehouse)
                    excel_due_date = sheet.cell(row,cols_due_date).value
                    mrp_qty = float(sheet.cell(row,cols_quantity).value)
                    uom = sheet.cell(row,cols_uom).value
                    uom_id = uom_obj.search([("name","=",uom)])
                    if not uom_id:
                        message_uom = "ไม่พบ หน่วย {} แถวที่ {} กรุณากำหนดหน่วยสินค้าให้ตรงกับ MRP Planning Parameter".format(sheet.cell(row, cols_uom).value,str(row+1),'\n')
                        errors_cols_uom.append(message_uom)
                    
                    warehouse_id = warehouse_obj.search([('name','=',"MTP")])
                    value = {
                        "mrp_parameter_id":mrp_parameter_id.id,
                        "product_id":mrp_parameter_id.product_id.id,
                        "warehouse_id":warehouse_id.id,
                        "due_date": datetime.strptime(excel_due_date, '%d/%m/%Y'),
                        "user_id": self.env.user.id,
                        "mrp_qty": mrp_qty,
                        "product_uom":uom_id.id,
                    }
                    vals.append(value)
            if len(errors_cols_parameter_id) > 0:
                raise UserError(_("%s"%"\n".join(errors_cols_parameter_id)))
            elif len(errors_cols_warehouse) > 0:
                raise UserError(_("%s"%"\n".join(errors_cols_warehouse)))
            elif len(errors_cols_uom) > 0:
                raise UserError(_("%s"%"\n".join(errors_cols_uom)))
            else:
                for mrp_plan in vals:
                    mrp_planned_orders_obj.create(mrp_plan)

            wizard_message_id = self.env['wizard.success.message'].create({'message': 'Import Planned Order completed.'})
            return {
                'name': 'Success',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'wizard.success.message',
                'res_id': wizard_message_id.id,
                'target': 'new'
            }
