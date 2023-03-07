import math
import logging
import requests

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

RETURN_REASON = [
    ('not_quality', 'สินค้าไม่ได้คุณภาพ'),
    ('damaged', 'สินค้าเสียหาย'),
    ('detail_not_match', 'สินค้าไม่ตรงตามรายละเอียด'),
    ('incomplete', 'สินค้าไม่ครบถ้วน'),
    ('expired', 'สินค้าหมดอายุ'),
]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    must_validate = fields.Boolean(copy=False)
    first_validate = fields.Boolean(copy=False)
    second_validate = fields.Boolean(copy=False)
    return_reason = fields.Selection(RETURN_REASON)
    return_remark = fields.Text(string="Remark")

    # ux field
    show_return_button = fields.Boolean(compute="_compute_show_return_button")
    show_return_info = fields.Boolean(readonly=True)

    # === Interface Truckscale Options ===
    set_done_by_weight = fields.Boolean()
    interface_truckscale_data = fields.Boolean(related='picking_type_id.interface_truckscale_data', store=True, readonly=True)
    show_truckscale_data = fields.Boolean(related='picking_type_id.show_truckscale_data', readonly=True)

    # === Truckscale API ===
    api_truckscale_model = fields.Char(string='Truckscale Model', default="wizard.truckscale.item", readonly=True)
    api_truckscale_id = fields.Integer(string='Truckscale', default=False, readonly=True, states={'assigned': [('readonly', False)]}, copy=False)

    # === Truckscale fields ===
    ts_id = fields.Integer(string='Truckscale ID', copy=False)
    ts_trans_id = fields.Char(string='TransId', copy=False)
    ts_car_code = fields.Char(string='CarCode', copy=False)
    ts_car_prov = fields.Char(string='CarProv', copy=False)
    ts_car_code2 = fields.Char(string='CarCode2', copy=False)
    ts_car_prov2 = fields.Char(string='CarProv2', copy=False)
    ts_driver = fields.Char(string='DriverName', copy=False)
    ts_driver_id = fields.Char(string='DriverIdCard', copy=False)
    ts_barcode = fields.Char(string='Barcode', copy=False)
    ts_ingred_code = fields.Char(string='IngredCode', copy=False)
    ts_vendor_code = fields.Char(string='VendorCode', copy=False)
    ts_trans_wt = fields.Float(string='TransWeight', copy=False)
    ts_car_wt = fields.Float(string='CarWeight', copy=False)
    ts_actual_wt = fields.Float(string='ActualWeight', copy=False)
    # ux field
    show_set_done_by_weight = fields.Boolean(compute="_compute_show_set_done_by_weight")
    transportation = fields.Char(compute="_compute_get_default", string="Transportation")
    port_of_loading = fields.Char(compute="_compute_get_default", string="Port of Loading")
    port_of_destination = fields.Char(compute="_compute_get_default", string="Port of Destination")

    def _compute_get_default(self):
        for rec in self:
            if rec.sale_id:
                rec.transportation = rec.sale_id.transportation
                rec.port_of_loading = rec.sale_id.port_of_loading
                rec.port_of_destination = rec.sale_id.port_of_destination
            else:
                rec.transportation = False
                rec.port_of_loading = False
                rec.port_of_destination = False

    @api.depends('ts_trans_id', 'picking_type_id')
    def _compute_show_set_done_by_weight(self):
        for rec in self:
            val = False
            if rec.state != "assigned":
                pass
            elif rec.picking_type_id.set_done_by_weight and rec.ts_trans_id:
                val = True
            rec.show_set_done_by_weight = val

    def _compute_show_return_button(self):
        for rec in self:
            if rec.state != "done":
                rec.show_return_button = False
                continue

            warehouse_id = rec.picking_type_id.warehouse_id
            rec.show_return_button = rec.picking_type_id in [warehouse_id.in_type_id, warehouse_id.out_type_id]

    def clear_truckscale(self):
        for rec in self:
            rec.update({
                "api_truckscale_id": None,
                "ts_id": None,
                "ts_trans_id": None,
                "ts_car_code": None,
                "ts_car_prov": None,
                "ts_car_code2": None,
                "ts_car_prov2": None,
                "ts_driver": None,
                "ts_driver_id": None,
                "ts_barcode": None,
                "ts_ingred_code": None,
                "ts_vendor_code": None,
                "ts_trans_wt": None,
                "ts_car_wt": None,
                "ts_actual_wt": None
            })

    @api.onchange('api_truckscale_id')
    def _onchange_api_truckscale(self):
        if not self.interface_truckscale_data:
            return

        truckscale = self.env['wizard.truckscale.item'].browse(self.api_truckscale_id)
        self.ts_id = truckscale.ts_id
        self.ts_trans_id = truckscale.ts_trans_id
        self.ts_car_code = truckscale.ts_car_code
        self.ts_car_prov = truckscale.ts_car_prov
        self.ts_car_code2 = truckscale.ts_car_code2
        self.ts_car_prov2 = truckscale.ts_car_prov2
        self.ts_driver = truckscale.ts_driver
        self.ts_driver_id = truckscale.ts_driver_id
        self.ts_barcode = truckscale.ts_barcode
        self.ts_ingred_code = truckscale.ts_ingred_code
        self.ts_vendor_code = truckscale.ts_vendor_code
        self.ts_trans_wt = truckscale.ts_trans_wt
        self.ts_car_wt = truckscale.ts_car_wt
        self.ts_actual_wt = truckscale.ts_actual_wt
        self.api_truckscale_id = None
        self.set_done_by_weight = False

    def truckscale_update_quantity(self):
        if self.picking_type_id.set_done_by_weight:
            for ml_id in self.move_line_ids_without_package.filtered(lambda ml: ml.product_id.is_truckscale):
                if self.move_line_ids_without_package.filtered(lambda l: l.product_id == ml_id.product_id and l.id != ml_id.id):
                    raise ValidationError(_(f'Product {ml_id.product_id.name} can\'t more then one.'))
                ml_id.qty_done = self.ts_actual_wt
        self.set_done_by_weight = True

    def cancel_truckscale(self, ts_id):
        ir_config = self.env['ir.config_parameter'].sudo()
        middleware_uri = ir_config.get_param('middleware_api_uri')
        middleware_username = ir_config.get_param('middleware_api_username')
        middleware_password = ir_config.get_param('middleware_api_password')
        try:
            auth_url = middleware_uri + "/api/TokenAuth/Authenticate"
            data = {
                "UserNameOrEmailAddress": middleware_username,
                "Password": middleware_password
            }
            res = requests.post(auth_url, json=data)
            auth_response = res.json()
            if auth_response.get("error"):
                raise ValueError("MiddleWare Authenticate error.")

            cancel_url = middleware_uri + "/api/services/app/Truckscales/Cancel"
            headers = {
                'Authorization': 'Bearer %s' % auth_response.get("result", {}).get("accessToken")
            }
            r = requests.post(url=cancel_url, headers=headers, json={"id": ts_id})
            r_json = r.json()
            if r_json.get('error'):
                raise ValueError("MiddleWare /app/Truckscales/Cancel error.")

        except Exception as e:
            _logger.error('Truckscale API connection error: %s', e)
            raise ValidationError("Truckscale Error. Please contact your administrator.")

    def delete_truckscale(self, ts_id):
        ir_config = self.env['ir.config_parameter'].sudo()
        middleware_uri = ir_config.get_param('middleware_api_uri')
        middleware_username = ir_config.get_param('middleware_api_username')
        middleware_password = ir_config.get_param('middleware_api_password')
        try:
            auth_url = middleware_uri + "/api/TokenAuth/Authenticate"
            data = {
                "UserNameOrEmailAddress": middleware_username,
                "Password": middleware_password
            }
            res = requests.post(auth_url, json=data)
            auth_response = res.json()
            if auth_response.get("error"):
                raise ValueError("MiddleWare Authenticate error.")
            delete_url = middleware_uri + f"/api/services/app/Truckscales/Delete?id={ts_id}"
            headers = {
                'Authorization': 'Bearer %s' % auth_response.get("result", {}).get("accessToken")
            }
            r = requests.delete(url=delete_url, headers=headers)
            r_json = r.json()
            if r_json.get('error'):
                raise ValueError("MiddleWare /app/Truckscales/Delete error.")

        except Exception as e:
            _logger.error('Truckscale API connection error: %s', e)
            raise ValidationError("Truckscale Error. Please contact your administrator.")

    def action_cancel(self):
        res = super(StockPicking, self).action_cancel()
        if not res:
            return res
        for record in self:
            if record.interface_truckscale_data and record.ts_id:
                record.cancel_truckscale(record.ts_id)
                record.clear_truckscale()
        return res

    def action_confirm(self):
        res = super().action_confirm()
        for rec in self:
            if rec.picking_type_id == rec.picking_type_id.warehouse_id.int_type_id and rec.location_id.warehouse_id != rec.location_dest_id.warehouse_id:
                rec.must_validate = True
        return res

    def action_first_validate(self):
        if not self.env.user.has_group('custom_stock.inventory_approval'):
            raise ValidationError(_('Only User Inventory Approval can Validate.'))
        self.first_validate = True

    def action_second_validate(self):
        if not self.env.user.has_group('custom_stock.inventory_manager_approval'):
            raise ValidationError(_('Only User Inventory Manager Approval can Validate.'))
        self.second_validate = True

    def button_validate(self):
        for rec in self:
            if rec.must_validate:
                if not rec.first_validate:
                    raise ValidationError(_('Inventory Approval must Validate before do this process.'))
                elif not rec.second_validate:
                    raise ValidationError(_('Inventory Manager Approval must Validate before do this process.'))
            if rec.picking_type_id == rec.picking_type_id.warehouse_id.int_type_id and rec.create_uid != rec.env.user:
                raise ValidationError(_('Only creator can Validate.'))
        return super().button_validate()

    def ceil(self, number1, number2):
        return math.ceil(number1 / number2)

    def write(self, vals):
        if 'ts_id' not in vals:
            return super(StockPicking, self).write(vals)
        if len(self) > 1:
            raise ValidationError("You can update 1 Truckscale at a time.")
        ori_ts_id = self.ts_id
        res = super(StockPicking, self).write(vals)
        if self.picking_type_id.set_done_by_weight and not self.set_done_by_weight:
            self.truckscale_update_quantity()
        if ori_ts_id:
            self.cancel_truckscale(ori_ts_id)
        self.delete_truckscale(self.ts_id)
        return res
