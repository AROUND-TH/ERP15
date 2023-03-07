# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import xlrd

from datetime import datetime
from odoo import fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class WizardImportMRPBomLine(models.TransientModel):
    _name = "wizard.import.mrp.bom.line"
    _description = 'WizardImportMRPBomLine'

    row = fields.Integer("Row")
    product_tmpl_id = fields.Many2one("product.template")
    product_default_code = fields.Char("Default Code")
    production_type = fields.Selection([
        ("PACKING","PACKING"),
        ("MIXING","MIXING"),
        ("EXTRUSION","EXTRUSION"),
        ("PREMIX","PREMIX"),
        ("DIGEST","DIGEST"),
        ("MIXSHAPE","MIXSHAPE")],string="Production Type",default="MIXING")
    type = fields.Selection([
        ("normal","Manufacture this product"),
        ("phantom","Kit"),
        ("subcontract","Subcontracting")],string="Bom Type",default="normal")
    bom_status = fields.Selection([
        ("Active","Active"),
        ("Inactive","Inactive")],string="Bom Status",default="Active")
    code = fields.Char("Reference")
    ecm_no = fields.Char("ECM No.")
    ecm_date = fields.Date("ECM Date")
    product_qty = fields.Float("Quantity")
    product_uom_id = fields.Many2one("uom.uom",string="Unit")
    bom_line_product_id = fields.Many2one("product.product")
    bom_line_type = fields.Char("Type")
    bom_line_product_qty = fields.Float("Quantity")
    bom_line_product_uom_id = fields.Many2one("uom.uom",string="Product Unit")
    operation_ids_workcenter_name = fields.Char("Operations")
    operation_ids_workcenter_id = fields.Many2one("mrp.workcenter")
    operation_ids_time_cycle_manual = fields.Float("Default Duration")
    finished_product_percentage = fields.Float("Finished Product Percentage")

