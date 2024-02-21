# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime, timedelta, timezone

class InventoryAccountReport(models.AbstractModel):
    _name = "inventory.account.report"
    _inherit = "account.report"
    _description = "Inventory Account Report"

    filter_date = {'mode': 'range', 'filter': 'this_year'}

    @api.model
    def _get_templates(self):
        templates = super(InventoryAccountReport, self)._get_templates()
        templates['main_template'] = 'account_reports.main_template_with_filter_input_accounts'
        return templates

    @api.model
    def _get_columns(self, options):
        header1 = [
            {'name': '', 'class': 'o_account_coa_column_contrast', 'colspan': 8},
            {'name': 'Balance', 'class': 'o_account_coa_column_contrast', 'colspan': 4},
        ]

        header2 = [
            {'name': 'Product', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Date', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Stock Move', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Journal Entry', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Unit Value', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Quantity', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Unit of Measure', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Total Value', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Quantity', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Unit Value', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Unit of Measure', 'class': 'o_account_coa_column_contrast'},
            {'name': 'Total Value', 'class': 'o_account_coa_column_contrast'},
        ]

        return [header1, header2]

    @api.model
    def _get_lines(self, options, line_id=None):

        lines = []
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])

        stock_valuation_ids = self.env['stock.valuation.layer'].search(
            [('create_date', '>=', date_from), ('create_date', '<=', date_to)], order='create_date asc')
        
        MAX_COLUMNS = 11
        group_product = {}
        for stock in stock_valuation_ids:

            if str(stock.product_id.id) not in group_product:
                group_product[str(stock.product_id.id)] = [stock]
            else:
                group_product[str(stock.product_id.id)] += [stock]
        
        for item in group_product:

            quantity_calculate = 0.0
            average_price = 0.0
            value_calculate = 0.0
            stock_valuation_ids = self.env['stock.valuation.layer'].search
            lines.append(self._get_title_line(options, item))

            for i, val in enumerate(group_product[item]):

            
                columns = []
                quantity_calculate += val.quantity
                value_calculate += val.value
                average_price = value_calculate/quantity_calculate if quantity_calculate != 0.0 else 0
                for i in range(MAX_COLUMNS):
                    tz = timezone(timedelta(hours=7))
                    new_time = val.create_date.astimezone(tz)
                    new_date = str(new_time).split('.')

                    #Date
                    if i == 0: columns.append({'name': new_date[0], 'class': 'number'})
                    #Stock Move
                    if i == 1: columns.append({'name': self.name_get(val.stock_move_id), 'class': 'number'})
                    #Journal Entry
                    if i == 2: columns.append({'name': val.account_move_id.name, 'class': 'number'})
                    #Unit Value
                    if i == 3: columns.append({'name': self.format_value(val.unit_cost), 'class': 'number'})
                    #Quantity
                    if i == 4: columns.append({'name': round(val.quantity, 2), 'class': 'number'})
                    #Unit of Measure
                    if i == 5: columns.append({'name': val.uom_id.name, 'class': 'number'})
                    #Total Value
                    if i == 6: columns.append({'name': self.format_value(val.value), 'class': 'number'})
                    #Balance Quantity
                    if i == 7: columns.append({'name': round(quantity_calculate, 2), 'class': 'number'})
                    #Balance Unit Value
                    if i == 8: columns.append({'name': self.format_value(average_price), 'class': 'number'})
                    #Balance Unit of Measure
                    if i == 9: columns.append({'name': val.uom_id.name, 'class': 'number'})
                    #Balance Total Value
                    if i == 10: columns.append({'name': self.format_value(value_calculate), 'class': 'number'})
                    

                lines.append({
                    'id': 'stock_%d' % val.id,
                    'class': 'o_account_reports_initial_balance',
                    'name': _('[%s] %s') % (val.product_id.default_code, val.product_id.name),
                    'parent_id': 'product_%d' % val.product_id.id,
                    'columns': columns,
                })

        return lines

    @api.model
    def _get_report_name(self):
        return _("Inventory Report")

    def name_get(self, stock_move_id):
        name = ('%s%s%s%s' % (
            stock_move_id.picking_id.origin and '%s/' % stock_move_id.picking_id.origin or '',
            stock_move_id.product_id.code and '%s: ' % stock_move_id.product_id.code or '',
            stock_move_id.location_id.name and '%s> ' % stock_move_id.location_id.name or '', 
            stock_move_id.location_dest_id.name or ''
        ))
            
        return name

    @api.model
    def _get_title_line(self, options, product_id):
        product = self.env['product.product'].search([('id', '=', product_id)])

        return {
            'id': 'product_%d' % product.id,
            'name': _('[%s] %s') % (product.default_code, product.name),
            'columns': [],
            'level': 1,
            'unfoldable': True,
            'unfolded': True and 'product_%d' % product.id in options.get('unfolded_lines'),
            'colspan': 11,
            'class': 'o_account_reports_totals_below_sections',
        }

