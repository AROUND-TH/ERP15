from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    lc_number = fields.Char(string="L/C Number")
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('confirm', 'Confirmed'),
        ('to approve', 'Pending Approval'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))

    # @Approval State
    category_ids = fields.Many2many('product.category', string='Category', required=False)
    req_approve_employee_id = fields.Many2one(
        'hr.employee',
        string='Waiting Approver',
        readonly=True,
        copy=False,
    )
    procedure_id = fields.Many2one(
        'release.procedure',
        string='Release Procedure'
    )
    approve_sequence = fields.Integer(
        string='Approve Sequence',
        default=0
    )
    approve_sequence_max = fields.Integer(
        string='Approve Sequence Max',
        compute='_compute_approve_sequence_max',
        default=0
    )
    purchase_order_approval_ids = fields.One2many(
        'purchase.order.approval',
        'order_id',
        string='Purchase Order Approval',
        states=READONLY_STATES,
        copy=False,
    )
    approval_position = fields.Many2one('purchase.order.approval', string='Approval Position', domain="[('order_id', '=', id)]")

    # @Confirm and Approve Data
    confirm_employee_id = fields.Many2one(
        'hr.employee',
        string='Confirmed by',
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        string='Confirmed Date',
        readonly=True,
        copy=False,
    )

    approve_employee_id = fields.Many2one(
        'hr.employee',
        string='Approved by',
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string='Approved Date',
        readonly=True,
        copy=False,
    )

    reject_employee_id = fields.Many2one(
        'hr.employee',
        string='Rejected by',
        readonly=True,
        copy=False,
    )
    userreject_date = fields.Date(
        string='Rejected Date',
        readonly=True,
        copy=False,
    )

    # ux field
    show_receive_service = fields.Boolean(compute="_compute_show_receive_service")
    is_on_active = fields.Boolean(compute='_compute_is_on_active',)
    coo_approve_id = fields.Many2one('res.users', string='COO Approved by', readonly=True, copy=False,)
    coo_approve_date = fields.Date('COO Approved Date')
    ceo_approve_id = fields.Many2one('res.users', string='CEO Approved by', readonly=True, copy=False,)
    ceo_approve_date = fields.Date('CEO Approved Date')

    def print_purchase_order(self):
        self.ensure_one()
        return self.env.ref('purchase.action_report_purchase_order').report_action(self)

    def print_purchase_order(self):
        self.ensure_one()
        return self.env.ref('purchase.action_report_purchase_order').report_action(self)

    def _compute_is_on_active(self):
        for rec in self:
            if self.user_has_groups('custom_purchase.group_purchase_no_activity'):
                rec.is_on_active = True
            else:
                rec.is_on_active = False

    def _compute_show_receive_service(self):
        for rec in self:
            show_receive_service = False
            if rec.state == 'done' and rec.order_line.filtered(lambda line_id: line_id.product_id.type == "service"):
                show_receive_service = True
            rec.show_receive_service = show_receive_service

    @api.onchange('partner_id')
    def _onchange_partner(self):
        for line in self.order_line:
            line.date_planned = False
            line._onchange_quantity()

    @api.depends('purchase_order_approval_ids')
    def _compute_approve_sequence_max(self):
        for record in self:
            record.approve_sequence_max = len(record.purchase_order_approval_ids)

    def recursive_employee_id(self, employee, list=[]):
        if employee:
            list.append(employee.id)
            if employee.parent_id:
                return self.recursive_employee_id(employee.parent_id, list)
            else:
                return list

    def recursive_category_id(self, category, list=[]):
        if category:
            list.append(category.id)
            if category.parent_id:
                return self.recursive_category_id(category.parent_id, list)
            else:
                return list

    # @Set Approval Process
    def _set_approval_process(self, record):
        if not record:
            return False

        values = {}
        category_ids = []
        for line in record.order_line:
            self.recursive_category_id(line.product_id.categ_id, category_ids)
        category_ids = list(set(category_ids))
        values['category_ids'] = [(6, 0, category_ids)]

        query_chk = """
            SELECT rp.id, rp."name", rp_chk.chk_count
            FROM release_procedure rp 
            INNER JOIN
            (SELECT release_procedure_id, count(product_category_id) as chk_count
                FROM product_category_release_procedure_rel pcrpr
                WHERE product_category_id IN %s
                GROUP BY release_procedure_id
                HAVING count(product_category_id) = %s
            ) AS rp_chk
            ON rp.id = rp_chk.release_procedure_id
            WHERE rp.procedure_type = 'po'
            AND %s >= rp.min_amount
            AND (
            (rp."condition" = 'equal' AND %s = rp.max_amount)
            OR
            (rp."condition" = 'greater_than' AND %s > rp.max_amount)
            OR
            (rp."condition" = 'less_than' AND %s < rp.max_amount)
            OR
            (rp."condition" = 'greater_than_equal' AND %s >= rp.max_amount)
            OR
            (rp."condition" = 'less_than_equal' AND %s <= rp.max_amount)
            )
            ORDER BY rp.max_amount DESC,
            rp.min_amount DESC, rp."condition" ASC
            LIMIT 1
        """
        self._cr.execute(query_chk, (
        tuple(category_ids), len(category_ids), record.amount_total, record.amount_total, record.amount_total,
        record.amount_total, record.amount_total, record.amount_total))
        result = self._cr.dictfetchall()

        if result:
            values['procedure_id'] = result[0]['id']

            employee_ids = []
            self.recursive_employee_id(record.employee_id, employee_ids)
            employee_ids.reverse()
            employees = self.env['hr.employee'].browse(employee_ids)

            approval_ids = []
            procedure_lines = self.env['release.procedure.line'].search([('procedure_id', '=', result[0]['id'])])
            for line in procedure_lines:
                employee_id = None
                for emp in employees:
                    if not emp.job_id:
                        continue

                    if line.position_chk == 'name':
                        if emp.job_id.name == line.positions_id.name:
                            employee_id = emp.id
                    else:
                        if emp.job_id == line.positions_id:
                            employee_id = emp.id

                if line.position_chk == 'name':
                    authentication_id = self.env['purchase.authentication'].search(
                        [('positions_po_id.name', '=', line.positions_id.name)], limit=1)
                else:
                    authentication_id = self.env['purchase.authentication'].search(
                        [('positions_po_id', '=', line.positions_id.id)], limit=1)
                if authentication_id:
                    employee_id = authentication_id.user_po_id.id

                approval_ids.append(
                    (0, 0,
                     {
                         'order_id': record.id,
                         'approver': line.approver,
                         'position_id': line.positions_id.id,
                         'position_chk': line.position_chk,
                         'employee_id': employee_id,
                     }
                     )
                )
            values['purchase_order_approval_ids'] = approval_ids

            if len(procedure_lines) > 0:
                if record.purchase_order_approval_ids:
                    record.purchase_order_approval_ids.unlink()

                values['approve_sequence'] = 1
                record.update(values)
                return True

        record.update(values)
        return False

    # @Override the button Confirm Order
    def button_confirm(self):
        today = fields.Date.today()
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()

            # @Remark to not use standart approval allowed.
            # # Deal with double validation process
            # if order._approval_allowed():
            #     order.button_approve()
            # else:
            #     order.write({'state': 'to approve'})

            result = self._set_approval_process(order)
            if result:
                order.confirm_employee_id = employee_id
                order.confirm_date = today
                order.state = 'confirm'
            else:
                chk_approval_procedure = self.env['ir.config_parameter'].sudo().get_param(
                    'purchase.po_approval_procedure')
                if not self.user_has_groups('custom_purchase.purchase_all_approval') and chk_approval_procedure:
                    raise UserError(
                        _('All PO must to pass the approve by Approval Procedure process,\nBut this PO not match with Release Procedure Configuration!\nPlease contact Administrator.'))

                order.confirm_employee_id = employee_id
                order.confirm_date = today

                order.approve_employee_id = employee_id
                order.userrapp_date = today
                order.button_approve()

            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    # @Add the button Request for Approval
    def request_approval(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        today = fields.Date.today()

        for rec in self:
            if rec.state != 'confirm':
                return

            for approval in rec.purchase_order_approval_ids:
                if not self.user_has_groups('custom_purchase.purchase_all_approval') and not approval.employee_id:
                    raise UserError(
                        _('Please set "Approval User" of the "%s" position in Approval Procedure.' % approval.position_id.name))

            if rec.approve_sequence > 0 and rec.approve_sequence < rec.approve_sequence_max:
                rec.req_approve_employee_id = rec.purchase_order_approval_ids[rec.approve_sequence - 1].employee_id
                if not self.user_has_groups('custom_purchase.purchase_all_approval') and not rec.req_approve_employee_id:
                    raise UserError(_('Please set "Approval User" of the "%s" position in Approval Procedure.' %
                                      rec.purchase_order_approval_ids[rec.approve_sequence - 1].position_id.name))

                rec.state = 'to approve'
                rec.approval_position = rec.purchase_order_approval_ids[rec.approve_sequence - 1].id

                request_mail_template = self.env.ref('custom_purchase.email_purchase_order_request_approve')
                if request_mail_template:
                    request_mail_template.sudo().send_mail(self.id)

            elif rec.approve_sequence > 0 and rec.approve_sequence >= rec.approve_sequence_max:
                rec.req_approve_employee_id = rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].employee_id
                if not self.user_has_groups('custom_purchase.purchase_all_approval') and not rec.req_approve_employee_id:
                    raise UserError(_('Please set "Approval User" of the "%s" position in Approval Procedure.' %
                                      rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].position_id.name))

                rec.state = 'to approve'
                rec.approval_position = rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].id

                request_mail_template = self.env.ref('custom_purchase.email_purchase_order_request_approve')
                if request_mail_template:
                    request_mail_template.sudo().send_mail(self.id)

            else:
                chk_approval_procedure = self.env['ir.config_parameter'].sudo().get_param(
                    'purchase.po_approval_procedure')
                if not self.user_has_groups('custom_purchase.purchase_all_approval') and chk_approval_procedure:
                    raise UserError(
                        _('All PO must to pass the approve by Approval Procedure process,\nBut this PO not match with Release Procedure Configuration!\nPlease contact Administrator.'))

                rec.approve_employee_id = employee_id
                rec.userrapp_date = today
                rec.button_approve()
                response_mail_template = self.env.ref('custom_purchase.email_purchase_order_approved')
                if response_mail_template:
                    response_mail_template.sudo().send_mail(self.id)

    # @Add new Approve button for approval procedure
    def manager_approve(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        today = fields.Date.today()

        for rec in self:
            if rec.state != 'to approve':
                return

            if rec.approve_sequence > 0 and rec.approve_sequence < rec.approve_sequence_max:
                rec.req_approve_employee_id = rec.purchase_order_approval_ids[rec.approve_sequence - 1].employee_id

                if not self.user_has_groups('custom_purchase.purchase_all_approval'):
                    if not rec.req_approve_employee_id:
                        raise UserError(_('Please set "Approval User" of the "%s" position in Approval Procedure.' %
                                        rec.purchase_order_approval_ids[rec.approve_sequence - 1].position_id.name))

                    if employee_id != rec.req_approve_employee_id:
                        raise UserError(_('Waiting for "%s" from "%s" to Approve.' % (
                        rec.purchase_order_approval_ids[rec.approve_sequence - 1].employee_id.name,
                        rec.purchase_order_approval_ids[rec.approve_sequence - 1].position_id.name)))

                rec.purchase_order_approval_ids[rec.approve_sequence - 1].approval_date = today
                rec.approve_employee_id = employee_id
                rec.userrapp_date = today
                rec.state = 'to approve'
                rec.approve_sequence += 1
                rec.approval_position = rec.purchase_order_approval_ids[rec.approve_sequence - 1].id

                response_mail_template = self.env.ref('custom_purchase.email_purchase_order_approved')
                if response_mail_template:
                    response_mail_template.sudo().send_mail(self.id)

                rec.req_approve_employee_id = rec.purchase_order_approval_ids[rec.approve_sequence - 1].employee_id
                request_mail_template = self.env.ref('custom_purchase.email_purchase_order_request_approve')
                if request_mail_template:
                    request_mail_template.sudo().send_mail(self.id)

            elif rec.approve_sequence > 0 and rec.approve_sequence >= rec.approve_sequence_max:
                rec.req_approve_employee_id = rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].employee_id

                if not self.user_has_groups('custom_purchase.purchase_all_approval'):
                    if not rec.req_approve_employee_id:
                        raise UserError(_('Please set "Approval User" of the "%s" position in Approval Procedure.' %
                                        rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].position_id.name))

                    if employee_id != rec.req_approve_employee_id:
                        raise UserError(_('Waiting for "%s" from "%s" to Approve.' % (
                        rec.purchase_order_approval_ids[rec.approve_sequence - 1].employee_id.name,
                        rec.purchase_order_approval_ids[rec.approve_sequence - 1].position_id.name)))

                rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].approval_date = today
                rec.approve_employee_id = employee_id
                rec.userrapp_date = today
                rec.button_approve()
                rec.approve_sequence += 1
                rec.approval_position = rec.purchase_order_approval_ids[rec.approve_sequence_max - 1].id

                response_mail_template = self.env.ref('custom_purchase.email_purchase_order_approved')
                if response_mail_template:
                    response_mail_template.sudo().send_mail(self.id)

            else:
                chk_approval_procedure = self.env['ir.config_parameter'].sudo().get_param(
                    'purchase.po_approval_procedure')
                if not self.user_has_groups('custom_purchase.purchase_all_approval') and chk_approval_procedure:
                    raise UserError(
                        _('All PO must to pass the approve by Approval Procedure process,\nBut this PO not match with Release Procedure Configuration!\nPlease contact Administrator.'))

                rec.approve_employee_id = employee_id
                rec.userrapp_date = today
                rec.button_approve()
                rec.approve_sequence = 0

                response_mail_template = self.env.ref('custom_purchase.email_purchase_order_approved')
                if response_mail_template:
                    response_mail_template.sudo().send_mail(self.id)

    # @Override the button Cancel
    def button_cancel(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        today = fields.Date.today()

        # groups can cancel when state not po
        user = self.env.user
        is_role_user = user.has_group('purchase.group_purchase_user')
        is_role_no_activity = user.has_group('custom_purchase.group_purchase_no_activity')
        # groups can cancel when state is po and not received
        is_role_admin = user.has_group('purchase.group_purchase_manager')
        is_role_all_approval = user.has_group('custom_purchase.purchase_all_approval')

        for order in self:
            if order.state in ["purchase", "done"]:
                if not is_role_admin and not is_role_all_approval:
                    raise UserError(_('No permission. When document is "Done" only "Purchase Admin" can cancel.'))
            else:
                if not is_role_user and not is_role_no_activity:
                    raise UserError(_('No permission. Only "Purchase User" can cancel.'))

            for move in order.order_line.mapped('move_ids'):
                if move.state == 'done':
                    raise UserError(
                        _('Unable to cancel purchase order %s as some receptions have already been done.') % (
                            order.name))

            # If the product is MTO, change the procure_method of the closest move to purchase to MTS.
            # The purpose is to link the po that the user will manually generate to the existing moves's chain.
            if order.state in ('draft', 'sent', 'to approve', 'purchase', 'done'):
                for order_line in order.order_line:
                    order_line.move_ids._action_cancel()
                    if order_line.move_dest_ids:
                        move_dest_ids = order_line.move_dest_ids
                        if order_line.propagate_cancel:
                            move_dest_ids._action_cancel()
                        else:
                            move_dest_ids.write({'procure_method': 'make_to_stock'})
                            move_dest_ids._recompute_state()

            for pick in order.picking_ids.filtered(lambda r: r.state != 'cancel'):
                pick.action_cancel()

            order.order_line.write({'move_dest_ids': [(5, 0, 0)]})

            for inv in order.invoice_ids:
                if inv and inv.state not in ('cancel', 'draft'):
                    raise UserError(
                        _("Unable to cancel this purchase order. You must first cancel the related vendor bills."))

            order.reject_employee_id = employee_id
            order.userreject_date = today
        self.write({'state': 'cancel', 'mail_reminder_confirmed': False})

    def _get_approval_by_level(self, lv):
        approval_id = self.purchase_order_approval_ids.filtered(lambda x: x.approver == lv)
        if not approval_id:
            return False
        return approval_id


class PurchaseOrderApproval(models.Model):
    _name = "purchase.order.approval"
    _description = "Purchase Order Approval"
    _order = 'order_id, approver'

    name = fields.Char(
        related='position_id.name',
        string='Approval Procedure',
    )

    order_id = fields.Many2one('purchase.order', string='Purchase Order', index=True)
    approver = fields.Selection([
        ('lv1', 'Level 1'),
        ('lv2', 'Level 2'),
        ('lv3', 'Level 3'),
        ('lv4', 'Level 4'),
    ],
        string='Approver',
        readonly=True,
        required=True
    )
    position_id = fields.Many2one('hr.job', string='Job Position', required=True)

    position_chk = fields.Selection([
        ('id', 'ID'),
        ('name', 'NAME'),
    ],
        string='Match Position By',
        default='name',
        required=True
    )

    employee_domain = fields.One2many('hr.employee', compute='_compute_employee_domain', store=False)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Approval User',
        required=False,
        domain="[('id', 'in', employee_domain)]",
    )

    approval_date = fields.Date(string='Approval Date', readonly=True)

    @api.onchange('position_chk')
    def _onchange_position_chk(self):
        self.employee_id = False

    @api.onchange('position_id')
    def _onchange_position_id(self):
        self.employee_id = False

    @api.depends('position_chk', 'position_id')
    def _compute_employee_domain(self):
        for approval in self:
            if approval.position_chk == 'name':
                authentication_ids = self.env['purchase.authentication'].search(
                    [('positions_po_id.name', '=', approval.position_id.name)])
                if authentication_ids:
                    approval.employee_id = authentication_ids.user_po_id.id
                    approval.employee_domain = authentication_ids.user_po_id.ids
                else:
                    employee_ids = self.env['hr.employee'].search([('job_id.name', '=', approval.position_id.name)])
                    if len(employee_ids) == 1:
                        approval.employee_id = employee_ids
                    approval.employee_domain = employee_ids or False
            else:
                authentication_ids = self.env['purchase.authentication'].search(
                    [('positions_po_id', '=', approval.position_id.id)])
                if authentication_ids:
                    approval.employee_id = authentication_ids.user_po_id.id
                    approval.employee_domain = authentication_ids.user_po_id.ids
                else:
                    employee_ids = self.env['hr.employee'].search([('job_id', '=', approval.position_id.id)])
                    if len(employee_ids) == 1:
                        approval.employee_id = employee_ids
                    approval.employee_domain = employee_ids or False
