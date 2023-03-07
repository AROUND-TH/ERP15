import logging

from odoo import models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def interface_middleware_get_bom_header_item(self, access_token):
        self.ensure_one()
        InterfaceMrp = self.env['middleware.mrp']
        query_string = "BomIdFilter=%s" % self.id
        response = InterfaceMrp.bom_headers_get_all(query=query_string, access_token=access_token)
        result = response.get("result")
        total_count = result.get("totalCount")
        if total_count > 1:
            raise ValidationError(_("Bom ID :  %s has more than 1 records in middleware", str(self.id)))
        return result.get("items")[0].get("bomHeader") if total_count == 1 else None

    def interface_middleware_bom_headers_create_or_edit(self, access_token, _id):
        self.ensure_one()
        InterfaceMrp = self.env['middleware.mrp']
        payload = {
            "bomId": self.id,
            "chgNo": self.ecm_no or "",
            "chgDate": self.ecm_date.strftime("%d/%m/%Y") if self.ecm_date else "",
            "plant": self.picking_type_id.warehouse_id.code,
            "materialCode": self.product_tmpl_id.default_code,
            "materialName": self.product_tmpl_id.name,
            "bomStatus": "Active" if self.active else "",
            "baseQuan": float(self.product_qty),
            "baseUnit": self.product_uom_id.name or "",
            "flagRead": "N",
            "shelfLifeDay": str(self.product_tmpl_id.expiration_time) or "",
            "reference": self.code or "",
            "productionType": self.production_type or ""
        }
        if _id:
            payload.update({"id": _id})

        return InterfaceMrp.bom_headers_create_or_edit(payload=payload, access_token=access_token)

    def interface_middleware_bom_items(self, access_token):
        InterfaceMrp = self.env['middleware.mrp']
        self.ensure_one()
        for bom_line in self.bom_line_ids.filtered(lambda l: l.product_id.default_code != "OH Cost"):
            query_string = "BomIdFilter=%s&ItemIdFilter=%s" % (self.id, bom_line.id)
            response = InterfaceMrp.bom_items_get_all(query=query_string, access_token=access_token)
            result = response.get("result")
            total_items = result.get("totalCount")
            if total_items > 1:
                raise ValidationError(
                    _("Bom Item ID :  %s has more than 1 records in middleware", str(self.id)))
            payload = {
                "bomId": self.id,
                "chgNo": self.ecm_no or "",
                "itemId": bom_line.id,
                "componentCode": bom_line.product_id.default_code,
                "componentName": bom_line.product_id.name,
                "compQty": float(bom_line.product_qty) or 0.00000,
                "compUnit": bom_line.product_uom_id.name,
                "compType": bom_line.bom_line_type or "",
                "convertionQty": bom_line.convertion_quantity,
                "flagRead": "N",
            }
            if total_items == 1:
                item = result.get("items")[0].get("bomItem")
                if item.get('flagRead') == "Y":
                    continue
                payload.update({"id": item.get("id")})

            InterfaceMrp.bom_items_create_or_edit(payload=payload, access_token=access_token)

    def action_interface_middleware(self):
        access_token = self.env['middleware.mrp'].get_middleware_token()
        flag_read_list = list()
        todos = list()
        for rec in self:
            item = rec.interface_middleware_get_bom_header_item(access_token)
            if not item or item.get('flagRead') == "N":
                _id = item.get('id') if item else None
                todos.append({'rec': rec, 'id': _id})
            else:
                flag_read_list.append(rec)

        if flag_read_list:
            message = ""
            for rec in flag_read_list:
                if rec.ecm_no:
                    message += f"{rec.product_tmpl_id.display_name} (ECM No. {rec.ecm_no}) already Used.\n"
                else:
                    message += f"{rec.product_tmpl_id.display_name} already Used.\n"
            wizard_message_id = self.env['wizard.success.message'].create({'message': message})
            return {
                'name': 'Error',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'wizard.success.message',
                'res_id': wizard_message_id.id,
                'target': 'new'
            }

        for todo in todos:
            rec, _id = todo.get('rec'), todo.get('id')
            rec.interface_middleware_bom_headers_create_or_edit(access_token, _id)
            rec.interface_middleware_bom_items(access_token)

        wizard_message_id = self.env['wizard.success.message'].create({'message': 'Interface bom completed.'})
        return {
            'name': 'Success',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.success.message',
            'res_id': wizard_message_id.id,
            'target': 'new'
        }
