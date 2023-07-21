# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo import tools


class ReportVehiclePipeline2(models.Model):
    _name = 'report.vehicle.pipeline2'
    _description = 'Report Vehicle in Pipeline 2'
    _auto = False
    _rec_name = 'product_id'
    _order = 'date_approve desc'

    # id = fields.Id()
    id = fields.Integer('ID')

    # invisible
    purchase_id = fields.Many2one('purchase.order',
        string='Purchase Order',
        default=False,
    )

    date_approve = fields.Datetime('Purchase Date')

    # invisible
    purchase_line_id = fields.Many2one('purchase.order.line',
        string='Purchase Order Line',
        default=False,
    )

    product_id = fields.Many2one('product.product',
        string='BAH no.',
        default=False,
    )

    partner_ref = fields.Char('Vendor Reference')

    x_studio_model_vehicle = fields.Many2one('fleet.vehicle.model',
        string='Model',
    )
    x_studio_model_tags = fields.Char('Model Tags')
    x_studio_exterior_color_ = fields.Char('Exterior Color (สี)')
    x_studio_interior_color_ = fields.Char('Interior Color (สีภายใน)')

    x_studio_etd = fields.Date(string='ETD (วันที่เรือออก)')
    x_studio_eta = fields.Date(string='ETA (วันเรือเข้า)')

    x_studio_estimate_arrived_for_sale = fields.Date(string='Estimated Arrival for Sales')

    fixed_price = fields.Float(
        string='Current Sales Price',
        digits=(12, 2),
    )
    list_price = fields.Float(
        string='Sales Price',
        digits=(12, 2),
    )
    currency_id = fields.Many2one('res.currency',
        string='Currency',
        default=False,
    )
    x_studio_exchange_rate_est = fields.Float(
        string='Rate (จ่ายประมาณการณ์)',
        digits=(12, 2),
    )

    # invisible
    invoice_id = fields.Many2one('account.move',
        string='Bill',
        default=False,
    )
    # not store only
    currency_rate = fields.Float(
        string='Rate (จ่ายเงินจริง)',
        compute='_compute_currency_rate',
        # store=True,
        # digits=(12, 2),
    )

    # invisible
    price_unit = fields.Float(
        string='Unit Price',
        digits=(12, 2),
    )
    total_rate_exchange = fields.Float(
        string='Total (สกุลเงิน บาท อ้างอิง Rate ประมาณการณ์)',
        digits=(12, 2),
    )
    total_rate_real = fields.Float(
        string='Total (สกุลเงิน บาท อ้างอิง Rate จ่ายเงินจริง)',
        digits=(12, 2),
    )
    deposit_price = fields.Float(
        string='Deposit ที่จ่าย Supplier',
        digits=(12, 2),
    )
    date_planned = fields.Datetime(
        string='วันที่จ่าย Deposit กับ Suppier',
    )

    # invisible
    car_order_id = fields.Many2one('car.order',
        string='Car Order',
        default=False,
    )
    # invisible
    sale_order_id = fields.Many2one('sale.order',
        string='Sale Order',
        default=False,
    )
    partner_id = fields.Many2one('res.partner',
        string='ชื่อลูกค้า',
        default=False,
    )
    salesman_id = fields.Many2one('hr.employee',
        string='Sale ที่ขาย',
        default=False,
    )
    sale_price = fields.Float(
        string="ราคาขาย",
    )
    reserve_price = fields.Float(
        string="เงินจอง Deposit",
    )

    # invisible
    vehicle_id = fields.Many2one('fleet.vehicle',
    	string="Vehicle",
        default=False,
    )
    x_studio_picture = fields.Boolean(
        string='Picture (status)'
    )
    x_studio_inspection_sheet = fields.Boolean(
        string='Inspection Sheet (status)'
    )
    x_studio_received_bl_date = fields.Date(string='Received BL Date')
    x_studio_insurance_pay = fields.Date(string='Insurance + Payin')
    x_studio_bill_of_landing_no = fields.Char('Bill of Landing No.')
    x_studio_bl_surrendered_date = fields.Date(string='B/L Surrendered Date')

    po_state = fields.Selection([
            ('draft', 'RFQ'),
            ('sent', 'RFQ Sent'),
            ('to approve', 'To Approve'),
            ('purchase', 'Purchase Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled')
        ],
        string='Purchase Order Status',
    )
    co_state = fields.Selection([
            ('draft', 'ใบเสนอราคา / ใบจอง'),
            ('confirm', 'รายละเอียดการขายรถยนตร์'),
            ('done', 'ยืนยันแล้ว'),
            ('cancel', 'ยกเลิก'),
        ],
        string='Car Order Status',
    )
    so_state = fields.Selection([
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sales Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled'),
        ],
        string='Sales Order Status',
    )


    @api.depends("invoice_id")
    def _compute_currency_rate(self):
        for rec in self:
            if rec.invoice_id:
                rec.currency_rate = rec.invoice_id.currency_rate
            else:
                rec.currency_rate = 0.0


    @api.model
    def init(self):
        # Manipulate existing view
        tools.drop_view_if_exists(self.env.cr, self._table)

        # Logical Table Query
        query = """
            create or replace view {view_name} as (
                select pol.id as id, po.id as purchase_id, po.date_approve, pol.id as purchase_line_id, pol.product_id,
                po.partner_ref, pt.x_studio_model_vehicle, pt.x_studio_model_tags, pt.x_studio_exterior_color_, pt.x_studio_interior_color_,
                pt.x_studio_etd, pt.x_studio_eta, po.x_studio_estimate_arrived_for_sale, ppi.fixed_price, pt.list_price, po.currency_id,
                pol.x_studio_exchange_rate_est, ampor.invoice_id, pol.price_unit, pol.price_unit * pol.x_studio_exchange_rate_est as total_rate_exchange,
                ampor.amount_total_signed * (-1) as total_rate_real, polsum.deposit_price, polsum.date_planned, co.id as car_order_id, so.id as sale_order_id, co.partner_id, co.salesman_id,
                co.sale_price, co.reserve_price, fv.id as vehicle_id, fv.x_studio_picture, fv.x_studio_inspection_sheet,
                pt.x_studio_received_bl_date, pt.x_studio_insurance_pay, pt.x_studio_bill_of_landing_no, pt.x_studio_bl_surrendered_date,
                po.state as po_state, co.state as co_state, so.state as so_state
                from purchase_order po 
                inner join purchase_order_line pol on pol.order_id = po.id
                inner join product_product pp on pp.id = pol.product_id and pp.active = true
                inner join product_template pt on pt.id = pp.product_tmpl_id and pt.custom_fleet_ok = true
                left join (
                    select ppi.product_tmpl_id, max(ppi.fixed_price) as fixed_price
                    from product_pricelist_item ppi 
                    inner join (
                        select product_tmpl_id, max(date_start) as start_date, max(date_end) as end_date
                        from product_pricelist_item ppi_group
                        where active = true 
                        and product_tmpl_id is not null
                        group by product_tmpl_id 
                        having max(date_start) is null
                        or max(date_end) is null
                    ) as ppi_group on ppi_group.product_tmpl_id = ppi.product_tmpl_id 
                        and ppi.active = true 
                    group by ppi.product_tmpl_id 
                    union 
                    select ppi.product_tmpl_id, max(ppi.fixed_price) as fixed_price
                    from product_pricelist_item ppi 
                    inner join (
                        select product_tmpl_id, max(date_start) as start_date, max(date_end) as end_date
                        from product_pricelist_item ppi_group
                        where active = true 
                        group by product_tmpl_id 
                    ) as ppi_group on ppi_group.product_tmpl_id = ppi.product_tmpl_id 
                        and ppi.active = true 
                        and ppi.date_start = ppi_group.start_date 
                        and ppi.date_end = ppi_group.end_date
                    group by ppi.product_tmpl_id 
                ) as ppi on ppi.product_tmpl_id = pt.id
                left join (
                    select ampor.purchase_order_id as purchase_id,
                    max(ampor.account_move_id) as invoice_id,
                    sum(am.amount_total_signed) as amount_total_signed
                    from account_move_purchase_order_rel ampor
                    inner join account_move am on am.id = ampor.account_move_id
                    where am.state = 'posted'
                    group by ampor.purchase_order_id
                ) as ampor on ampor.purchase_id = po.id
                left join account_move am on am.id = ampor.invoice_id
                left join (
                    select pol.order_id, sum(pol.price_unit) as deposit_price, max(pol.date_planned) as date_planned
                    from purchase_order_line pol 
                    inner join product_product pp on pp.id = pol.product_id 
                    inner join product_template pt on pt.id = pp.product_tmpl_id and pt.custom_fleet_ok = false
                    where pol.product_qty = 0
                    group by pol.order_id
                ) as polsum on polsum.order_id = po.id
                left join car_order co on co.product_id = pol.product_id and co.state != 'cancel'
                left join sale_order so on so.id = co.sale_id and so.state != 'cancel'
                inner join fleet_vehicle fv on fv.id = pt.custom_vehicle_id
                where po.state != 'cancel'
                order by date_approve desc
            )
        """

        # Excute by Odoo Cursor Environment
        self.env.cr.execute(
            query.format(view_name = self._table)
        )

    @api.model
    def fields_get(self, fields=None, attributes=None):
        res = super(ReportVehiclePipeline2, self).fields_get(fields, attributes=attributes)

        if not self.user_has_groups('report_vehicle_pipeline.group_report_vehicle_pipeline_full'):
            hide = [
                'x_studio_exchange_rate_est',
                'currency_rate',
                'total_rate_exchange',
                'total_rate_real',
                'deposit_price',
                'date_planned',
            ]
            for field in hide:
                # To Hide Field From Filter
                # res[field]['selectable'] = False
                res[field]['searchable'] = False

                # To Hide Field From Group by
                res[field]['sortable'] = False

                # To Hide Field From Export List
                # res[field]['exportable'] = False

        return res

