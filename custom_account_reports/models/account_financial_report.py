# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"


    # @Override odoo core method _display_debug_info
    # For change check by debug mode to check by Accounting Advisor
    @api.model
    def _display_debug_info(self, options):
        ''' Helper determining if the debug info popup column should be displayed or not.
        :param options: The report options.
        :return:        A boolean.
        '''
        return not self._context.get('print_mode') and self.user_has_groups('account.group_account_manager') \
               and (not options.get('comparison') or not options['comparison'].get('periods'))


    # @Override odoo core method _get_financial_line_report_line
    # For change check by debug mode to check by Accounting Advisor
    @api.model
    def _get_financial_line_report_line(self, options, financial_line, solver, groupby_keys):
        ''' Create the report line for an account.financial.html.report.line record.
        :param options:             The report options.
        :param financial_line:      An account.financial.html.report.line record.
        :param solver_results:      An instance of the FormulaSolver class.
        :param groupby_keys:        The sorted encountered keys in the solver.
        :return:                    The dictionary corresponding to a line to be rendered.
        '''
        results = solver.get_results(financial_line)['formula']

        is_leaf = solver.is_leaf(financial_line)
        has_lines = solver.has_move_lines(financial_line)
        has_something_to_unfold = is_leaf and has_lines and bool(financial_line.groupby)

        # Compute if the line is unfoldable or not.
        is_unfoldable = has_something_to_unfold and financial_line.show_domain == 'foldable'

        # Compute the id of the report line we'll generate
        report_line_id = self._get_generic_line_id('account.financial.html.report.line', financial_line.id)

        # Compute if the line is unfolded or not.
        # /!\ Take care about the case when the line is unfolded but not unfoldable with show_domain == 'always'.
        if not has_something_to_unfold or financial_line.show_domain == 'never':
            is_unfolded = False
        elif financial_line.show_domain == 'always':
            is_unfolded = True
        elif financial_line.show_domain == 'foldable' and report_line_id in options['unfolded_lines']:
            is_unfolded = True
        else:
            is_unfolded = False

        # Standard columns.
        columns = []
        for key in groupby_keys:
            amount = results.get(key, 0.0)
            columns.append({'name': self._format_cell_value(financial_line, amount), 'no_format': amount, 'class': 'number'})

        # Growth comparison column.
        if self._display_growth_comparison(options):
            columns.append(self._compute_growth_comparison_column(options,
                columns[0]['no_format'],
                columns[1]['no_format'],
                green_on_positive=financial_line.green_on_positive
            ))

        financial_report_line = {
            'id': report_line_id,
            'name': financial_line.name,
            'model_ref': ('account.financial.html.report.line', financial_line.id),
            'level': financial_line.level,
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
            'columns': columns,
            'unfoldable': is_unfoldable,
            'unfolded': is_unfolded,
            'page_break': financial_line.print_on_new_page,
            'action_id': financial_line.action_id.id,
        }

        # Only run the checks in debug mode
        if self.user_has_groups('account.group_account_manager'):
            # If a financial line has a control domain, a check is made to detect any potential discrepancy
            if financial_line.control_domain:
                if not financial_line._check_control_domain(options, results, self):
                    # If a discrepancy is found, a check is made to see if the current line is
                    # missing items or has items appearing more than once.
                    has_missing = solver._has_missing_control_domain(options, financial_line)
                    has_excess = solver._has_excess_control_domain(options, financial_line)
                    financial_report_line['has_missing'] = has_missing
                    financial_report_line['has_excess'] = has_excess
                    # In either case, the line is colored in red.
                    # The ids of the missing / excess report lines are stored in the options for the top yellow banner
                    if has_missing:
                        financial_report_line['class'] += ' alert alert-danger'
                        options.setdefault('control_domain_missing_ids', [])
                        options['control_domain_missing_ids'].append(financial_line.id)
                    if has_excess:
                        financial_report_line['class'] += ' alert alert-danger'
                        options.setdefault('control_domain_excess_ids', [])
                        options['control_domain_excess_ids'].append(financial_line.id)

        # Debug info columns.
        if self._display_debug_info(options):
            columns.append(self._compute_debug_info_column(options, solver, financial_line))

        # Custom caret_options for tax report.
        if self.tax_report and financial_line.domain and not financial_line.action_id:
            financial_report_line['caret_options'] = 'tax.report.line'

        return financial_report_line

