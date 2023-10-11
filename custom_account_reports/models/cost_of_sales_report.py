# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
import copy
from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta
from odoo.addons.custom_account_reports.models.data_item import COLUMNS_SALES_ITEM, COLUMNS_PRODUCTION_COST_ITEM

import logging
_logger = logging.getLogger(__name__)

class ReportCostOfSales(models.AbstractModel):
    _name = "cost.sales.report"
    _inherit = "account.report"
    _description = "Cost Of Sales Report"

    filter_date = {'mode': 'range', 'filter': 'this_month'}
    filter_comparison = {'date_from': '', 'date_to': '', 'filter': 'no_comparison', 'number_period': 1}

    @api.model
    def _get_templates(self):
        templates = super(ReportCostOfSales, self)._get_templates()
        templates['main_template'] = 'account_reports.main_template_with_filter_input_accounts'
        return templates

    @api.model
    def _get_columns(self, options):

        header1 = [ 
            {'name': '', 'class': 'o_account_coa_column_contrast', 'style': 'width:10%'},
            {'name':_('บริษัท บลูฟาโล่ เพ็ทแคร์ จำกัด'), 'class': 'o_account_coa_column_contrast', 'style': 'width:15%' },
            {'name': '', 'class': 'o_account_coa_column_contrast',},
        ]

        header2 = [ 
            {'name': '', 'class': 'o_account_coa_column_contrast', 'style': 'width:10%'},
            {'name':_('งบต้นทุนขาย'), 'class': 'o_account_coa_column_contrast', 'style': 'width:15%' },
            {'name': '', 'class': 'o_account_coa_column_contrast',},
        ]

        header3 = [
            {'name': '', 'class': 'o_account_coa_column_contrast', 'style': 'width:10%'},
            {'name': 'สำหรับสิ้นสุดวันที่ %s' %(options['date']['string']), 'class': 'o_account_coa_column_contrast', 'style': 'width:15%' },
            {'name': '', 'class': 'o_account_coa_column_contrast',},
        ]

        if options.get('comparison') and options['comparison'].get('periods'):
            header1 += [
                {'name': '', 'class': 'o_account_coa_column_contrast',},
            ] * len(options['comparison']['periods'])

            header2 += [
                {'name': '', 'class': 'o_account_coa_column_contrast',},
            ] * len(options['comparison']['periods'])

            header3 += [
                {'name': '', 'class': 'o_account_coa_column_contrast',},
            ] * len(options['comparison']['periods'])

        return [header1, header2, header3]

    @api.model
    def _copy_options(self, options):
        new_options = copy.deepcopy(options)

        date_from = new_options[0]['date']['date_from'].split('-')
        date_to = new_options[0]['date']['date_to'].split('-')

        last_month = int(date_from[1])
        last_year = int(date_from[0])

        if last_month > 1:
            last_month -= 1
        else:
            last_month = 12
            last_year -= 1

        end_of_month = calendar.monthrange(last_year, last_month)[1]

        str_last_month = '0' + str(last_month) if last_month < 10 else str(last_month)

        last_from = str(last_year) + '-' +  str_last_month + '-' + date_from[2]
        last_to = str(last_year) + '-' +  str_last_month + '-' + str(end_of_month)

        new_options[0]['date']['date_from'] = last_from
        new_options[0]['date']['date_to'] = last_to

        return new_options

    @api.model
    def _get_total_balance(self, options, group_ids, type, line_id=None):
        date_to = fields.Date.from_string(options[0]['date']['date_to'])
        date_from = fields.Date.from_string(options[0]['date']['date_from'])

        expanded_account = line_id and self.env['account.account'].browse(int(line_id[8:]))
        accounts_results, taxes_results = self._do_query(options, expanded_account=expanded_account)
        
        total_debit = total_credit = total_balance = 0.0
        for account, periods_results in accounts_results:
            results = periods_results[0]

            account_sum = results.get('sum', {})
            account_un_earn = results.get('unaffected_earnings', {})
            
            debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
            credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
            balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
            
            if type in ['A', 'F'] and account.id in group_ids.ids and \
                account.user_type_id.id == self.env.ref('account.data_account_type_current_assets').id:

                total_debit += debit
                total_credit += credit
                total_balance += balance

            elif type in ['D'] and account.id in group_ids.ids and \
                account.user_type_id.id == self.env.ref('account.data_account_type_current_assets').id:

                aml_obj = self.env['account.move.line']
                domain = [('account_id', '=', account.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('move_id.state', 'in', ['posted']),
                ]

                move_lines = aml_obj.search(domain)
                m_debit = sum((move.debit) for move in move_lines)
                m_credit = sum((move.credit) for move in move_lines)
                m_balance = m_debit - m_credit

                total_debit += m_debit
                total_credit += m_credit
                total_balance += m_balance

        return total_debit, total_credit, total_balance

    @api.model
    def _get_lines(self, options, line_id=None):
        new_options = options.copy()
        new_options['unfold_all'] = True
        options_list = self._get_options_periods_list(new_options)

        company_currency = self.env.company.currency_id

        lines = []
        type_a = [0.0] * (len(options_list))
        type_b = [0.0] * (len(options_list))
        type_d = [0.0] * (len(options_list))
        type_e = [0.0] * (len(options_list))
        type_f = [0.0] * (len(options_list))
        type_g = [0.0] * (len(options_list))

        for col in COLUMNS_SALES_ITEM:

            columns = [{}] * (len(options_list) + 1)
            columns[0] = {'name': col['children'], 'class': 'o_account_coa_column_contrast', 'style': 'width:10%'}
            group_account_ids = self.env['setting.cost.sales'].search([])

            for i, option in enumerate(options_list):
                if col['type'] == 'A':
                    
                    copy_options = self._copy_options([option])
                    total_debit, total_credit, total_balance = self._get_total_balance(copy_options, group_account_ids.group_account_inventories_start_ids, col['type'], line_id)
                    columns[i+1] = {'name': self.format_value(company_currency.round(total_balance)), 'class': 'number o_account_coa_column_contrast'}
                    type_a[i] += round(total_balance, 2)

                elif col['type'] == 'B':

                    total = self._get_production_cost(option, line_id)
                    columns[i+1] = {'name': self.format_value(company_currency.round(total)), 'class': 'number o_account_coa_column_contrast'}
                    type_b[i] += round(total, 2)
                
                elif col['type'] == 'D':

                    total_debit, total_credit, total_balance = self._get_total_balance([option], group_account_ids.group_account_finished_goods_ids, col['type'], line_id)
                    columns[i+1] = {'name': self.format_value(company_currency.round(total_debit)), 'class': 'number o_account_coa_column_contrast'}
                    type_d[i] += round(total_debit, 2)

                elif col['type'] == 'E':

                    total = type_a[i] + type_b[i] + type_d[i]
                    columns[i+1] = {'name': self.format_value(company_currency.round(total)), 'class': 'number o_account_coa_column_contrast'}
                    type_e[i] += round(total, 2)

                elif col['type'] == 'F':

                    total_debit, total_credit, total_balance = self._get_total_balance([option], group_account_ids.group_account_inventories_end_ids, col['type'], line_id)
                    columns[i+1] = {'name': self.format_value(company_currency.round(total_balance)), 'class': 'number o_account_coa_column_contrast'}
                    type_f[i] += round(total_balance, 2)

                elif col['type'] == 'G':

                    columns[i+1] = {'name': self.format_value(company_currency.round(type_e[i] - type_f[i])), 'class': 'number o_account_coa_column_contrast'}
                    type_g[i] += round(type_e[i] - type_f[i], 2)

                else:
                    columns[i+1] = {'name': option['date']['string'], 'class': 'number o_account_coa_column_contrast'}

            lines.append({
                'id': col['name'] + ' ' + col['children'],
                'name': col['name'],
                'columns': columns,
                'class': 'o_account_coa_column_contrast',
            })

        return lines

    @api.model
    def _get_report_name(self):
        return _("งบต้นทุนขาย")

    @api.model
    def _get_total_production_cost(self, options, group_ids, type, line_id=None):
        date_from = fields.Date.from_string(options[0]['date']['date_from'])
        date_to = fields.Date.from_string(options[0]['date']['date_to'])

        expanded_account = line_id and self.env['account.account'].browse(int(line_id[8:]))
        accounts_results, taxes_results = self._do_query(options, expanded_account=expanded_account)
        
        assets_list = []
        total_debit = total_credit = total_balance = 0.0
        for account, periods_results in accounts_results:
            results = periods_results[0]

            account_sum = results.get('sum', {})
            account_un_earn = results.get('unaffected_earnings', {})
            
            # Check if there is sub-lines for the current period.
            max_date = account_sum.get('max_date')
            has_lines = max_date and max_date >= date_from or False
            

            debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
            credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
            balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
            
            if type in ['A', 'E'] and account.id in group_ids.ids and \
                account.user_type_id.id == self.env.ref('account.data_account_type_current_assets').id:

                total_debit += debit
                total_credit += credit
                total_balance += balance

            elif type in ['K', 'M'] and account.id in group_ids.ids and \
                account.user_type_id.id == self.env.ref('account.data_account_type_current_assets').id:

                total_debit += debit
                total_credit += credit
                total_balance += balance

            elif type in ['B'] and account.id in group_ids.ids and \
                account.user_type_id.id == self.env.ref('account.data_account_type_current_assets').id:
                
                aml_obj = self.env['account.move.line']
                domain = [('account_id', '=', account.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('move_id.state', 'in', ['posted']),
                ]

                move_lines = aml_obj.search(domain)
                m_debit = sum((move.debit) for move in move_lines)
                m_credit = sum((move.credit) for move in move_lines)
                m_balance = m_debit - m_credit

                total_debit += m_debit
                total_credit += m_balance
                total_balance += m_balance

                assets_list.append({
                    'name': account.code + ' ' + account.name,
                    'debit': m_debit,
                    'credit': m_credit,
                    'balance': m_balance,
                })

            elif type in ['H', 'G'] and has_lines and account.id in group_ids.ids \
                and account.user_type_id.id == self.env.ref('account.data_account_type_expenses').id:

                aml_obj = self.env['account.move.line']
                domain = [('account_id', '=', account.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('move_id.state', 'in', ['posted']),
                ]

                move_lines = aml_obj.search(domain)
                h_debit = sum((move.debit) for move in move_lines)
                h_credit = sum((move.credit) for move in move_lines)
                h_balance = h_debit - h_credit

                total_debit += h_debit
                total_credit += h_credit
                total_balance += h_balance

        return total_debit, total_credit, total_balance, assets_list

    @api.model
    def _get_production_cost(self, option, line_id=None):

        value_a = value_b = value_d = value_e = value_f = value_g = value_h = value_i = value_j = value_k = value_l = value_m = value_n = 0.0
        for col in COLUMNS_PRODUCTION_COST_ITEM:

            group_production_account_ids = self.env['setting.production.cost'].search([])
            if col['type'] == 'A':

                copy_options = self._copy_options([option])
                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost(copy_options, group_production_account_ids.group_account_raw_mate_ids, col['type'], line_id)
                value_a += round(total_balance, 2)

            elif col['type'] == 'B':

                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost([option], group_production_account_ids.group_account_raw_mate_ids, col['type'], line_id)
                value_b += round(total_debit, 2)

            elif col['type'] == 'D':

                value_d += round((value_a + value_b), 2)

            elif col['type'] == 'E':

                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost([option], group_production_account_ids.group_account_raw_mate_ids, col['type'], line_id)
                value_e += round(total_balance, 2)

            elif col['type'] == 'F':

                value_f += round((value_d - value_e), 2)

            elif col['type'] == 'G':

                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost([option], group_production_account_ids.group_account_direct_labor_ids, col['type'], line_id, )
                value_g += round(total_balance, 2)

            elif col['type'] == 'H':
                
                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost([option], group_production_account_ids.group_account_production_ids, col['type'], line_id, )
                value_h += round(total_balance, 2)

            elif col['type'] == 'I':

                value_i += round((value_h + value_g), 2)

            elif col['type'] == 'J':

                value_j += round((value_f + value_i), 2)

            elif col['type'] == 'K':

                copy_options = self._copy_options([option])
                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost(copy_options, group_production_account_ids.group_account_start_progress_ids, col['type'], line_id)
                value_k += round(total_balance, 2)

            elif col['type'] == 'L':

                value_l += round((value_j + value_k), 2)

            elif col['type'] == 'M':

                total_debit, total_credit, total_balance, assets_list = self._get_total_production_cost([option], group_production_account_ids.group_account_end_progress_ids, col['type'], line_id)
                value_m += round(total_balance, 2)

            elif col['type'] == 'N':
                
                value_n += round((value_l - value_m), 2)

        return value_n

    @api.model
    def _force_strict_range(self, options):
        ''' Duplicate options with the 'strict_range' enabled on the filter_date.
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options['date'] = new_options['date'].copy()
        new_options['date']['strict_range'] = True
        return new_options

    @api.model
    def _get_filter_accounts_domain(self, options, prefix=''):
        if options.get('filter_accounts'):
            account_name_label = 'name'
            account_code_label = 'code'
            if prefix:
                account_name_label = '%s.%s' % (prefix, account_name_label)
                account_code_label = '%s.%s' % (prefix, account_code_label)
            return [
                '|',
                (account_name_label, 'ilike', options['filter_accounts']),
                (account_code_label, 'ilike', options['filter_accounts'])
            ]
        return []

    @api.model
    def _get_options_domain(self, options):
        # OVERRIDE
        domain = super(ReportCostOfSales, self)._get_options_domain(options)
        # Filter accounts based on the search bar.
        domain += self._get_filter_accounts_domain(options, 'account_id')
        return domain

    @api.model
    def _get_options_sum_balance(self, options):
        ''' Create options used to compute the aggregated sums on accounts.
        The resulting dates domain will be:
        [
            ('date' <= options['date_to']),
            '|',
            ('date' >= fiscalyear['date_from']),
            ('account_id.user_type_id.include_initial_balance', '=', True)
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(new_options['date']['date_from']))
        new_options['date'] = {
            'mode': 'range',
            'date_from': fiscalyear_dates['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': options['date']['date_to'],
        }
        return new_options

    @api.model
    def _get_options_unaffected_earnings(self, options):
        ''' Create options used to compute the unaffected earnings.
        The unaffected earnings are the amount of benefits/loss that have not been allocated to
        another account in the previous fiscal years.
        The resulting dates domain will be:
        [
          ('date' <= fiscalyear['date_from'] - 1),
          ('account_id.user_type_id.include_initial_balance', '=', False),
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options.pop('filter_accounts', None)
        fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))
        new_date_to = fiscalyear_dates['date_from'] - timedelta(days=1)
        new_options['date'] = {
            'mode': 'single',
            'date_to': new_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
        }
        return new_options

    @api.model
    def _get_options_initial_balance(self, options):
        ''' Create options used to compute the initial balances.
        The initial balances depict the current balance of the accounts at the beginning of
        the selected period in the report.
        The resulting dates domain will be:
        [
            ('date' <= options['date_from'] - 1),
            '|',
            ('date' >= fiscalyear['date_from']),
            ('account_id.user_type_id.include_initial_balance', '=', True)
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))
        new_date_to = fields.Date.from_string(new_options['date']['date_from']) - timedelta(days=1)
        new_options['date'] = {
            'mode': 'range',
            'date_from': fiscalyear_dates['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': new_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
        }
        return new_options

    @api.model
    def _get_query_amls(self, options, expanded_account, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_account:    The account.account record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''

        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._force_strict_range(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        query = f'''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                account_move_line__move_id.name         AS move_name,
                company.currency_id                     AS company_currency_id,
                partner.name                            AS partner_name,
                account_move_line__move_id.move_type    AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name,
                full_rec.name                           AS full_rec_name
            FROM {tables}
            LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company               ON company.id = account_move_line.company_id
            LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
            LEFT JOIN account_account account           ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
            LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
            WHERE {where_clause}
            ORDER BY account_move_line.date, account_move_line.id
        '''

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params

    @api.model
    def _do_query(self, options_list, expanded_account=None, fetch_lines=True):
        ''' Execute the queries, perform all the computation and return (accounts_results, taxes_results). Both are
        lists of tuple (record, fetched_values) sorted by the table's model _order:
        - accounts_values: [(record, values), ...] where
            - record is an account.account record.
            - values is a list of dictionaries, one per period containing:
                - sum:                              {'debit': float, 'credit': float, 'balance': float}
                - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
                - (optional) lines:                 [line_vals_1, line_vals_2, ...]
        - taxes_results: [(record, values), ...] where
            - record is an account.tax record.
            - values is a dictionary containing:
                - base_amount:  float
                - tax_amount:   float
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :param fetch_lines:         A flag to fetch the account.move.lines or not (the 'lines' key in accounts_values).
        :return:                    (accounts_values, taxes_results)
        '''
        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(options_list, expanded_account=expanded_account)

        groupby_accounts = {}
        groupby_companies = {}
        groupby_taxes = {}

        self.env.cr.execute(query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            i = res['period_number']
            key = res['key']
            if key == 'sum':
                groupby_accounts.setdefault(res['groupby'], [{} for n in range(len(options_list))])
                groupby_accounts[res['groupby']][i][key] = res
            elif key == 'initial_balance':
                groupby_accounts.setdefault(res['groupby'], [{} for n in range(len(options_list))])
                groupby_accounts[res['groupby']][i][key] = res
            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(res['groupby'], [{} for n in range(len(options_list))])
                groupby_companies[res['groupby']][i] = res
            elif key == 'base_amount' and len(options_list) == 1:
                groupby_taxes.setdefault(res['groupby'], {})
                groupby_taxes[res['groupby']][key] = res['balance']
            elif key == 'tax_amount' and len(options_list) == 1:
                groupby_taxes.setdefault(res['groupby'], {})
                groupby_taxes[res['groupby']][key] = res['balance']

        # Fetch the lines of unfolded accounts.
        # /!\ Unfolding lines combined with multiple comparisons is not supported.
        if fetch_lines and len(options_list) == 1:
            options = options_list[0]
            unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
            if expanded_account or unfold_all or options['unfolded_lines']:
                query, params = self._get_query_amls(options, expanded_account)
                self.env.cr.execute(query, params)
                for res in self._cr.dictfetchall():
                    groupby_accounts[res['account_id']][0].setdefault('lines', [])
                    groupby_accounts[res['account_id']][0]['lines'].append(res)

        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        if groupby_companies:
            options = options_list[0]
            unaffected_earnings_type = self.env.ref('account.data_unaffected_earnings')
            search_domain = [('user_type_id', '=', unaffected_earnings_type.id),
                             ('company_id', 'in', list(groupby_companies.keys()))] + self._get_filter_accounts_domain(options)

            candidates_accounts = self.env['account.account'].search(search_domain)
            for account in candidates_accounts:
                company_unaffected_earnings = groupby_companies.get(account.company_id.id)
                if not company_unaffected_earnings:
                    continue
                for i in range(len(options_list)):
                    unaffected_earnings = company_unaffected_earnings[i]
                    groupby_accounts.setdefault(account.id, [{} for i in range(len(options_list))])
                    groupby_accounts[account.id][i]['unaffected_earnings'] = unaffected_earnings
                del groupby_companies[account.company_id.id]

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.
        if expanded_account:
            accounts = expanded_account
        elif groupby_accounts:
            accounts = self.env['account.account'].search([('id', 'in', list(groupby_accounts.keys()))])
        else:
            accounts = []
        accounts_results = [(account, groupby_accounts[account.id]) for account in accounts]

        # Fetch as well the taxes.
        if groupby_taxes:
            taxes = self.env['account.tax'].search([('id', 'in', list(groupby_taxes.keys()))])
        else:
            taxes = []
        taxes_results = [(tax, groupby_taxes[tax.id]) for tax in taxes]
        return accounts_results, taxes_results

    ####################################################
    # COLUMN/LINE HELPERS
    ####################################################

    @api.model
    def _get_query_sums(self, options_list, expanded_account=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        options = options_list[0]
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================

        domain = [('account_id', '=', expanded_account.id)] if expanded_account else []

        for i, options_period in enumerate(options_list):

            # The period domain is expressed as:
            # [
            #   ('date' <= options['date_to']),
            #   '|',
            #   ('date' >= fiscalyear['date_from']),
            #   ('account_id.user_type_id.include_initial_balance', '=', True),
            # ]

            new_options = self._get_options_sum_balance(options_period)
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            params += where_params
            queries.append('''
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS period_number,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM %s
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                WHERE %s
                GROUP BY account_move_line.account_id
            ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 2) Get sums for the unaffected earnings.
        # ============================================

        domain = [('account_id.user_type_id.include_initial_balance', '=', False)]
        if expanded_account:
            domain.append(('company_id', '=', expanded_account.company_id.id))

        # Compute only the unaffected earnings for the oldest period.

        i = len(options_list) - 1
        options_period = options_list[-1]

        # The period domain is expressed as:
        # [
        #   ('date' <= fiscalyear['date_from'] - 1),
        #   ('account_id.user_type_id.include_initial_balance', '=', False),
        # ]

        new_options = self._get_options_unaffected_earnings(options_period)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.company_id                            AS groupby,
                'unaffected_earnings'                                   AS key,
                NULL                                                    AS max_date,
                %s                                                      AS period_number,
                COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.company_id
        ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 3) Get sums for the initial balance.
        # ============================================

        domain = []
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif not unfold_all and options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        for i, options_period in enumerate(options_list):

            # The period domain is expressed as:
            # [
            #   ('date' <= options['date_from'] - 1),
            #   '|',
            #   ('date' >= fiscalyear['date_from']),
            #   ('account_id.user_type_id.include_initial_balance', '=', True)
            # ]

            new_options = self._get_options_initial_balance(options_period)
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            params += where_params
            queries.append('''
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'initial_balance'                                       AS key,
                    NULL                                                    AS max_date,
                    %s                                                      AS period_number,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM %s
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                WHERE %s
                GROUP BY account_move_line.account_id
            ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 4) Get sums for the tax declaration.
        # ============================================

        journal_options = self._get_options_journals(options)
        if not expanded_account and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            for i, options_period in enumerate(options_list):
                tables, where_clause, where_params = self._query_get(options_period)
                params += where_params + where_params
                queries += ['''
                    SELECT
                        tax_rel.account_tax_id                  AS groupby,
                        'base_amount'                           AS key,
                        NULL                                    AS max_date,
                        %s                                      AS period_number,
                        0.0                                     AS amount_currency,
                        0.0                                     AS debit,
                        0.0                                     AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM account_move_line_account_tax_rel tax_rel, %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE account_move_line.id = tax_rel.account_move_line_id AND %s
                    GROUP BY tax_rel.account_tax_id
                ''' % (i, tables, ct_query, where_clause), '''
                    SELECT
                    account_move_line.tax_line_id               AS groupby,
                    'tax_amount'                                AS key,
                        NULL                                    AS max_date,
                        %s                                      AS period_number,
                        0.0                                     AS amount_currency,
                        0.0                                     AS debit,
                        0.0                                     AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE %s
                    GROUP BY account_move_line.tax_line_id
                ''' % (i, tables, ct_query, where_clause)]

        return ' UNION ALL '.join(queries), params