class WizardImportMRPBom(models.TransientModel):
    _name = "wizard.import.mrp.bom"
    _description = 'WizardImportMRPBom'

    upload = fields.Binary('Import File (*.xlsx)')

    def get_mrp_bom_template(self):
        return {
            'type':'ir.actions.act_url',
            'name':'mrp_planned_template',
            'target':'new',
            'url':'/excel_import_export_mrp/static/templates/mrp_bom_bluefalo.xlsx',
        }
    
    def create_mrp_bom_from_wizard(self,bom_list):
        wizard_import_mrp_bom_line_env = self.env['wizard.import.mrp.bom.line']
        mrp_bom_env = self.env['mrp.bom']
        bom_lines = []
        operation_ids = []
        for rec in bom_list:
            wizard_import_mrp_bom_lines = wizard_import_mrp_bom_line_env.search([('product_default_code','=',rec)])
            if wizard_import_mrp_bom_lines:
                vals = {
                    'product_tmpl_id':wizard_import_mrp_bom_lines[0].product_tmpl_id.id,
                    'production_type':wizard_import_mrp_bom_lines[0].production_type,
                    'type':wizard_import_mrp_bom_lines[0].type,
                    'bom_status':wizard_import_mrp_bom_lines[0].bom_status,
                    'code':wizard_import_mrp_bom_lines[0].code,
                    'ecm_no':wizard_import_mrp_bom_lines[0].ecm_no,
                    'ecm_date':wizard_import_mrp_bom_lines[0].ecm_date,
                    'product_qty':wizard_import_mrp_bom_lines[0].product_qty,
                    'product_uom_id':wizard_import_mrp_bom_lines[0].product_uom_id.id,
                    'costs_overhead_product_percentage':wizard_import_mrp_bom_lines[0].finished_product_percentage,
                }
                mrp_bom_id = mrp_bom_env.create(vals)
            for bom_line in wizard_import_mrp_bom_lines:
                # _logger.info(bom_line.bom_line_product_uom_id.id)
                bom_lines.append([0,0,{
                    'product_id':bom_line.bom_line_product_id.id,
                    'bom_line_type':bom_line.bom_line_type,
                    'product_qty':bom_line.bom_line_product_qty,
                    'product_uom_id':bom_line.bom_line_product_uom_id.id,
                }])
                if bom_line.operation_ids_workcenter_id.id:
                    # _logger.info(bom_line.operation_ids_workcenter_id.id)
                    operation_ids.append([0,0,{
                        'name':bom_line.operation_ids_workcenter_name,
                        'workcenter_id':bom_line.operation_ids_workcenter_id.id,
                        'time_cycle_manual':bom_line.operation_ids_time_cycle_manual,
                    }])
            mrp_bom_id.write({
                "bom_line_ids":bom_lines,
                "operation_ids":operation_ids,
            })
            bom_lines = []
            operation_ids = []

    def conv_float_date_to_date(self,value):
        # _logger.info(value)
        hours, hourSeconds = divmod(value,1)
        minutes, seconds = divmod(hourSeconds *60,1)
        return (
            int(hours),
            int(minutes),
            int(seconds * 60),
        )

    def conv_time_float(self,value):
        if value != "":
            vals = value.split(':')
            float_time = float(vals[0]) * 60
            float_time += float(vals[1])
            minutes, seconds = divmod(float(vals[2]), 60)
            float_time += minutes
            float_time += seconds / 60
            return float_time
        else:
            return 0.0

    def action_upload(self):
        record_data = base64.b64decode(self.upload)
        cols_product_internal_code = 0
        cols_production_type = 1
        cols_bom_type = 2
        cols_bom_status = 3
        cols_code = 4
        cols_ecm_no = 5
        cols_ecm_date = 6
        cols_product_qty = 7
        cols_product_uom_id = 8
        cols_bom_line_ids_product_internal_code = 9
        cols_bom_line_ids_type = 11
        cols_bom_line_ids_product_qty = 12
        cols_bom_line_ids_product_uom_id = 13
        cols_operation_ids_workcenter_id = 14
        cols_operation_ids_time_cycle_manual = 15
        cols_finished_product_percentage = 17

        mrp_bom_obj = self.env['mrp.bom']
        product_template_obj = self.env['product.template']
        product_product_obj = self.env['product.product']
        uom_obj = self.env['uom.uom']
        mrp_workcenter_obj = self.env['mrp.workcenter']
        wizard_import_mrp_bom_line_obj = self.env['wizard.import.mrp.bom.line']
        import_mrp_bom_line_ids = wizard_import_mrp_bom_line_obj.search([])
        import_mrp_bom_line_ids.unlink()
        wb = xlrd.open_workbook(file_contents=record_data)
        product_tmpl_list = []
        bom = []
        bom_line = []
        product_tmpl_code = ""
        for sheet in wb.sheets():
            if not sheet:
                raise UserError(_('Format ไม่ถูกต้อง กรุณาตรวจสอบข้อมูล หรือดาวน์โหลด Template ตัวอย่างจากในระบบ'))
            for row in range(sheet.nrows):
                if row > 0 and row < sheet.nrows + 1:
                    product_code = sheet.cell(row,cols_product_internal_code).value
                    production_type_value = sheet.cell(row,cols_production_type).value
                    bom_type_value = sheet.cell(row,cols_bom_type).value
                    bom_status_value = sheet.cell(row,cols_bom_status).value
                    code_value = sheet.cell(row,cols_code).value
                    ecm_no_value = sheet.cell(row,cols_ecm_no).value
                    ecm_date_value = sheet.cell(row,cols_ecm_date).value
                    product_qty_value = sheet.cell(row,cols_product_qty).value
                    product_uom_id_value = sheet.cell(row,cols_product_uom_id).value
                    bom_line_product_default_code = sheet.cell(row,cols_bom_line_ids_product_internal_code).value
                    bom_line_type = sheet.cell(row,cols_bom_line_ids_type).value
                    bom_line_product_qty = sheet.cell(row,cols_bom_line_ids_product_qty).value
                    bom_line_product_uom_id = sheet.cell(row,cols_bom_line_ids_product_uom_id).value
                    operation_ids_workcenter = sheet.cell(row,cols_operation_ids_workcenter_id).value
                    operation_ids_workcenter_time_cycle_manual = sheet.cell(row,cols_operation_ids_time_cycle_manual).value
                    finished_product_percentage_value = sheet.cell(row,cols_finished_product_percentage).value
                    
                    # _logger.info(product_code.encode('utf-8'))
                    if not product_code.encode('utf-8') == b'':
                        product_tmpl_code = product_code
                        production_type = production_type_value
                        bom_type = bom_type_value
                        bom_status = bom_status_value
                        code = code_value
                        ecm_no = ecm_no_value
                        ecm_date = ecm_date_value
                        product_qty = product_qty_value
                        product_uom_id = product_uom_id_value
                        finished_product_percentage = finished_product_percentage_value
                        if bom_line_product_default_code and operation_ids_workcenter:
                            vals_bom_lines = {
                                "row":row,
                                "product_tmpl_code": product_tmpl_code,
                                "production_type":production_type,
                                "type":bom_type,
                                "bom_status":bom_status,
                                "code":code,
                                "ecm_no":ecm_no,
                                "ecm_date":ecm_date,
                                "product_qty":product_qty,
                                "product_uom_id":product_uom_id,
                                "bom_line_product_id":bom_line_product_default_code,
                                "bom_line_type":bom_line_type,
                                "bom_line_product_qty":bom_line_product_qty,
                                "bom_line_product_uom_id":bom_line_product_uom_id,
                                "operation_ids_workcenter_id":operation_ids_workcenter,
                                "operation_ids_workcenter_time_cycle_manual":operation_ids_workcenter_time_cycle_manual,
                                "finished_product_percentage":finished_product_percentage,
                            }
                        bom_line.append(vals_bom_lines)
                    elif product_code.encode('utf-8') == b'' and bom_line_product_default_code and operation_ids_workcenter:
                        vals_bom_lines = {
                            "row":row,
                            "product_tmpl_code": product_tmpl_code,
                            "production_type":production_type,
                            "type":bom_type,
                            "bom_status":bom_status,
                            "code":code,
                            "ecm_no":ecm_no,
                            "ecm_date":ecm_date,
                            "product_qty":product_qty,
                            "product_uom_id":product_uom_id,
                            "bom_line_product_id":bom_line_product_default_code,
                            "bom_line_type":bom_line_type,
                            "bom_line_product_qty":bom_line_product_qty,
                            "bom_line_product_uom_id":bom_line_product_uom_id,
                            "operation_ids_workcenter_id":operation_ids_workcenter,
                            "operation_ids_workcenter_time_cycle_manual":operation_ids_workcenter_time_cycle_manual,
                            'finished_product_percentage':finished_product_percentage,
                        }
                        bom_line.append(vals_bom_lines)
                    elif product_code.encode('utf-8') == b'' and bom_line_product_default_code and operation_ids_workcenter.encode('utf-8') == b'':
                        vals_bom_lines = {
                            "row":row,
                            "product_tmpl_code": product_tmpl_code,
                            "production_type":production_type,
                            "type":bom_type,
                            "bom_status":bom_status,
                            "code":code,
                            "ecm_no":ecm_no,
                            "ecm_date":ecm_date,
                            "product_qty":product_qty,
                            "product_uom_id":product_uom_id,
                            "bom_line_product_id":bom_line_product_default_code,
                            "bom_line_type":bom_line_type,
                            "bom_line_product_qty":bom_line_product_qty,
                            "bom_line_product_uom_id":bom_line_product_uom_id,
                            "operation_ids_workcenter_id":"",
                            "operation_ids_workcenter_time_cycle_manual":"",
                            "finished_product_percentage":0,
                        }
                        bom_line.append(vals_bom_lines)
                    if product_tmpl_code not in product_tmpl_list:
                        product_tmpl_list.append(product_tmpl_code)

            bom.append(bom_line)
            product_tmpl_not_found_list = []
            for product_tmpl in product_tmpl_list:
                product_tmpl_id = product_template_obj.search([('default_code','=',product_tmpl)])
                if not product_tmpl_id:
                    product_tmpl_not_found_list.append(product_tmpl)
            if len(product_tmpl_not_found_list) > 0:
                raise UserError(_("Not found product reference code \n %s"%"\n".join(product_tmpl_not_found_list)))

            bom_line_product_id_not_found_list = []
            for line in bom_line:
                product_product_id = product_product_obj.search([('default_code','=',line["bom_line_product_id"])])
                if not product_product_id:
                    bom_line_product_id_not_found_list.append(line["bom_line_product_id"])
            if len(bom_line_product_id_not_found_list) > 0:
                raise UserError(_("Not found product reference code \n %s"%"\n".join(bom_line_product_id_not_found_list)))
            
            for rec in bom_line:
                product_tmpl_id = product_template_obj.search([('default_code','=',rec['product_tmpl_code'])])
                if rec['type'] == 'Manufacture this product':
                    bom_type = "normal"
                elif rec['type'] == 'Kit':
                    bom_type = "phantom"
                elif rec['type'] == 'Subcontracting':
                    bom_type = "subcontract"
                else :
                    bom_type = "normal"
                product_uom_id = uom_obj.search([('name','=',rec['product_uom_id'])],limit=1,order="id asc")
                bom_line_product_id = product_product_obj.search([("default_code",'=',rec['bom_line_product_id'])])
                bom_line_product_uom_id = uom_obj.search([('name','=',rec['bom_line_product_uom_id'])],limit=1,order="id asc")
                operation_ids_workcenter_id = mrp_workcenter_obj.search([("name",'=',rec['operation_ids_workcenter_id'])])
                # excel_ecm_date = xlrd.xldate_as_datetime(rec['ecm_date'],0)
                ecm_date_format = str(rec['ecm_date'])+' 00:00:00'
                ecm_date = datetime.strptime(ecm_date_format,'%d/%m/%Y %H:%M:%S').date()
                # ecm_date = excel_ecm_date.date()
                wizard_import_mrp_bom_line_id = wizard_import_mrp_bom_line_obj.create({
                    "row":rec['row'],
                    "product_tmpl_id":product_tmpl_id.id or "",
                    "product_default_code":rec['product_tmpl_code'],
                    "production_type":rec['production_type'],
                    "type":bom_type,
                    "bom_status":rec['bom_status'],
                    "code":rec['code'],
                    "ecm_no":rec['ecm_no'],
                    "ecm_date":ecm_date,
                    "product_qty":rec['product_qty'],
                    "product_uom_id":product_uom_id.id or "",
                    "bom_line_product_id":bom_line_product_id.id or "",
                    "bom_line_type":rec['bom_line_type'],
                    "bom_line_product_qty":rec['bom_line_product_qty'],
                    "bom_line_product_uom_id":bom_line_product_id.uom_id.id,
                    "operation_ids_workcenter_name":rec['operation_ids_workcenter_id'],
                    "operation_ids_workcenter_id":operation_ids_workcenter_id.id or "",
                    "operation_ids_time_cycle_manual":self.conv_time_float(rec['operation_ids_workcenter_time_cycle_manual']) or "",
                    "finished_product_percentage":rec['finished_product_percentage'],
                })
                # _logger.info(wizard_import_mrp_bom_line_id.id)
            self.create_mrp_bom_from_wizard(product_tmpl_list)
            wizard_message_id = self.env['wizard.success.message'].create({'message':'Import BOM completed.'})
            return {
                'name':'Success',
                'type':'ir.actions.act_window',
                'view_mode':'form',
                'res_model':'wizard.success.message',
                'res_id': wizard_message_id.id,
                'target': 'new'
            }
