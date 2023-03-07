# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from datetime import datetime
from odoo.tools import pycompat
from odoo.tools.float_utils import float_round
import xlsxwriter

import logging
_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug('Cannot `import xlsxwriter`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ExportStockInfoWiz(models.TransientModel):
    _name = 'export.stock.info.wiz'
    _description = 'ExportStockInfoWiz'


    check_active = fields.Boolean('Active Products Only?')
    color_neg = fields.Boolean('Display Red Text For Negative Quantity')
    date_to = fields.Date('Date To')
    date_from = fields.Date('Date From')
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
    location_ids = fields.Many2many('stock.location', string="Location")
    cat_ids = fields.Many2many('product.category', string="Category")
    supp_ids = fields.Many2many('res.partner', string="Supplier")
    report_type = fields.Selection([('warehouse','Warehouse'),('location','Location')], default='warehouse', string='Generate Report Based on')
    document = fields.Binary('File To Download')
    file = fields.Char('Report File Name', readonly=1)

    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'company_owned', 'force_company',
    ) 

    @api.onchange('report_type')
    def on_change_designation(self):
        if self.report_type == 'warehouse':
            self.location_ids = False
        else:
            self.warehouse_ids = False

    # @api.multi
    def print_pdf_report(self):
        self.ensure_one()
        [data] = self.read()
        datas = {
             'ids': [1],
             'model': 'export.stock.info.wiz',
             'form': data
        }
        return self.env.ref('export_stock_info.action_report_export_stock_information').report_action(self, data=datas)

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
    def get_warehouse_details(self, data, warehouse):
        lines =[]
        end_date_data = data.get('date_to')
        start_date_data = data.get('date_from')
        category_ids = self.env['product.category'].browse(data.get('cat_ids'))
        supplier_ids = self.env['res.partner'].browse(data.get('supp_ids'))
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
                                                from_date = data.get('date_from'),
                                                to_date = data.get('date_to'))
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
                'product_active'     : product_id.active,
                'product_name'       : product_id.name or '',
                'product_code'       : product_id.default_code or '',
                'product_category'   : product_id.categ_id.name or '',
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
    def get_location_details(self, data, location_id):
        lines =[]
        end_date_data = data.get('date_to')
        start_date_data = data.get('date_from')
        category_ids = self.env['product.category'].browse(data.get('cat_ids'))
        supplier_ids = self.env['res.partner'].browse(data.get('supp_ids'))
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
        for product_id in product_ids:
            value  = {}
            res = self._compute_quantities_dict(product_id,
                                                lot_id = self._context.get('lot_id'),
                                                location_id = location_id, 
                                                from_date = data.get('date_from'),
                                                to_date = data.get('date_to'))
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
                'product_active'     : product_id.active,
                'product_name'       : product_id.name or '',
                'product_code'       : product_id.default_code or '',
                'product_category'   : product_id.categ_id.name or '',
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
    def print_excel_report(self):
        self.ensure_one()
        [data] = self.read()
        file_path = 'Export Stock Information' + '.xlsx'
        workbook = xlsxwriter.Workbook('/tmp/' + file_path)
        worksheet = workbook.add_worksheet('Export Stock Information')

        start_date = datetime.strptime(str(data.get('date_from', False)), '%Y-%m-%d').date()
        from_date = start_date.strftime('%d-%m-%Y')
        end_date = datetime.strptime(str(data.get('date_to', False)), '%Y-%m-%d').date()
        to_date = end_date.strftime('%d-%m-%Y')

        header_format = workbook.add_format({'bold': True,'valign':'vcenter','font_size':16,'align': 'center','bg_color':'#D8D8D8'})
        title_format = workbook.add_format({'border': 1,'bold': True, 'valign': 'vcenter','align': 'center', 'font_size':14,'bg_color':'#D8D8D8'})
        cell_wrap_format = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'left','font_size':12,}) ##E6E6E6
        cell_wrap_format_bold = workbook.add_format({'border': 1, 'bold': True,'valign':'vjustify','valign':'vcenter','align': 'center','font_size':12,'bg_color':'#D8D8D8'}) ##E6E6E6
        cell_wrap_format_amount = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,}) ##E6E6E6
        cell_wrap_format_qty_available = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ccffcc'}) ##E6E6E6
        cell_wrap_format_qty_incoming = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ffedcc'}) ##E6E6E6
        cell_wrap_format_qty_outgoing = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ffd9cc'}) ##E6E6E6
        cell_wrap_format_net_on_hand = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ccccff'}) ##E6E6E6
        cell_wrap_format_qty_forecasted = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#f2ccff'}) ##E6E6E6
        cell_wrap_format_space = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ffffcc'}) ##E6E6E6
        cell_wrap_format_negative = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ff0000'}) ##E6E6E6
        cell_wrap_format_qty_total = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ccffff'}) ##E6E6E6
        cell_wrap_format_qty_valuation = workbook.add_format({'border': 1,'valign':'vjustify','valign':'vcenter','align': 'right','font_size':12,'bg_color':'#ffcccc'}) ##E6E6E6

        worksheet.set_row(1,20)  #Set row height
        #Merge Row Columns
        TITLEHEDER = 'Export Stock Information' 
        worksheet.set_column(0, 5, 20)
        worksheet.set_column(6, 6, 2)
        worksheet.set_column(7, 10, 20)
        worksheet.set_column(11, 11, 2)
        worksheet.set_column(12, 13, 20)
        worksheet.set_column(14, 14, 2)
        worksheet.set_column(15, 15, 20)

        ware_obj = self.env['stock.warehouse']
        location_obj = self.env['stock.location']
        warehouse_ids = ware_obj.browse(data.get('warehouse_ids'))
        location_ids = location_obj.browse(data.get('location_ids'))
        worksheet.merge_range(1, 0, 1, 15, TITLEHEDER,header_format)
        rowscol = 1
        if warehouse_ids:
            for warehouse in warehouse_ids:
                # Report Title
                worksheet.merge_range((rowscol + 1), 0, (rowscol + 1), 2,'Report Date : ' + from_date + ' ' + '-' + ' ' + to_date, title_format)
                worksheet.merge_range((rowscol + 3), 0, (rowscol + 3), 5,'Product Information', title_format)
                worksheet.merge_range((rowscol + 3), 6, (rowscol + 3), 15, str(warehouse.name), title_format)
                # Report Content
                worksheet.write((rowscol + 5), 0, 'Status', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 1, 'Internal Reference', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 2, 'Product Name', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 3, 'Product Category', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 4, 'Cost Price', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 5, 'Available Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 6, '', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 7, 'Incoming Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 8, 'Outgoing Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 9, 'Net On Hand', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 10, 'Forecasted Stock', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 11, '', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 12, 'Total Sold Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 13, 'Total Purchase Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 14, '', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 15, 'Valuation', cell_wrap_format_bold)
                rows = (rowscol + 6)
                for record in self.get_warehouse_details(data, warehouse):
                    if record.get('product_active') == True:
                        worksheet.write(rows, 0,  'Active', cell_wrap_format)
                    else:
                        worksheet.write(rows, 0,  'Inactive', cell_wrap_format)
                    worksheet.write(rows, 1,  record.get('product_code'), cell_wrap_format)
                    worksheet.write(rows, 2,  record.get('product_name'), cell_wrap_format)
                    worksheet.write(rows, 3,  record.get('product_category'), cell_wrap_format)
                    worksheet.write(rows, 4,  str('%.2f' % record.get('standard_price')), cell_wrap_format_amount)
                    worksheet.write(rows, 5,  str('%.2f' % record.get('qty_available')), cell_wrap_format_qty_available)
                    worksheet.write(rows, 6,  '', cell_wrap_format_space)
                    worksheet.write(rows, 7,  str('%.2f' % record.get('incoming_qty')), cell_wrap_format_qty_incoming)
                    worksheet.write(rows, 8,  str('%.2f' % record.get('outgoing_qty')), cell_wrap_format_qty_outgoing)
                    if data.get('color_neg') == True:
                        if record.get('net_on_hand_qty') < 0.00:
                            worksheet.write(rows, 9, str('%.2f' % record.get('net_on_hand_qty')), cell_wrap_format_negative)
                        else:
                            worksheet.write(rows, 9, str('%.2f' % record.get('net_on_hand_qty')), cell_wrap_format_net_on_hand)
                    else:
                        worksheet.write(rows, 9, str('%.2f' % record.get('net_on_hand_qty')), cell_wrap_format_net_on_hand)
                    # Virtual Available
                    if data.get('color_neg') == True:
                        if record.get('virtual_available') < 0.00:
                            worksheet.write(rows, 10, str('%.2f' % record.get('virtual_available')), cell_wrap_format_negative)
                        else:
                            worksheet.write(rows, 10, str('%.2f' % record.get('virtual_available')), cell_wrap_format_qty_forecasted)
                    else:
                        worksheet.write(rows, 10, str('%.2f' % record.get('virtual_available')), cell_wrap_format_qty_forecasted)
                    worksheet.write(rows, 11, '', cell_wrap_format_space)
                    worksheet.write(rows, 12, str('%.2f' % record.get('total_sold_qty')), cell_wrap_format_qty_total)
                    worksheet.write(rows, 13, str('%.2f' % record.get('total_purchase_qty')), cell_wrap_format_qty_total)
                    worksheet.write(rows, 14, '', cell_wrap_format_space)
                    worksheet.write(rows, 15, str('%.2f' % record.get('value_svl')), cell_wrap_format_qty_valuation)
                    rows = rows+1
                rowscol = rows + 2
        else:
            for location in location_ids:
                location_name = str(location.location_id.name or '') + '/' + str(location.name or '') 
                # Report Title
                worksheet.merge_range((rowscol + 1), 0, (rowscol + 1), 2,'Report Date : ' + from_date + ' ' + '-' + ' ' + to_date, title_format)
                worksheet.merge_range((rowscol + 3), 0, (rowscol + 3), 5,'Product Information', title_format)
                worksheet.merge_range((rowscol + 3), 6, (rowscol + 3), 15, str(location_name), title_format)
                # Report Content
                worksheet.write((rowscol + 5), 0, 'Status', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 1, 'Internal Reference', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 2, 'Product Name', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 3, 'Product Category', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 4, 'Cost Price', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 5, 'Available Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 6, '', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 7, 'Incoming Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 8, 'Outgoing Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 9, 'Net On Hand', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 10, 'Forecasted Stock', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 11, '', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 12, 'Total Sold Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 13, 'Total Purchase Qty', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 14, '', cell_wrap_format_bold)
                worksheet.write((rowscol + 5), 15, 'Valuation', cell_wrap_format_bold)
                rows = (rowscol + 6)
                for record in self.get_location_details(data, location):
                    if record.get('product_active') == True:
                        worksheet.write(rows, 0,  'Active', cell_wrap_format)
                    else:
                        worksheet.write(rows, 0,  'Inactive', cell_wrap_format)
                    worksheet.write(rows, 1,  record.get('product_code'), cell_wrap_format)
                    worksheet.write(rows, 2,  record.get('product_name'), cell_wrap_format)
                    worksheet.write(rows, 3,  record.get('product_category'), cell_wrap_format)
                    worksheet.write(rows, 4,  str('%.2f' % record.get('standard_price')), cell_wrap_format_amount)
                    worksheet.write(rows, 5,  str('%.2f' % record.get('qty_available')), cell_wrap_format_qty_available)
                    worksheet.write(rows, 6,  '', cell_wrap_format_space)
                    worksheet.write(rows, 7,  str('%.2f' % record.get('incoming_qty')), cell_wrap_format_qty_incoming)
                    worksheet.write(rows, 8,  str('%.2f' % record.get('outgoing_qty')), cell_wrap_format_qty_outgoing)
                    if data.get('color_neg') == True:
                        if record.get('net_on_hand_qty') < 0.00:
                            worksheet.write(rows, 9, str('%.2f' % record.get('net_on_hand_qty')), cell_wrap_format_negative)
                        else:
                            worksheet.write(rows, 9, str('%.2f' % record.get('net_on_hand_qty')), cell_wrap_format_net_on_hand)
                    else:
                        worksheet.write(rows, 9, str('%.2f' % record.get('net_on_hand_qty')), cell_wrap_format_net_on_hand)
                    # Virtual Available
                    if data.get('color_neg') == True:
                        if record.get('virtual_available') < 0.00:
                            worksheet.write(rows, 10, str('%.2f' % record.get('virtual_available')), cell_wrap_format_negative)
                        else:
                            worksheet.write(rows, 10, str('%.2f' % record.get('virtual_available')), cell_wrap_format_qty_forecasted)
                    else:
                        worksheet.write(rows, 10, str('%.2f' % record.get('virtual_available')), cell_wrap_format_qty_forecasted)
                    worksheet.write(rows, 11, '', cell_wrap_format_space)
                    worksheet.write(rows, 12, str('%.2f' % record.get('total_sold_qty')), cell_wrap_format_qty_total)
                    worksheet.write(rows, 13, str('%.2f' % record.get('total_purchase_qty')), cell_wrap_format_qty_total)
                    worksheet.write(rows, 14, '', cell_wrap_format_space)
                    worksheet.write(rows, 15, str('%.2f' % record.get('value_svl')), cell_wrap_format_qty_valuation)
                    rows = rows+1
                rowscol = rows + 2

        workbook.close()
        buf = base64.b64encode(open('/tmp/' + file_path, 'rb+').read())
        self.document = buf
        self.file = 'Export Stock Information'+'.xlsx'
        return {
            'res_id': self.id,
            'name': 'Files to Download',
            'view_type': 'form',
            "view_mode": 'form,tree',
            'res_model': 'export.stock.info.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    # @api.multi
    def action_back(self):
        if self._context is None:
            self._context = {}
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'export.stock.info.wiz',
            'target': 'new',
        }
