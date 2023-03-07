# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.tools import float_compare, float_is_zero, float_round, date_utils
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class MRPPlanningEngineRun(models.TransientModel):
    _inherit = 'mrp.planning.engine.run'

    def action_planning_engine_run_by_mrp_parameter_id(self):
        message = self.planning_engine_run_by_parameter_id(self.warehouse_id,self.mrp_parameter_id)
        t_mess_id = False
        if message:
            t_mess_id = self.env["mrp.planning.message"].create({'name': message}).id
        else:
            t_mess_id = self.env["mrp.planning.message"].create({'name': 'no planning result'}).id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Planning Run Results'),
            'res_model': "mrp.planning.message",
            'res_id': t_mess_id,
            'views': [(self.env.ref('mrp_planning_engine.view_mrp_planning_message_form').id, "form")],
            'target': 'new',
        }
    
    
    def planning_engine_run_by_parameter_id(self, warehouse_id,mrp_parameter_id):
        message = False
        self._mrp_cleanup_by_mrp_parameter_id(warehouse_id,mrp_parameter_id)
        mrp_lowest_llc = self._low_level_code_calculation_by_mrp_parameter_id(warehouse_id,mrp_parameter_id)
        self._mrp_initialisation_by_mrp_parameter_id(warehouse_id,mrp_parameter_id)
        mrp_counter, mrp_planned_order_counter = self._mrp_calculation_by_mrp_parameter_id(mrp_lowest_llc, warehouse_id,mrp_parameter_id)
        rop_counter, rop_planned_order_counter = self._rop_calculation_by_mrp_parameter_id(warehouse_id,mrp_parameter_id)
        counter = mrp_counter + rop_counter
        # logger.info('##############')
        # logger.info(mrp_planned_order_counter)
        # logger.info(rop_planned_order_counter)
        # logger.info('#############')
        planned_order_counter = mrp_planned_order_counter + rop_planned_order_counter
        message = _('planned products: %r ; planned orders: %r' %(counter, planned_order_counter))
        if warehouse_id.company_id.forward_planning:
            self._forward_scheduling(warehouse_id)
        return message
    
    def _mrp_cleanup_by_mrp_parameter_id(self, warehouse_id,mrp_parameter_id):
        logger.info("Start MRP Cleanup")
        # domain_element = [("warehouse_id", "=", warehouse_id.id), ("fixed", "=", False), ("mrp_origin", "!=", "st")]
        # domain_element = ['&','&',"&",('mrp_parameter_id','=',mrp_parameter_id.id),("warehouse_id", "=", warehouse_id.id), ("fixed", "=", False),("mrp_type",'!=','d')]
        domain_element = ['&','&',('mrp_parameter_id','=',self.mrp_parameter_id.id),("warehouse_id", "=", self.warehouse_id.id), ("fixed", "=", False)]
        mrp_element_ids = self.env["mrp.element"].search(domain_element)
        for mrp_element in mrp_element_ids:
            if not mrp_element.parent_product_id:
                mrp_element.unlink()
            elif mrp_element.parent_product_id and mrp_element.mrp_type != 'd' and not mrp_element.fixed:
                mrp_element.unlink()
            else:
                next

        # self.env["mrp.element"].search(domain_element).unlink()
        # # domain_order = [("warehouse_id", "=", warehouse_id.id), ("fixed", "=", False)]
        domain_order = [("mrp_parameter_id", "=", mrp_parameter_id.id), ("fixed", "=", False)]
        self.env["mrp.planned.order"].search(domain_order).unlink()
        logger.info("End MRP Cleanup")
        return True

    def mrp_cleanup_element_by_mrp_parameter_id(self):
        logger.info("Start MRP Cleanup Element")
        # domain_element = [("warehouse_id", "=", warehouse_id.id), ("fixed", "=", False), ("mrp_origin", "!=", "st")]
        # domain_element = ['&','&',"&",('mrp_parameter_id','=',self.mrp_parameter_id.id),("warehouse_id", "=", self.warehouse_id.id), ("fixed", "=", False),("mrp_origin","in",["so","di"]),("parent_product_id",'=',False)]
        # # domain_element = ['&','&',"&",('mrp_parameter_id','=',self.mrp_parameter_id.id),("warehouse_id", "=", self.warehouse_id.id), ("fixed", "=", False),("mrp_type",'!=','st')]
        # mrp_element_ids = self.env["mrp.element"].search(domain_element)
        # self.env["mrp.element"].search(domain_element).unlink()
        domain_element = ['&','&',('mrp_parameter_id','=',self.mrp_parameter_id.id),("warehouse_id", "=", self.warehouse_id.id), ("fixed", "=", False)]
        mrp_element_ids = self.env["mrp.element"].search(domain_element)
        delete_count = 0
        for mrp_element in mrp_element_ids:
            if not mrp_element.parent_product_id:
                # mrp_element.unlink()
                # logger.info(mrp_element)
                delete_count += 1
            elif mrp_element.parent_product_id and mrp_element.mrp_type != 'd' and not mrp_element.fixed:
                # mrp_element.unlink()
                # logger.info(mrp_element)
                delete_count += 1
            else:
                # next
                logger.info(mrp_element)
        logger.info(len(mrp_element_ids))
        
        raise UserError(_(delete_count))
        # logger.info("End MRP Cleanup Element")
        # return True

    def mrp_cleanup_parameter_by_mrp_parameter_id(self):
        logger.info("Start MRP Cleanup Parameter")
        # domain_order = [("warehouse_id", "=", warehouse_id.id), ("fixed", "=", False)]
        domain_order = [("mrp_parameter_id", "=", self.mrp_parameter_id.id), ("fixed", "=", False)]
        self.env["mrp.planned.order"].search(domain_order).unlink()
        # mrp_parameter_ids = self.env["mrp.planned.order"].search(domain_order)
        # raise UserError(_(mrp_parameter_ids))
        logger.info("End MRP Cleanup Parameter")
        return True
    
    
    def _low_level_code_calculation_by_mrp_parameter_id(self, warehouse_id,mrp_parameter_id):
        logger.info("Start low level code calculation")
        counter = 0
        # reorder point
        llc = -1
        mrp_parameter_llc_minus = self.env["mrp.parameter"].search(['&',("id", "=",mrp_parameter_id.id),("warehouse_id", "=", warehouse_id.id),("mrp_type", "=", 'R')])
        logger.info("MRP Parameter Minus LLC")
        logger.info(mrp_parameter_id.product_id.id)
        logger.info(mrp_parameter_llc_minus)
        logger.info("MRP Parameter Minus LLC")
        if mrp_parameter_llc_minus:
            mrp_parameter_llc_minus.write({"llc": llc})
        parameters = self.env["mrp.parameter"].search([("llc", "=", llc)])
        if parameters:
            counter = len(parameters)
        log_msg = "Low level code -1 finished - Nbr. products: %s" % counter
        logger.info(log_msg)
        # MRP
        llc = 0
        mrp_parameter_llc = self.env["mrp.parameter"].search(['&',("id", "=",mrp_parameter_id.id),("warehouse_id", "=", warehouse_id.id),("mrp_type", "=", 'M')])
        if mrp_parameter_llc:
            logger.info("MRP Parameter LLC")
            logger.info(mrp_parameter_llc)
            logger.info(mrp_parameter_id.product_id.id)
            mrp_parameter_llc.write({"llc": llc})
            logger.info("MRP Parameter LLC")
        parameters = self.env["mrp.parameter"].search([("llc", "=", llc)])
        if parameters:
            counter = len(parameters)
        log_msg = "Low level code 0 finished - Nbr. products: %s" % counter
        logger.info(log_msg)
        while counter:
            llc += 1
            parameters = self.env["mrp.parameter"].search([("llc", "=", llc - 1)])
            product_ids = parameters.product_id.ids
            product_template_ids = parameters.product_id.product_tmpl_id.ids
            bom_lines = self.env["mrp.bom.line"].search([("product_id", "in", product_ids),("bom_id.product_tmpl_id", "in", product_template_ids)])
            products = bom_lines.mapped("product_id")
            self.env["mrp.parameter"].search([("product_id", "in", products.ids),("warehouse_id", "=", warehouse_id.id),("mrp_type", "=", 'M')]).write({"llc": llc})
            counter = self.env["mrp.parameter"].search_count([("llc", "=", llc)])
            log_msg = "Low level code {} finished - Nbr. products: {}".format(llc, counter)
            logger.info(log_msg)
        mrp_lowest_llc = llc
        logger.info("End low level code calculation")
        return mrp_lowest_llc
    
    
    def _mrp_initialisation_by_mrp_parameter_id(self, warehouse_id,mrp_parameter_id):
        logger.info("Start MRP initialisation")
        mrp_parameters = self.env["mrp.parameter"].search(['&',('id','=',mrp_parameter_id.id),("warehouse_id", "=", warehouse_id.id), ("trigger", "=", "auto")])
        for mrp_parameter in mrp_parameters:
            self._init_mrp_element(mrp_parameter)
        logger.info("End MRP initialisation")
    
    def _mrp_calculation_by_mrp_parameter_id(self, mrp_lowest_llc, warehouse_id,mrp_parameter_id):
        logger.info("Start MRP calculation")
        counter = planned_order_counter = llc = 0
        stock_mrp = 0.0
        release_date = mrp_date = False
        #forward_mode_indicator = False
        logger.info(mrp_lowest_llc)
        logger.info(warehouse_id.id)
        while mrp_lowest_llc > llc:
            mrp_parameters = self.env["mrp.parameter"].search([("llc", "=", llc),('id','=',mrp_parameter_id.id),("warehouse_id", "=", warehouse_id.id), ("trigger", "=", "auto")])
            logger.info(len(mrp_parameters))
            # for mrp_parameter in mrp_parameters:
            #     logger.info(mrp_parameter.id)
            llc += 1
            for mrp_parameter in mrp_parameters:
                # logger.info("1111111")
                # logger.info(mrp_parameter)
                
                stock_mrp = mrp_parameter._compute_qty_available()
                # stock_mrp = 100
                # logger.info(stock_mrp)
                # logger.info(mrp_parameter.mrp_minimum_stock)
                # logger.info("1111111")
                if stock_mrp < mrp_parameter.mrp_minimum_stock:
                    qty_to_order = mrp_parameter.mrp_minimum_stock - stock_mrp
                    lot_qty = mrp_parameter._get_lot_qty(qty_to_order)
                    mrp_date = mrp_parameter._get_finish_date(datetime.now())
                    # planned order creation
                    planned_order = self.create_backward_planned_order(mrp_parameter, mrp_date, lot_qty)
                    # logger.info('#######')
                    # logger.info(planned_order)
                    # logger.info(mrp_parameter.mrp_element_ids)
                    # logger.info('#######')
                    planned_order_counter += 1
                    stock_mrp += lot_qty
                for mrp_element_id in mrp_parameter.mrp_element_ids:
                    # logger.info('zzzz')
                    # logger.info(mrp_element_id)
                    # logger.info('zzzzz')
                    qty_to_order = mrp_parameter.mrp_minimum_stock - stock_mrp - mrp_element_id.mrp_qty
                    
                    if qty_to_order > 0.0:
                        mrp_date = datetime.strptime(str(mrp_element_id.mrp_date), DEFAULT_SERVER_DATE_FORMAT) #from date to datetime
                        if mrp_parameter.lot_qty_method == 'S':
                            last_date = warehouse_id.calendar_id.plan_days(int(mrp_parameter.mrp_coverage_days), mrp_date, True) # datetime
                            domain_damand = [
                                ('mrp_date', '>=', mrp_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                ('mrp_date', '<=', last_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                ('mrp_type', '=', 'd'),
                                ]
                            demand_records = mrp_parameter.mrp_element_ids.filtered_domain(domain_damand)
                            demand_mrp_qty = sum(demand_records.mapped('mrp_qty'))
                            qty_to_order = mrp_parameter.mrp_minimum_stock - stock_mrp - demand_mrp_qty
                        lot_qty = mrp_parameter._get_lot_qty(qty_to_order)
                        if mrp_parameter.mrp_safety_time > 0 and warehouse_id.calendar_id:
                            mrp_date = warehouse_id.calendar_id.plan_days(-int(mrp_parameter.mrp_safety_time+1), mrp_date, True)
                        # planned order creation
                        if lot_qty > 0:
                            planned_order = self.create_backward_planned_order(mrp_parameter, mrp_date, lot_qty)
                            planned_order_counter += 1
                            # strategy 50
                            if mrp_parameter.demand_indicator == "50" and mrp_element_id.mrp_origin == "di" and mrp_element_id.doc_qty==-mrp_element_id.mrp_qty:
                                planned_order.conversion_indicator = False
                            # strategy 20
                            if mrp_parameter.demand_indicator == "20":
                                planned_order.mto_origin = mrp_element_id.mto_origin
                                planned_order.mrp_element_down_ids.mto_origin = mrp_element_id.mto_origin
                        stock_mrp += mrp_element_id.mrp_qty + lot_qty
                    else:
                        stock_mrp += mrp_element_id.mrp_qty
                counter += 1
            log_msg = "MRP Calculation LLC {} Finished - Nr. products: {}".format(llc - 1, counter)
            logger.info(log_msg)
        logger.info("End MRP calculation")
        return counter, planned_order_counter
        
    def _rop_calculation_by_mrp_parameter_id(self, warehouse_id,mrp_parameter_id):
        logger.info("Start ROP calculation")
        counter = planned_order_counter = 0
        stock_mrp = 0.0
        mrp_element_in_records = False
        mrp_element_out_ready_records = False
        mrp_element_out_all_records = False
        #forward_mode_indicator = True
        mrp_element_in_qty = 0.0
        mrp_element_out_ready_qty = 0.0
        mrp_element_out_all_qty = 0.0
        mrp_parameters = self.env["mrp.parameter"].search([("llc", "=", -1),('id','=',mrp_parameter_id.id),("warehouse_id", "=", warehouse_id.id), ("trigger", "=", "auto")])
        for mrp_parameter in mrp_parameters:
            to_date = mrp_parameter._get_finish_date(datetime.now()) + timedelta(days=1)
            to_date = to_date.date()
            stock_mrp = mrp_parameter._compute_qty_available()
            domain_mrp_element_in = [
                        ('mrp_parameter_id', '=', mrp_parameter.id),
                        ('mrp_type', '=', 's'),
                        ('mrp_date', '<=', to_date),
                        ]
            mrp_element_in_records = self.env["mrp.element"].search(domain_mrp_element_in)
            if mrp_element_in_records:
                mrp_element_in_qty = sum(mrp_element_in_records.mapped('mrp_qty'))
            if mrp_parameter.requirements_method == 'N':
                stock_mrp += mrp_element_in_qty
            elif mrp_parameter.requirements_method == 'C':
                domain_mrp_element_out_ready = [
                    ('mrp_parameter_id', '=', mrp_parameter.id),
                    ('mrp_type', '=', 'd'),
                    ('mrp_date', '<=', to_date),
                    ('state','=', 'assigned'),
                    ]
                mrp_element_out_ready_records = self.env["mrp.element"].search(domain_mrp_element_out_ready)
                if mrp_element_out_ready_records:
                    mrp_element_out_ready_qty = sum(mrp_element_out_ready_records.mapped('mrp_qty'))
                stock_mrp += mrp_element_in_qty + mrp_element_out_ready_qty
            elif mrp_parameter.requirements_method == 'A':
                domain_mrp_element_out_all = [
                    ('mrp_parameter_id', '=', mrp_parameter.id),
                    ('mrp_type', '=', 'd'),
                    ('mrp_date', '<=', to_date),
                    ]
                mrp_element_out_all_records = self.env["mrp.element"].search(domain_mrp_element_out_all)
                if mrp_element_out_all_records:
                    mrp_element_out_all_qty = sum(mrp_element_out_all_records.mapped('mrp_qty'))
                stock_mrp += mrp_element_in_qty + mrp_element_out_all_qty
            if stock_mrp is None:
                continue
            if float_compare(stock_mrp, mrp_parameter.mrp_threshold_stock, precision_rounding=mrp_parameter.product_id.uom_id.rounding) < 0:
                lot_qty = mrp_parameter._get_lot_qty(mrp_parameter.mrp_threshold_stock - stock_mrp) or 0.0
                if lot_qty > 0:
                    planned_order = self.create_forward_planned_order(mrp_parameter, datetime.now(), lot_qty)
                    planned_order_counter += 1
            counter += 1
            log_msg = "ROP Calculation Finished - Nbr. products: %s" % counter
            logger.info(log_msg)
        logger.info("End ROP calculation")
        return counter, planned_order_counter