
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource
from datetime import datetime as dt
import logging

import base64
import xlrd

_logger = logging.getLogger(__name__)

class ResultMrpDemand(models.TransientModel):
    _name = "result.mrp.demand"
    _description = "Wizard for result.mrp.demand"
    _inherit = "xlsx.report"


    xls_import_file = fields.Binary(
        string="Import File (*.xlsx)"
    )

    # Report Result, import.mrp.demand
    results = fields.Many2many(
        "import.mrp.demand",
        string="Results",
        compute="_compute_results",
        help="Use compute fields, so there is nothing stored in database",
    )

    def get_mrp_demand_template(self):
        return {
            'type':'ir.actions.act_url',
            'name':'mrp_demand_template',
            'target':'new',
            'url':'/excel_import_export_mrp/static/templates/template_mrp_demand.xlsx',
        }


    def _compute_results(self):
        """On the wizard, result will be computed and added to results line
        before export to excel, by using xlsx.export
        """
        self.ensure_one()

        wb = xlrd.open_workbook(file_contents=base64.decodestring(self.xls_import_file))

        col_name = {
            0: ["warehouse_name", False],
            1: ["product_code", False],
            2: ["date_planned", False],
            3: ["planned_qty", False],
            4: ["uom_name", False],
        }
        field_type = {}
        self._set_field_data("import.mrp.demand", col_name, field_type)

        for sheet in wb.sheets():
            for row in range(sheet.nrows):
                field_value = {}

                for col in range(sheet.ncols):
                    if row > 0:
                        if col in col_name:
                            field_value[col_name[col][0]] = self._get_cell_value(sheet.cell(row,col), field_type[col_name[col][0]])

                            # @Example
                            if col_name[col][1] == True:
                                print ("col_name[col][1] : ", col_name[col][1])
                                continue
                                # @Do Something

                if row > 0:
                    res_parameter = self.env["mrp.parameter"].search(['&',('warehouse_id','=',field_value["warehouse_name"]),('product_id.default_code','=',field_value["product_code"])])
                    res_demand = self.env["mrp.demand"].search([('warehouse_id','=',field_value["warehouse_name"]),('product_id.default_code','=',field_value["product_code"]),('date_planned','=',field_value["date_planned"])])

                    if not res_parameter:
                        field_value["status"] = _("Error")
                        field_value["message"] = _("กรุณาสร้าง MRP Planning Parameters ก่อนทำรายการ MRP Demand")

                    else:
                        if not res_demand:
                            res_demand.create({
                                "mrp_parameter_id": res_parameter[0].id,
                                "date_planned": field_value["date_planned"],
                                "planned_qty": field_value["planned_qty"],
                            })
                            field_value["status"] = _("OK")
                        else:
                            if res_demand.state == 'draft':
                                res_demand.update({
                                    "planned_qty": field_value["planned_qty"],
                                })
                                field_value["status"] = _("OK")
                            else:
                                field_value["status"] = _("Error")
                                field_value["message"] = _("รายการ MRP Demand นี้ไม่ได้อยู่ในสถานะ Draft")


                    # res_warehouse = self.env["stock.warehouse"].search(['&',('name','=',field_value["warehouse_name"]),('active','=',True)])
                    # res_product = self.env["product.product"].search(['&',('default_code','=',field_value["product_code"]),('active','=',True)])
                    # if res_warehouse and res_product:
                    #     field_value["warehouse_id"] = res_warehouse[0].id
                    #     field_value["product_id"] = res_product[0].id

                    self.results += self.results.create(field_value)

        # Result = self.env["import.mrp.demand"]
        # domain = []
        # # if self.partner_id:
        # #     domain += [("partner_id", "=", self.partner_id.id)]
        # self.results = Result.search(domain)


    @api.model
    def _get_field_type(self, model, field):
        try:
            record = self.env[model].new()
            field_type = record._fields[field].type
            return field_type
        except Exception:
            raise ValidationError(
                _("Invalid declaration, %s has no valid field type") % field
            )

    @api.model
    def _set_field_data(self, model, column_dict, type_dict):
        try:
            record = self.env[model].new()

            for key, value in column_dict.items():
                type_dict[value[0]] = record._fields[value[0]].type

        except Exception:
            raise ValidationError(
                _("Invalid declaration or invalid data of {}".format(column_dict))
            )


    def _get_cell_value(self, cell, field_type=False):
        """If Odoo's field type is known, convert to valid string for import,
        if not know, just get value  as is"""
        value = False
        datemode = 0  # From book.datemode, but we fix it for simplicity
        if field_type in ["date", "datetime"]:
            ctype = xlrd.sheet.ctype_text.get(cell.ctype, "unknown type")
            if ctype in ("xldate", "number"):
                is_datetime = cell.value % 1 != 0.0
                time_tuple = xlrd.xldate_as_tuple(cell.value, datemode)
                date = dt(*time_tuple)
                value = (
                    date.strftime("%d/%m/%Y %H:%M:%S")
                    if is_datetime
                    else date.strftime("%d/%m/%Y")
                )
            else:
                date_time_value = str(cell.value)+" 08:00:00"
                value = dt.strptime(date_time_value,'%d/%m/%Y %H:%M:%S')
        elif field_type in ["integer", "float"]:
            value_str = str(cell.value).strip().replace(",", "")
            if len(value_str) == 0:
                value = ""
            elif value_str.replace(".", "", 1).isdigit():  # Is number
                if field_type == "integer":
                    value = int(float(value_str))
                elif field_type == "float":
                    value = float(value_str)
            else:  # Is string, no conversion
                value = value_str
        elif field_type in ["many2one"]:
            # If number, change to string
            if isinstance(cell.value, (int, float, complex)):
                value = str(cell.value)
            else:
                value = cell.value
        else:  # text, char
            value = str(cell.value)
        # If string, cleanup
        if isinstance(value, str):
            if value[-2:] == ".0":
                value = value[:-2]
        # Except boolean, when no value, we should return as ''
        if field_type not in ["boolean"]:
            if not value:
                value = ""
        return value

