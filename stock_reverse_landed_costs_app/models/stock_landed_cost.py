# -*- coding: utf-8 -*-

from odoo import fields, models, api, tools,_


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'
    _description = 'Stock Landed Cost'

    account_move_count = fields.Integer(string='Moves Count', compute='_get_account_moves', readonly=True)

    
    def _get_account_moves(self):
        move_obj = self.env['account.move']
        self.account_move_count = move_obj.search_count(['|',
                                                         ('ref', 'like', self.account_move_id.name),
                                                         ('id', 'in', self.account_move_id.ids)])

    
    def action_view_account_moves(self):
        xml_id = 'account.view_move_tree'
        tree_view_id = self.env.ref(xml_id).id
        xml_id = 'account.view_move_form'
        form_view_id = self.env.ref(xml_id).id
        return {
            'name': _('Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [(tree_view_id, 'tree'),
                      (form_view_id, 'form')],
            'res_model': 'account.move',
            'domain': ['|',
                       ('ref', 'like', self.account_move_id.name),
                       ('id', 'in', self.account_move_id.ids)],
            'type': 'ir.actions.act_window',
        }

    
    def button_cancel(self):
        for stock in self:
            
            if stock.account_move_id:
                stock.account_move_id.button_cancel()
                        
            for line in stock.valuation_adjustment_lines.filtered(lambda line: line.move_id):
                    

                remaining_qty = sum(line.move_id.stock_valuation_layer_ids.mapped('remaining_qty'))
                linked_layer = line.move_id.stock_valuation_layer_ids[:1]

                # Prorate the value at what's still in stock
                cost_to_add = (remaining_qty / line.move_id.product_qty) * line.additional_landed_cost
               
                if not stock.company_id.currency_id.is_zero(cost_to_add):
                    valuation_layer = self.env['stock.valuation.layer'].search([('stock_valuation_layer_id','=',linked_layer.id)],order="id desc", limit=1)

                    
                    valuation_layer.write({'value' :valuation_layer.value -cost_to_add  })
                    linked_layer.remaining_value -= cost_to_add
            
        
                line.unlink()
        return self.write({'state': 'cancel'})

    
    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel'])
        return orders.write({
            'state': 'draft',
        })
