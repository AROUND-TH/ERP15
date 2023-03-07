# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, date, time, timedelta
from odoo.exceptions import UserError


class MrpDemandAdjustment(models.TransientModel):
    _name = "mrp.demand.adjustment"
    _description = "MRP Demand Adjustment"

    mrp_parameter_ids = fields.Many2many('mrp.parameter', string='MRP Planning Parameters')
    all_mrp_parameters = fields.Boolean('All MRP Planning Parameters')
    cleaning_date = fields.Datetime('Cleaning Date', required=True)


    def action_demand_adjustment_run(self):
        messages = self.demand_adjustment_run()
        t_mess_id = False
        if messages:
            out_message = ''
            for message in messages:
                out_message += '\n' + message
                t_mess_id = self.env["mrp.demand.adjustment.message"].create({'name': out_message}).id
        else:
            t_mess_id = self.env["mrp.demand.adjustment.message"].create({'name': 'no demand item has been archived'}).id
        return {
            'name': _('Demand Adjustment Run Results'),
            "view_mode": 'form',
            'res_model': "mrp.demand.adjustment.message",
            'res_id': t_mess_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def demand_adjustment_run(self):
        parameters_ids = False
        messages = []
        if not self.mrp_parameter_ids and not self.all_mrp_parameters:
            raise UserError(_('select a MRP Parameter at least or set All MRP Planning Parameters indicator either'))
        if self.mrp_parameter_ids and self.all_mrp_parameters:
            raise UserError(_('select a MRP Parameter at least or set All MRP Planning Parameters indicator either'))
        if self.all_mrp_parameters:
            parameters_ids = self.env['mrp.parameter'].search([])
        else:
            parameters_ids = self.env['mrp.parameter'].search([('id', 'in', self.mrp_parameter_ids.ids)])
        for parameter in parameters_ids:
            demand_items = self.env['mrp.demand'].search([('mrp_parameter_id', '=', parameter.id),('date_planned', '<', self.cleaning_date)])
            if demand_items:
                demand_items.write({'active': False})
                count_demand_items = str(len(demand_items))
            else:
                count_demand_items = "0"
            message = parameter.warehouse_id.name + "-" + parameter.product_id.name + ":" + " archived demand items: " + count_demand_items
            if message:
                messages.append(message)
        return messages


class MrpDemandAdjustmentMessage(models.TransientModel):
    _name = "mrp.demand.adjustment.message"
    _description = "MRP Demand Adjustment Message"

    name = fields.Text('Result', readonly=True)