# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import models, api,fields
from odoo.tools import pycompat
from odoo.tools.float_utils import float_round


class ExportStockInformationReport(models.AbstractModel):
    _name = 'report.export_stock_info.report_exportstockinformation' 
    _description = 'Stock Report'

    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'company_owned', 'force_company',
    ) 


    def _get_domain_locations(self, location_id, warehouse_id):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        Warehouse = self.env['stock.warehouse']

        if self.env.context.get('company_owned', False):
            company_id = self.env.user.company_id.id
            return (
                [('location_id.company_id', '=', company_id), ('location_id.usage', 'in', ['internal', 'transit'])],
                [('location_id.company_id', '=', False), ('location_dest_id.company_id', '=', company_id)],
                [('location_id.company_id', '=', company_id), ('location_dest_id.company_id', '=', False),
            ])
        location_ids = []
        if location_id:
            if isinstance(location_id.id, list):
                location_ids = [location_id.id]
            elif isinstance(location_id.id, list):
                domain = [('complete_name', 'ilike', location_id.id)]
                if self.env.context.get('force_company', False):
                    domain += [('company_id', '=', self.env.context['force_company'])]
                location_ids = self.env['stock.location'].search(domain).ids
            else:
                location_ids = location_id.id
        else:
            if warehouse_id:
                if isinstance(warehouse_id.id, list):
                    wids = [warehouse_id.id]
                elif isinstance(warehouse_id.id, list):
                    domain = [('name', 'ilike', warehouse_id.id)]
                    if self.env.context.get('force_company', False):
                        domain += [('company_id', '=', self.env.context['force_company'])]
                    wids = Warehouse.search(domain).ids
                else:
                    wids = warehouse_id.id
            else:
                wids = Warehouse.search([]).ids

            for w in Warehouse.browse(wids):
                location_ids.append(w.view_location_id.id)
        return self._get_domain_locations_new(location_ids, company_id=self.env.context.get('force_company', False), compute_child=self.env.context.get('compute_child', True))

    def _get_domain_locations_new(self, location_ids, company_id=False, compute_child=True):
        operator = compute_child and 'child_of' or 'in'
        domain = company_id and ['&', ('company_id', '=', company_id)] or []
        locations = self.env['stock.location'].browse(location_ids)
        # TDE FIXME: should move the support of child_of + auto_join directly in expression
        hierarchical_locations = locations if operator == 'child_of' else locations.browse()
        other_locations = locations - hierarchical_locations
        loc_domain = []
        dest_loc_domain = []
        # this optimizes [('location_id', 'child_of', hierarchical_locations.ids)]
        # by avoiding the ORM to search for children locations and injecting a
        # lot of location ids into the main query
        for location in hierarchical_locations:
            loc_domain = loc_domain and ['|'] + loc_domain or loc_domain
            loc_domain.append(('location_id.parent_path', '=like', location.parent_path + '%'))
            dest_loc_domain = dest_loc_domain and ['|'] + dest_loc_domain or dest_loc_domain
            dest_loc_domain.append(('location_dest_id.parent_path', '=like', location.parent_path + '%'))
        if other_locations:
            loc_domain = loc_domain and ['|'] + loc_domain or loc_domain
            loc_domain = loc_domain + [('location_id', operator, other_locations.ids)]
            dest_loc_domain = dest_loc_domain and ['|'] + dest_loc_domain or dest_loc_domain
            dest_loc_domain = dest_loc_domain + [('location_dest_id', operator, other_locations.ids)]
        return (
            domain + loc_domain,
            domain + dest_loc_domain + ['!'] + loc_domain if loc_domain else domain + dest_loc_domain,
            domain + loc_domain + ['!'] + dest_loc_domain if dest_loc_domain else domain + loc_domain
        )

    def _compute_quantities_dict(self, product_id, lot_id=False, owner_id=False, package_id=False, location_id=False , warehouse_id=False, from_date=False, to_date=False):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations(location_id, warehouse_id)
        domain_quant = [('product_id', 'in', [product_id.id])] + domain_quant_loc
        dates_in_the_past = False
        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)
        if to_date and to_date < fields.Datetime.now():
            dates_in_the_past = True

        domain_move_in = [('product_id', 'in', [product_id.id])] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', [product_id.id])] + domain_move_out_loc
        if lot_id is not None:
            domain_quant += [('lot_id', '=', lot_id)]
        if owner_id is not None:
            domain_quant += [('owner_id', '=', owner_id)]
            domain_move_in += [('restrict_partner_id', '=', owner_id)]
            domain_move_out += [('restrict_partner_id', '=', owner_id)]
        if package_id is not None:
            domain_quant += [('package_id', '=', package_id)]
        if dates_in_the_past:
            domain_move_in_done = list(domain_move_in)
            domain_move_out_done = list(domain_move_out)
        if from_date:
            domain_move_in += [('date', '>=', from_date)]
            domain_move_out += [('date', '>=', from_date)]
        if to_date:
            domain_move_in += [('date', '<=', to_date)]
            domain_move_out += [('date', '<=', to_date)]

        Move = self.env['stock.move']
        Quant = self.env['stock.quant']
        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        quants_res = dict((item['product_id'][0], item['quantity']) for item in Quant.read_group(domain_quant, ['product_id', 'quantity'], ['product_id'], orderby='id'))
        if dates_in_the_past:
            # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
            domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
            domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
            moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        res = dict()
        for product in [product_id.id]:
            product_id = product
            product = self.env['product.product'].browse(product_id)
            rounding = product.uom_id.rounding
            res[product_id] = {}
            if dates_in_the_past:
                qty_available = quants_res.get(product_id, 0.0) - moves_in_res_past.get(product_id, 0.0) + moves_out_res_past.get(product_id, 0.0)
            else:
                qty_available = quants_res.get(product_id, 0.0)
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)
        return res

    # @api.multi
    def _get_warehouse_details(self, data, warehouse):
        lines =[]
        if warehouse:
            end_date_data = data.get('end_date').date()
            start_date_data = data.get('start_date').date()
            category_ids = data.get('category_ids')
            supplier_ids = data.get('supplier_ids')
            check_active = data.get('check_active')

            # Active Product
            if check_active and not category_ids:
                product_ids = self.env['product.product'].search([('active','=', check_active)])
            # Category Vis Product
            elif category_ids and not check_active:
                product_ids = self.env['product.product'].search([('categ_id', 'in', category_ids.ids)])
            # Active and Category Vis Product
            elif check_active and category_ids:
                product_ids = self.env['product.product'].search([('active','=', check_active),
                                                                  ('categ_id', 'in', category_ids.ids)])
            # All Product
            else:
                product_ids = self.env['product.product'].search([])

            if not supplier_ids:
                supplier_ids = self.env['res.partner'].search([])

            move_ids =self.env['stock.move'].search([('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available','done')),
                                                    ('date','>=', start_date_data),
                                                    ('date','<=', end_date_data),
                                                    ('warehouse_id','=',warehouse.id),
                                                    ('product_id','in', product_ids.ids),
                                                    ('picking_id.partner_id','in', supplier_ids.ids)
                                                    ])
            product_ids=[]
            for stock_move in move_ids:
                if stock_move.product_id not in product_ids:
                    product_ids.append(stock_move.product_id)
            for product_id  in product_ids:
                value  = {}
                res = self._compute_quantities_dict(product_id,
                                                    lot_id = self._context.get('lot_id'),
                                                    warehouse_id = warehouse, 
                                                    from_date = data.get('start_date'),
                                                    to_date = data.get('end_date'))
                qty_available     = res.get(product_id.id).get('qty_available') or 0.0
                incoming_qty      = res.get(product_id.id).get('incoming_qty') or 0.0
                outgoing_qty      = res.get(product_id.id).get('outgoing_qty') or 0.0
                virtual_available = res.get(product_id.id).get('virtual_available') or 0.0
                net_on_hand_qty   = (qty_available - outgoing_qty) or 0.0
                # Total Sold Qty
                sale_order_line_ids = self.env['sale.order.line'].\
                                                        search([('state', 'in', ('sale','done')),
                                                                ('order_id.date_order','>=', start_date_data),
                                                                ('order_id.date_order','<=', end_date_data),
                                                                ('product_id','=', product_id.id),
                                                                ('order_id.picking_ids','!=', False)
                                                                ])
                total_sold_qty = 0.0
                for line in sale_order_line_ids:
                    total_sold_qty += line.product_uom_qty

                # Total Purchase Qty
                purchase_order_line_ids = self.env['purchase.order.line'].\
                                                        search([('state', 'in', ('purchase','done')),
                                                                ('order_id.date_order','>=', start_date_data),
                                                                ('order_id.date_order','<=', end_date_data),
                                                                ('product_id','=', product_id.id),
                                                                ('order_id.picking_ids','!=', False)
                                                                ])
                total_purchase_qty = 0.0
                for line in purchase_order_line_ids:
                    total_purchase_qty += line.product_qty

                value.update({
                    'product_id'         : product_id.id,
                    'product_name'       : product_id.name or '',
                    'product_code'       : product_id.default_code or '',
                    'standard_price'     : product_id.standard_price or 0.00,
                    'value_svl'          : product_id.value_svl or 0.00,

                    'uom'                : product_id.uom_id.name or '',
                    'qty_available'      : qty_available or 0.00,
                    'incoming_qty'       : incoming_qty or 0.00,
                    'outgoing_qty'       : outgoing_qty or 0.00,
                    'net_on_hand_qty'    : net_on_hand_qty or 0.00,
                    'virtual_available'  : virtual_available or 0.00,
                    'total_sold_qty'     : total_sold_qty or 0.00,
                    'total_purchase_qty' : total_purchase_qty or 0.00,
                })
                lines.append(value)
            return lines

    # @api.multi
    def _get_location_details(self, data, location_id):
        lines =[]
        if location_id:
            end_date_data = data.get('end_date').date()
            start_date_data = data.get('start_date').date()
            category_ids = data.get('category_ids')
            supplier_ids = data.get('supplier_ids')
            check_active = data.get('check_active')

            # Active Product
            if check_active and not category_ids:
                product_ids = self.env['product.product'].search([('active','=', check_active)])
            # Category Vis Product
            elif category_ids and not check_active:
                product_ids = self.env['product.product'].search([('categ_id', 'in', category_ids.ids)])
            # Active and Category Vis Product
            elif check_active and category_ids:
                product_ids = self.env['product.product'].search([('active','=', check_active),
                                                                  ('categ_id', 'in', category_ids.ids)])
            # All Product
            else:
                product_ids = self.env['product.product'].search([])

            if not supplier_ids:
                supplier_ids = self.env['res.partner'].search([])

            move_ids =self.env['stock.move'].search([('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available','done')),
                                                    ('date','>=', start_date_data),
                                                    ('date','<=', end_date_data),
                                                    ('product_id','in', product_ids.ids),
                                                    ('picking_id.partner_id','in', supplier_ids.ids),
                                                    '|',('location_id','=', location_id.id) , 
                                                    ('location_dest_id','=', location_id.id)
                                                    ])
            product_ids=[]
            for stock_move in move_ids:
                if stock_move.product_id not in product_ids:
                    product_ids.append(stock_move.product_id)
            for product_id  in product_ids:
                value  = {}
                res = self._compute_quantities_dict(product_id,
                                                    lot_id = self._context.get('lot_id'),
                                                    location_id = location_id,
                                                    from_date = data.get('start_date'),
                                                    to_date = data.get('end_date'))
                qty_available     = res.get(product_id.id).get('qty_available') or 0.0
                incoming_qty      = res.get(product_id.id).get('incoming_qty') or 0.0
                outgoing_qty      = res.get(product_id.id).get('outgoing_qty') or 0.0
                virtual_available = res.get(product_id.id).get('virtual_available') or 0.0
                net_on_hand_qty   = (qty_available - outgoing_qty) or 0.0
                # Total Sold Qty
                sale_order_line_ids = self.env['sale.order.line'].\
                                                        search([('state', 'in', ('sale','done')),
                                                                ('order_id.date_order','>=', start_date_data),
                                                                ('order_id.date_order','<=', end_date_data),
                                                                ('product_id','=', product_id.id),
                                                                ('order_id.picking_ids','!=', False)
                                                                ])
                total_sold_qty = 0.0
                for line in sale_order_line_ids:
                    total_sold_qty += line.product_uom_qty

                # Total Purchase Qty
                purchase_order_line_ids = self.env['purchase.order.line'].\
                                                        search([('state', 'in', ('purchase','done')),
                                                                ('order_id.date_order','>=', start_date_data),
                                                                ('order_id.date_order','<=', end_date_data),
                                                                ('product_id','=', product_id.id),
                                                                ('order_id.picking_ids','!=', False)
                                                                ])
                total_purchase_qty = 0.0
                for line in purchase_order_line_ids:
                    total_purchase_qty += line.product_qty

                value.update({
                    'product_id'         : product_id.id,
                    'product_name'       : product_id.name or '',
                    'product_code'       : product_id.default_code or '',
                    'standard_price'     : product_id.standard_price or 0.00,
                    'value_svl'          : product_id.value_svl or 0.00,

                    'uom'                : product_id.uom_id.name or '',
                    'qty_available'      : qty_available or 0.00,
                    'incoming_qty'       : incoming_qty or 0.00,
                    'outgoing_qty'       : outgoing_qty or 0.00,
                    'net_on_hand_qty'    : net_on_hand_qty or 0.00,
                    'virtual_available'  : virtual_available or 0.00,
                    'total_sold_qty'     : total_sold_qty or 0.00,
                    'total_purchase_qty' : total_purchase_qty or 0.00,
                }) 
                lines.append(value)
            return lines

    @api.model
    def _get_report_values(self, docids, data=None):
        end_date = data['form']['date_to']
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = data['form']['date_from']
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        location_ids  = self.env['stock.location'].browse(data['form']['location_ids'])
        warehouse_ids = self.env['stock.warehouse'].browse(data['form']['warehouse_ids'])
        supplier_ids = self.env['res.partner'].browse(data['form']['supp_ids'])
        category_ids = self.env['product.category'].browse(data['form']['cat_ids'])
        check_active = data['form']['check_active']
        color_neg    = data['form']['color_neg']
        date_to = datetime.strptime(data['form']['date_to'], "%Y-%m-%d").strftime("%d-%m-%Y")
        date_from = datetime.strptime(data['form']['date_from'], "%Y-%m-%d").strftime("%d-%m-%Y")
        data  = { 
            'end_date'      : end_date,
            'start_date'    : start_date,
            'date_to'       : date_to,
            'date_from'     : date_from,
            'warehouse_ids' : warehouse_ids,
            'location_ids'  : location_ids,
            'supplier_ids'  : supplier_ids,
            'category_ids'  : category_ids,
            'check_active'  : check_active,
            'color_neg'     : color_neg,
            }  
        docargs = {
                   'doc_model': 'export.stock.info.wiz',
                   'data': data,
                   'get_warehouse_details':self._get_warehouse_details,
                   'get_location_details' :self._get_location_details,
                   }
        return docargs
