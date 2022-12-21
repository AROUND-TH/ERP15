# -*- coding: utf-8 -*-

import calendar
from dateutil.relativedelta import relativedelta
from math import copysign

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, float_round

from collections import defaultdict
import re


class AccountAsset(models.Model):
    _name = 'account.asset'
    _inherit = ['account.asset', 'image.mixin']


    asset_number = fields.Char(
        string='Asset No.', 
        # @Remark for issue on crete invoice (Odoo15)
        # required=True,
        # index=True,
        readonly=False,
        copy=False,
    )
    running_prefix = fields.Char(
        string="Material Category", 
        readonly=True,
        states={'model': [('readonly', False)]}
    )
    running_digit = fields.Integer(
        string="Running No.", 
        readonly=True,
        states={'model': [('readonly', False)]}
    )

    purchase_order_id = fields.Many2one('purchase.order', 
        string='Purchase Order', 
    )
    document_number = fields.Char(
        string='Document No.', 
    )

    # Image
    image_1920 = fields.Image()

    # Depreciation params
    method = fields.Selection([('365', '365 days'), ('linear', 'Straight Line'), ('degressive', 'Declining'), ('degressive_then_linear', 'Declining then Straight Line')],
        string='Method',
        readonly=True,
        default='365',
        states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
        help="Choose the method to use to compute the amount of depreciation lines.\n"
            "  * 365 days: Calculated by day based on 365 days\n"
            "  * Straight Line: Calculated on basis of: Gross Value / Number of Depreciations\n"
            "  * Declining: Calculated on basis of: Residual Value * Declining Factor\n"
            "  * Declining then Straight Line: Like Declining but with a minimum depreciation value equal to the straight line value.")

    # Transfer
    transfer_date = fields.Date(
        string='Transfer Date',
        copy=False,
    )
    transfer_account_analytic_id = fields.Many2one(
        'account.analytic.account', 
        string='Transfer Analytic Account', 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    transfer_analytic_tag_ids = fields.Many2many(
        'account.analytic.tag',
        'transfer_analytic_tag_id',
        string='Transfer Analytic Tag',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )

    # Transfer Log Line
    transfer_log_ids = fields.One2many('asset.transfer.log', 'asset_id',
        string='Transfer Log',
        readonly=True,
        copy=False,
    )

    # Maintenance Line
    maintenance_ids = fields.One2many('asset.maintenance', 'asset_id',
        string='Maintenance',
        copy=False,
    )

    @api.constrains('running_prefix', 'running_digit')
    def _check_running_sequence(self):
        for rec in self:
            if rec.state == 'model':
                if rec.running_digit > 0 and not rec.running_prefix:
                    raise ValidationError(_("Material Category cannot be empty, If Running No was set."))
                elif rec.running_prefix and rec.running_digit <= 0:
                    raise ValidationError(_("Running No must greater than 0, If Material Category was set."))


    @api.onchange('running_prefix')
    def _onchange_running_prefix(self):
        if self.running_prefix:
            self.running_prefix = self.running_prefix.upper()
            if self.running_digit <= 0:
                self.running_digit = 5
        else:
            self.running_digit = 0

    # @Override method _onchange_model_id
    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata = model.prorata
            self.prorata_date = fields.Date.today()

            self.running_prefix = model.running_prefix
            self.running_digit = model.running_digit
            self.account_asset_id = model.account_asset_id

            self.account_analytic_id = model.account_analytic_id.id
            self.analytic_tag_ids = [(6, 0, model.analytic_tag_ids.ids)]
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id


    def _compute_board_amount_365(self, computation_sequence, residual_amount, total_amount_to_depr, max_depreciation_nb, starting_sequence, depreciation_date):
        amount = 0
        if computation_sequence == max_depreciation_nb:
            # last depreciation always takes the asset residual amount
            amount = residual_amount
        else:
            nb_depreciation = max_depreciation_nb - starting_sequence
            if self.prorata:
                nb_depreciation -= 1

            total_days = 365
            if self.method_period == "12":
                days = nb_depreciation * total_days
                # total_days = (depreciation_date.year % 4) and 365 or 366
                days_amount = (total_amount_to_depr / days) * total_days
                days_amount = float_round(days_amount, precision_digits=2, rounding_method='DOWN')
            else:
                days = (nb_depreciation / 12) * total_days
                days = float_round(days, precision_digits=2, rounding_method='DOWN')
                days_amount = (total_amount_to_depr / days) * depreciation_date.day
                days_amount = float_round(days_amount, precision_digits=2, rounding_method='DOWN')

            amount = min(days_amount, residual_amount)
        return amount

    # @Override method _recompute_board
    def _recompute_board(self, depreciation_number, starting_sequence, amount_to_depreciate, depreciation_date, already_depreciated_amount, amount_change_ids):
        self.ensure_one()
        residual_amount = amount_to_depreciate
        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        move_vals = []
        prorata = self.prorata and not self.env.context.get("ignore_prorata")
        if amount_to_depreciate != 0.0:
            for asset_sequence in range(starting_sequence + 1, depreciation_number + 1):
                while amount_change_ids and amount_change_ids[0].date <= depreciation_date:
                    if not amount_change_ids[0].reversal_move_id:
                        residual_amount -= amount_change_ids[0].amount_total
                        amount_to_depreciate -= amount_change_ids[0].amount_total
                        already_depreciated_amount += amount_change_ids[0].amount_total
                    amount_change_ids[0].write({
                        'asset_remaining_value': float_round(residual_amount, precision_rounding=self.currency_id.rounding),
                        'asset_depreciated_value': amount_to_depreciate - residual_amount + already_depreciated_amount,
                    })
                    amount_change_ids -= amount_change_ids[0]

                if self.method == "365":
                    amount = self._compute_board_amount_365(asset_sequence, residual_amount, amount_to_depreciate, depreciation_number, starting_sequence, depreciation_date)
                else:
                    amount = self._compute_board_amount(asset_sequence, residual_amount, amount_to_depreciate, depreciation_number, starting_sequence, depreciation_date)

                prorata_factor = 1
                move_ref = self.name + ' (%s/%s)' % (prorata and asset_sequence - 1 or asset_sequence, self.method_number)
                if prorata and asset_sequence == 1:
                    move_ref = self.name + ' ' + _('(prorata entry)')
                    first_date = self.prorata_date
                    if int(self.method_period) % 12 != 0:
                        month_days = calendar.monthrange(first_date.year, first_date.month)[1]
                        days = month_days - first_date.day + 1
                        prorata_factor = days / month_days
                    else:
                        total_days = (depreciation_date.year % 4) and 365 or 366
                        days = (self.company_id.compute_fiscalyear_dates(first_date)['date_to'] - first_date).days + 1
                        prorata_factor = days / total_days
                amount = self.currency_id.round(amount * prorata_factor)
                if float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    continue
                residual_amount -= amount

                move_vals.append(self.env['account.move']._prepare_move_for_asset_depreciation({
                    'amount': amount,
                    'asset_id': self,
                    'move_ref': move_ref,
                    'date': depreciation_date,
                    'account_analytic_id': self.account_analytic_id,
                    'analytic_tag_ids': self.analytic_tag_ids,
                    'purchase_order_id': self.purchase_order_id,
                    'document_number': self.document_number,
                    'asset_remaining_value': float_round(residual_amount, precision_rounding=self.currency_id.rounding),
                    'asset_depreciated_value': amount_to_depreciate - residual_amount + already_depreciated_amount,
                }))

                depreciation_date = depreciation_date + relativedelta(months=+int(self.method_period))
                # datetime doesn't take into account that the number of days is not the same for each month
                if int(self.method_period) % 12 != 0:
                    max_day_in_month = calendar.monthrange(depreciation_date.year, depreciation_date.month)[1]
                    depreciation_date = depreciation_date.replace(day=max_day_in_month)
        return move_vals


    # @Override method _get_disposal_moves
    def _get_disposal_moves(self, invoice_line_ids, disposal_date):
        def get_line(asset, amount, account):
            return (0, 0, {
                'name': asset.name,
                'account_id': account.id,
                'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
                'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
                'analytic_account_id': account_analytic_id.id if asset.asset_type == 'sale' else False,
                'analytic_tag_ids': [(6, 0, analytic_tag_ids.ids)] if asset.asset_type == 'sale' else False,
                'currency_id': current_currency.id,
                'amount_currency': -asset.value_residual,
            })

        move_ids = []
        assert len(self) == len(invoice_line_ids)
        for asset, invoice_line_id in zip(self, invoice_line_ids):
            posted_moves = asset.depreciation_move_ids.filtered(lambda x: (
                not x.reversal_move_id
                and x.state == 'posted'
            ))
            if posted_moves and disposal_date < max(posted_moves.mapped('date')):
                if invoice_line_id:
                    raise UserError('There are depreciation posted after the invoice date (%s).\nPlease revert them or change the date of the invoice.' % disposal_date)
                else:
                    raise UserError('There are depreciation posted in the future, please revert them.')
            account_analytic_id = asset.account_analytic_id
            analytic_tag_ids = asset.analytic_tag_ids
            company_currency = asset.company_id.currency_id
            current_currency = asset.currency_id
            prec = company_currency.decimal_places
            unposted_depreciation_move_ids = asset.depreciation_move_ids.filtered(lambda x: x.state == 'draft')

            old_values = {
                'method_number': asset.method_number,
            }

            # Remove all unposted depr. lines
            commands = [(2, line_id.id, False) for line_id in unposted_depreciation_move_ids]

            # Create a new depr. line with the residual amount and post it
            asset_sequence = len(asset.depreciation_move_ids) - len(unposted_depreciation_move_ids) + 1

            initial_amount = asset.original_value
            initial_account = asset.original_move_line_ids.account_id if len(asset.original_move_line_ids.account_id) == 1 else asset.account_asset_id
            depreciation_moves = asset.depreciation_move_ids.filtered(lambda r: r.state == 'posted' and not (r.reversal_move_id and r.reversal_move_id[0].state == 'posted'))
            depreciated_amount = copysign(
                sum(depreciation_moves.mapped('amount_total')) + asset.already_depreciated_amount_import,
                -initial_amount,
            )
            depreciation_account = asset.account_depreciation_id
            invoice_amount = copysign(invoice_line_id.price_subtotal, -initial_amount)
            invoice_account = invoice_line_id.account_id
            difference = -initial_amount - depreciated_amount - invoice_amount
            difference_account = asset.company_id.gain_account_id if difference > 0 else asset.company_id.loss_account_id
            line_datas = [(initial_amount, initial_account), (depreciated_amount, depreciation_account), (invoice_amount, invoice_account), (difference, difference_account)]
            if not invoice_line_id:
                del line_datas[2]
            vals = {
                'asset_id': asset.id,
                'ref': asset.name + ': ' + (_('Disposal') if not invoice_line_id else _('Sale')),
                'asset_remaining_value': 0,
                'asset_depreciated_value': max(asset.depreciation_move_ids.filtered(lambda x: x.state == 'posted'), key=lambda x: x.date, default=self.env['account.move']).asset_depreciated_value,
                'date': disposal_date,
                'account_analytic_id': asset.account_analytic_id.id,
                'analytic_tag_ids': asset.analytic_tag_ids.ids,
                'purchase_order_id': asset.purchase_order_id.id,
                'document_number': asset.document_number,
                'journal_id': asset.journal_id.id,
                'line_ids': [get_line(asset, amount, account) for amount, account in line_datas if account],
            }
            commands.append((0, 0, vals))
            asset.write({'depreciation_move_ids': commands, 'method_number': asset_sequence})
            tracked_fields = self.env['account.asset'].fields_get(['method_number'])
            changes, tracking_value_ids = asset._mail_track(tracked_fields, old_values)
            if changes:
                asset.message_post(body=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
            move_ids += self.env['account.move'].search([('asset_id', '=', asset.id), ('state', '=', 'draft')]).ids

        return move_ids


    # @Override method _insert_depreciation_line
    def _insert_depreciation_line(self, line_before, amount, label, depreciation_date):
        """ Inserts a new line in the depreciation board, shifting the sequence of
        all the following lines from one unit.
        :param line_before:     The depreciation line after which to insert the new line,
                                or none if the inserted line should take the first position.
        :param amount:          The depreciation amount of the new line.
        :param label:           The name to give to the new line.
        :param date:            The date to give to the new line.
        """
        self.ensure_one()
        moveObj = self.env['account.move']

        new_line = moveObj.create(moveObj._prepare_move_for_asset_depreciation({
            'amount': amount,
            'asset_id': self,
            'move_ref': self.name + ': ' + label,
            'date': depreciation_date,
            'account_analytic_id': self.account_analytic_id,
            'analytic_tag_ids': self.analytic_tag_ids,
            'purchase_order_id': self.purchase_order_id,
            'document_number': self.document_number,
            'asset_remaining_value': self.value_residual - amount,
            'asset_depreciated_value': line_before and (line_before.asset_depreciated_value + amount) or amount,
        }))
        return new_line


    # @Override method validate
    def validate(self):
        self._compute_asset_type()

        super(AccountAsset, self).validate()
        for asset in self:
            asset.asset_number = asset._get_sequence_next()

            for move in asset.depreciation_move_ids:
                move.account_analytic_id = asset.account_analytic_id
                move.analytic_tag_ids = asset.analytic_tag_ids
                move.purchase_order_id = asset.purchase_order_id
                move.document_number = asset.document_number

            for move_line in asset.original_move_line_ids:
                move_line.asset_count += 1

    @api.model
    def _get_sequence_next(self):
        if self.running_prefix and (self.running_digit > 0):
            code = f"account.asset.{self.running_prefix}"
            sequence_next = self.env['ir.sequence'].sudo().next_by_code(code)

            if not sequence_next:
                sequence = self.env['ir.sequence'].sudo().create({
                    'company_id': self.env.company.id,
                    'name': f'Asset Model {self.running_prefix}',
                    'code': code,
                    # 'prefix': self.running_prefix,
                    'prefix': f'{self.running_prefix}-',
                    'padding': self.running_digit,
                })
                sequence_next = sequence.sudo().next_by_code(code)

            return sequence_next
        else:
            return False

    def write(self, vals):
        change_sequence = False
        if vals.get('running_prefix') or vals.get('running_digit'):
            change_sequence = True

        result = super(AccountAsset, self).write(vals)
        if change_sequence:
            for rec in self:
                if rec.state == 'model' and rec.running_prefix and rec.running_digit > 0:
                    # update running_digit in Asset Model
                    models = self.env['account.asset'].search([
                            ('state', '=', 'model'),
                            ('running_prefix', '=', rec.running_prefix),
                            ('running_digit', '!=', rec.running_digit),
                        ])
                    if models:
                        models.update({"running_digit": rec.running_digit})

                    # update padding in Sequence
                    code = f"account.asset.{rec.running_prefix}"
                    sequence = self.env['ir.sequence'].sudo().search([
                            ('code', '=', code),
                            ('padding', '!=', rec.running_digit),
                        ])
                    if sequence:
                        sequence.update({"padding": rec.running_digit})
        return result


    ### Asset Transfer methods ###
    def button_transfer_print(self):
        self.ensure_one()

        value = self.read(['transfer_date', 'account_analytic_id', 'transfer_account_analytic_id', 'transfer_analytic_tag_ids'])[0]
        # Check mandatory field of Transfer Data >> transfer_date, transfer_account_analytic_id
        if (not value.get("transfer_date") or not value.get("transfer_account_analytic_id")):
            raise ValidationError(_("Please Input Transfer Data."))

        document_number = self.env['ir.sequence'].sudo().next_by_code(
            'sequence.asset.transfer') or False
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

        vals = {}
        vals["account_analytic_id"] = self.transfer_account_analytic_id
        vals["analytic_tag_ids"] = self.transfer_analytic_tag_ids
        vals["transfer_date"] = False
        vals["transfer_account_analytic_id"] = False
        vals["transfer_analytic_tag_ids"] = False

        transfer_log_ids = []
        transfer_log_ids.append(
            (0, 0,
                {
                    'asset_id': self.id,
                    'document_number': document_number,
                    'quantity': 1,
                    'account_analytic_id': self.account_analytic_id.id,
                    'transfer_account_analytic_id': self.transfer_account_analytic_id.id,
                    'transfer_date': self.transfer_date,
                    'employee_id': employee_id.id,
                }
            )
        )
        vals["transfer_log_ids"] = transfer_log_ids
        # self.update({'transfer_log_ids': transfer_log_ids})
        self.update(vals)

        for move in self.depreciation_move_ids:
            # @Check if move.date >= transfer_date then set transfer data.
            if move.date >= value.get("transfer_date"):
                move.account_analytic_id = self.account_analytic_id
                move.analytic_tag_ids = self.analytic_tag_ids
                move.purchase_order_id = self.purchase_order_id
                move.document_number = self.document_number

        data = {
            'docids': self.id,
            'document_number': document_number,
            'employee_name': employee_id.name,
            'quantity': 1,
            'transfer_date': value.get("transfer_date"),
            'account_analytic_id': value.get("account_analytic_id"),
            'transfer_account_analytic_id': value.get("transfer_account_analytic_id"),
            'transfer_analytic_tag_ids': value.get("transfer_analytic_tag_ids"),
            # 'transfer_date': self.transfer_date,
            # 'transfer_account_analytic_id': self.transfer_account_analytic_id,
            # 'transfer_analytic_tag_ids': self.transfer_analytic_tag_ids,
        }

        # return self.env.ref('custom_account.report_account_asset_transfer').report_action(self.id)
        return self.env.ref('custom_account.report_account_asset_transfer').report_action(None, data=data)



class AssetTransferLog(models.Model):
    _name = 'asset.transfer.log'
    _description = "Asset Transfer Log"


    asset_id = fields.Many2one('account.asset', 
        string='Accounting Asset',
        index=True, 
        readonly=True, 
        ondelete="cascade",
        help="The asset of this entry log."
    )
    document_number = fields.Char(
        string='Document No.', 
        index=True, 
        readonly=True, 
    )

    asset_number = fields.Char(
        string='Asset No.', 
        readonly=True,
        related='asset_id.asset_number', 
    )
    asset_name = fields.Char(
        string='Asset Name', 
        readonly=True,
        related='asset_id.name', 
    )

    user_id = fields.Many2one('res.users', 
        string='Create User',
        readonly=True,
        default=lambda self: self.env.user
    )
    employee_id = fields.Many2one('hr.employee', 
        string='Create By',
        readonly=True,
    )

    quantity = fields.Integer(
        string='Quantity',
        readonly=True,
    )

    account_analytic_id = fields.Many2one(
        'account.analytic.account', 
        string='Transfer From', 
        readonly=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    transfer_account_analytic_id = fields.Many2one(
        'account.analytic.account', 
        string='Transfer To', 
        readonly=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    )
    transfer_date = fields.Date(
        string='Transfer Date',
        readonly=True,
    )



class AssetMaintenance(models.Model):
    _name = 'asset.maintenance'
    _description = "Asset Maintenance"


    asset_id = fields.Many2one('account.asset', 
        string='Accounting Asset',
        index=True, 
        readonly=True, 
        ondelete="cascade",
        help="The asset of this maintenance entry."
    )
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,
        related='asset_id.currency_id')

    ordinal_number = fields.Integer(
        string='Ordinal No.', 
        index=True, 
        readonly=True, 
        default=0
    )

    maintenance_date = fields.Date(
        string='Maintenance Date',
        required=True,
    )

    detail = fields.Text(
        string='Detail', 
        required=True,
    )

    amount = fields.Monetary(
        string='Amount', 
        currency_field='company_currency_id',
        required=True,
        default=0
    )

    maintenance_company = fields.Char(
        string='Maintenance Company', 
        required=True,
    )

    responsible_person = fields.Char(
        string='Responsible Person', 
        required=True,
    )

    remark = fields.Text(
        string='Remark',
    )


    @api.model
    def create(self, values):
        maintenance = self.env['asset.maintenance'].search([('asset_id', '=', values.get('asset_id'))], order='ordinal_number desc', limit=1)

        if maintenance:
            values['ordinal_number'] = maintenance.ordinal_number + 1
        else:
            values['ordinal_number'] = 1

        return super(AssetMaintenance, self).create(values)

