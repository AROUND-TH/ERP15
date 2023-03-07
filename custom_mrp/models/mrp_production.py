# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging
import requests
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ks_datetime_start = fields.Datetime("Basic Start Date")
    ks_datetime_end = fields.Datetime("Basic End Date")
    date_actual_start_wo = fields.Datetime('WO Start Date')
    date_actual_finished_wo = fields.Datetime('WO End Date')

    def _generate_backorder_productions(self, close_mo):
        backorders = super()._generate_backorder_productions(close_mo)
        for workorder in backorders.workorder_ids:
            workorder.state = 'ready'
        return backorders

    def compute_product_multi_lot(self,product_id,product_qty,product_uom_id):
        stock_production_lot_env = self.env['stock.production.lot']
        stock_production_lot_rec = stock_production_lot_env.search(['&','&',('product_id','=',product_id),('name','!=',' '),('expiration_date','>=',self.date_planned_start_pivot)],order='id asc')
        if not stock_production_lot_rec:
            stock_production_lot_env.create({
                "product_id":product_id,
                "product_qty":product_qty,
                "product_uom_id":product_uom_id,
            })
        stock_production_lot_rec = stock_production_lot_env.search(['&','&',('product_id','=',product_id),('name','!=',' '),('expiration_date','>=',self.date_planned_start_pivot)],order='id asc')
        quantity_expected = product_qty
        lot_ids = []
        for lot in stock_production_lot_rec:
            if quantity_expected > lot.product_qty and lot.product_qty > 0:
                quantity_lot_expected = quantity_expected
                quantity_done = lot.product_qty
                lot_qty = lot.product_qty
                quantity_expected = quantity_expected - lot.product_qty
                vals = {
                    "quantity_expected":quantity_lot_expected,
                    "quantity_done":quantity_done,
                    "quantity_lot":lot_qty,
                    "lot_id":lot.id,
                }
                lot_ids.append(vals)
            elif quantity_expected < lot.product_qty and quantity_expected > 0:
                quantity_lot_expected = quantity_expected
                quantity_done = quantity_expected
                lot_qty = lot.product_qty
                quantity_expected = 0
                vals = {
                    "quantity_expected":quantity_lot_expected,
                    "quantity_done":quantity_done,
                    "quantity_lot":lot_qty,
                    "lot_id":lot.id,
                }
                lot_ids.append(vals)
            else:
                next
        return lot_ids

    def create_product_multi_lot(self,product_id,product_qty,product_uom_id,lot):
        stock_production_lot_env = self.env['stock.production.lot']
        stock_production_lot_rec = stock_production_lot_env.search([('product_id','=',product_id)],order='id asc')
        
        if not stock_production_lot_rec:
            stock_lot_id = stock_production_lot_env.create({
                "product_id":product_id,
                "product_qty":product_qty,
                "product_uom_id":product_uom_id,
                "name":lot
            })
            
        stock_production_lot_rec = stock_production_lot_env.search([('product_id','=',product_id)],order='id asc')
       
        quantity_expected = product_qty
        lot_ids = []
        for lot in stock_production_lot_rec:
            if quantity_expected > lot.product_qty and lot.product_qty > 0:
                quantity_lot_expected = quantity_expected
                quantity_done = lot.product_qty
                lot_qty = lot.product_qty
                quantity_expected = quantity_expected - lot.product_qty
                vals = {
                    "quantity_expected":quantity_lot_expected,
                    "quantity_done":quantity_done,
                    "quantity_lot":lot_qty,
                    "lot_id":lot.id,
                }
                lot_ids.append(vals)
            elif quantity_expected < lot.product_qty and quantity_expected > 0:
                quantity_lot_expected = quantity_expected
                quantity_done = quantity_expected
                lot_qty = lot.product_qty
                quantity_expected = 0
                vals = {
                    "quantity_expected":quantity_lot_expected,
                    "quantity_done":quantity_done,
                    "quantity_lot":lot_qty,
                    "lot_id":lot.id,
                }
                lot_ids.append(vals)
            else:
                next
        return lot_ids

    def compute_product_lot(self,product_id,quantity,product_uom_id):
        stock_production_lot_env = self.env['stock.production.lot']
        stock_production_lot_expected = stock_production_lot_env.search([('product_id','=',product_id)],limit=1,order="id asc")
        if not stock_production_lot_expected:
            stock_production_lot_env.create({
                "product_id":product_id,
                "product_qty":quantity,
                "product_uom_id":product_uom_id,
            })
        stock_production_lot_expected = stock_production_lot_env.search([('product_id','=',product_id)],limit=1,order="id asc")
        if stock_production_lot_expected:
            return stock_production_lot_expected.id

    def action_open_wizard_stock_move(self):
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        stock_production_lot_obj = self.env['stock.production.lot']
        stock_location_obj = self.env['stock.location']
        product_product_obj = self.env['product.product']
        stock_move_ids = []
        stock_move_env = self.env['stock.move']
        stock_location_obj = self.env['stock.location']
        production_consumption_dest_location_id = stock_location_obj.search(['&',('name','=','Production'),('usage','=','production')])
        uom_obj = self.env['uom.uom']
        accessToken = self.authenticate_middleware()
        if accessToken:
            # name = "BP101/PMM/00135"
            manufacturing_order = str(self.name).replace("/","%2F")
            # manufacturing_order = str(name).replace("/","%2F")
            tb_goodreceivefgs_uri = middleware_uri+"/api/services/app/TbGoodreceiveFgs/GetAll?ManufacturingOrderNoFilter="+manufacturing_order
            # _logger.info(tb_goodreceivefgs_uri)
            headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
            response_goodreceive = None
            content_goodreceive = requests.get(tb_goodreceivefgs_uri,params=None,headers=headers)
            # _logger.info(content)
            if content_goodreceive.status_code == 200 and 'application/json' in content_goodreceive.headers['Content-Type']:
                response_goodreceive = content_goodreceive.json()
                # _logger.info(response)
            else:
                _logger.info("{}".format(content_goodreceive.status_code,content_goodreceive.headers['Content-Type'].split(";")[0]))
            if response_goodreceive and response_goodreceive.get("success",False) == True:
                mo_items = response_goodreceive.get("result",{}).get("items")
                if len(mo_items) > 0:
                    # _logger.info("#########################")
                    # _logger.info("Found on Middleware")
                    for move_raw in self.move_raw_ids:
                        tb_movement_rms_uri = middleware_uri+"/api/services/app/TbMovementsRms/GetAll?ManufacturingOrderNoFilter="+manufacturing_order+"&ComponentCodeFilter="+move_raw.product_id.default_code
                        response_movement_rms = None
                        content_movement_rms = requests.get(tb_movement_rms_uri,params=None,headers=headers)
                        # _logger.info("#################################")
                        # _logger.info(tb_movement_rms_uri)
                        # _logger.info(move_raw.product_id.default_code)
                        # _logger.info("#################################")
                        if content_movement_rms.status_code == 200 and 'application/json' in content_movement_rms.headers['Content-Type']:
                            response_movement_rms = content_movement_rms.json()
                            items = response_movement_rms.get("result",{}).get("items")
                            for item in items:
                                tbMovementsRm = item.get("tbMovementsRm",{})
                                componentCode = tbMovementsRm.get("componentCode")
                                lot = tbMovementsRm.get("lot") or " "
                                quantity_rm = tbMovementsRm.get("entryQnt")
                                product_id = product_product_obj.search([('default_code','=',componentCode)])
                                uom_id = None
                                if tbMovementsRm.get("entryUom") == 'KG':
                                    uom_id = uom_obj.search(['&',('name','=','KG'),('category_id.name','=','Weight')],limit=1)
                                else:
                                    uom_id = uom_obj.search([('name','=',tbMovementsRm.get("entryUom"))],limit=1)
                                if product_id and product_id.tracking == 'lot':
                                    stock_move_id = stock_move_env.search(['&',('raw_material_production_id','=',self.id),('product_id','=',move_raw.product_id.id)],limit=1)
                                    product_lots = self.compute_product_multi_lot(product_id.id,quantity_rm,uom_id.id)
                                    for product in product_lots:
                                        stock_move_ids.append((0,0,{
                                            'move_id':stock_move_id.id,
                                            'product_id':product_id.id,
                                            'product_uom_qty':product["quantity_done"],
                                            'location_id':move_raw.picking_type_id.default_location_src_id.id,
                                            'location_dest_id':production_consumption_dest_location_id.id,
                                            'lot_id':product["lot_id"],
                                            'quantity_done':product["quantity_done"],
                                            'product_uom':uom_id.id,
                                            'tracking':product_id.tracking,
                                        }))
                                else:
                                    stock_move_ids.append((0,0,{
                                        'move_id':stock_move_id.id,
                                        'product_id':product_id.id,
                                        'product_uom_qty':quantity_rm,
                                        'location_id':move_raw.picking_type_id.default_location_src_id.id,
                                        'location_dest_id':production_consumption_dest_location_id.id,
                                        'quantity_done':quantity_rm,
                                        'product_uom':uom_id.id,
                                        'tracking':product_id.tracking,
                                    }))
                else:
                    for rec in self.move_raw_ids:
                        stock_move_id = stock_move_env.search(['&',('raw_material_production_id','=',self.id),('product_id','=',rec.product_id.id)],limit=1)
                        if rec.product_id and rec.product_id.tracking=='lot':
                            product_lots = self.compute_product_multi_lot(rec.product_id.id,rec.product_uom_qty,rec.product_uom.id)
                            for product in product_lots:
                                stock_move_ids.append((0,0,{
                                    'move_id':stock_move_id.id,
                                    'product_id':rec.product_id.id,
                                    'product_uom_qty':product["quantity_done"],
                                    'location_id':rec.picking_type_id.default_location_src_id.id,
                                    'location_dest_id':production_consumption_dest_location_id.id,
                                    'lot_id':product["lot_id"],
                                    'quantity_done':product["quantity_done"],
                                    'product_uom':rec.product_uom.id,
                                    'tracking':rec.product_id.tracking,
                                }))
                        else:
                            stock_move_ids.append((0,0,{
                                'move_id':stock_move_id.id,
                                'product_id':rec.product_id.id,
                                'product_uom_qty':rec.product_uom_qty,
                                'location_id':rec.picking_type_id.default_location_src_id.id,
                                'location_dest_id':production_consumption_dest_location_id.id,
                                'quantity_done':rec.product_uom_qty,
                                'product_uom':rec.product_uom.id,
                                'tracking':rec.product_id.tracking,
                            }))
        # _logger.info(stock_move_ids)
        return {
            'name': _('Consumption'),
            'view_mode': 'form',
            'res_model': 'wizard.consumption.stock.move',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                "default_doc_id":self.id,
                "default_mrp_production_id":self.id,
                "default_name":self.name,
                "default_consumption_stock_move_line_ids":stock_move_ids
            }
        }
    
    # @api.onchange('ks_datetime_start','ks_datetime_end')
    # def ks_compute_work_duration(self):
    #     _logger.info("########################")
    #     _logger.info("Compute ks work duration")
    #     _logger.info("########################")
    #     for rec in self:
    #         rec.ks_work_duration = 0
    #         if rec.date_planned_finished_wo and rec.date_planned_start_wo:
    #             if (rec.date_planned_finished_wo - rec.date_planned_start_wo).days == 0:
    #                 rec.ks_work_duration = str(rec.date_planned_finished_wo - rec.date_planned_start_wo) + " hours"
    #             else:
    #                 rec.ks_work_duration = str(rec.date_planned_finished_wo - rec.date_planned_start_wo)
    
    # @api.onchange('state')
    # def compute_ks_start_end_date(self):
    #     _logger.info("########################")
    #     _logger.info("Compute ks date start end")
    #     _logger.info("########################")
    #     for rec in self:
    #         if rec.date_planned_start_wo and rec.date_planned_finished_wo:
    #             rec.ks_datetime_start = rec.date_planned_start_wo
    #             rec.ks_datetime_end = rec.date_planned_finished_wo
    
    # def button_plan(self):
    #     res = super().button_plan()
    #     for rec in self:
    #         _logger.info(rec.date_planned_start_wo)
    #         _logger.info(rec.date_planned_finished_wo)
    #         if rec.date_planned_start_wo and rec.date_planned_finished_wo:
    #             rec.ks_datetime_start = rec.date_planned_start_wo
    #             rec.ks_datetime_end = rec.date_planned_finished_wo
    #     return res
    
    def conv_time_float(self,value):
        # _logger.info(value)
        if value != "":
            vals = value.split(':')
            t, minutes = divmod(float(vals[0]),60)
            t, seconds = divmod(float(vals[1]),60)
            minutes = minutes / 60.0
            seconds = seconds / 60.0
            return minutes + seconds
        else:
            return 0.0

    def conv_float_time_to_string(self,value):
        float_time_string = " 00:00:00"
        if value > 0:
            time_result = '{0:02.0f}:{1:02.0f}'.format(*divmod(value *60,60))
            # _logger.info(time_result)
            float_time_string = " "+time_result+":00"
        return float_time_string
    
    def authenticate_middleware(self):
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        middleware_username = self.env['ir.config_parameter'].sudo().get_param('middleware_api_username')
        middleware_password = self.env['ir.config_parameter'].sudo().get_param('middleware_api_password')
        authenticate_url = middleware_uri+"/api/TokenAuth/Authenticate"
        data = {
            "UserNameOrEmailAddress":middleware_username,
            "Password":middleware_password
        }
        response = None
        content = requests.post(authenticate_url,json=data)
        if content.status_code == 200:
            content.encoding = 'utf-8'
            response = content.json()
            # _logger.info(response)
        if response and response.get("success",False) == True:
            accessToken = response.get("result",{}).get("accessToken")
            return accessToken
    
    def get_middleware_goodreceive_fgs(self):
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        stock_production_lot_obj = self.env['stock.production.lot']
        stock_move_obj = self.env['stock.move']
        stock_move_line_obj = self.env['stock.move.line']
        stock_picking_obj = self.env['stock.picking']
        stock_location_obj = self.env['stock.location']
        product_product_obj = self.env['product.product']
        workcenter_obj = self.env['mrp.workcenter']
        uom_obj = self.env['uom.uom']
        production_consumption_dest_location_id = stock_location_obj.search(['&',('name','=','Production'),('usage','=','production')])
        accessToken = self.authenticate_middleware()
        if accessToken:
            # name = "BP101/PMM/00135"
            manufacturing_order = str(self.name).replace("/","%2F")
            # manufacturing_order = str(name).replace("/","%2F")
            tb_goodreceivefgs_uri = middleware_uri+"/api/services/app/TbGoodreceiveFgs/GetAll?ManufacturingOrderNoFilter="+manufacturing_order
            # _logger.info(tb_goodreceivefgs_uri)
            
            headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
            response_goodreceive = None
            content_goodreceive = requests.get(tb_goodreceivefgs_uri,params=None,headers=headers)
            
            # _logger.info(content)
            if content_goodreceive.status_code == 200 and 'application/json' in content_goodreceive.headers['Content-Type']:
                response_goodreceive = content_goodreceive.json()
                # _logger.info(response)
            else:
                _logger.info("{}".format(content_goodreceive.status_code,content_goodreceive.headers['Content-Type'].split(";")[0]))
                self.action_log_to_middleware(accessToken,self.name,"Not found job order on middleware")
            if response_goodreceive.get("result",{}).get("totalCount") == 0:
                self.action_log_to_middleware(accessToken,self.name,"Not found job order on middleware")
                return
            else:
                if response_goodreceive and response_goodreceive.get("success",False) == True:
                    mo_items = response_goodreceive.get("result",{}).get("items")
                    if len(mo_items) > 0:
                        mo_item = mo_items[0].get("tbGoodreceiveFg",{})
                        # _logger.info(mo_items)
                        quantity = round(mo_item.get("backflquant"))
                        unit_name = mo_item.get("unit")
                        lot = mo_item.get("lot") or " "
                        working_time = mo_item.get("workingTime")
                        setup_time = mo_item.get("setupTime") or "00:00"
                        workcenter = mo_item.get("workCenter")
                        working_float_time = 0.00
                        setup_float_time = 0.00
                        recordId = mo_item.get("id")
                        # _logger.info(setup_time)
                        if workcenter:
                            mrp_workcenter_id = workcenter_obj.search([('name','=',workcenter)])
                            if not mrp_workcenter_id:
                                self.action_log_to_middleware(accessToken,self.name,"Not found workcenter in odoo")
                        if working_time:
                            working_float_time = self.conv_time_float(working_time)
                            
                        if setup_time != "00:00":
                            setup_float_time = self.conv_time_float(setup_time)
                        finished_time = setup_float_time + working_float_time
                        finished_time_string = self.conv_float_time_to_string(finished_time)
                        date_planned_start_pivot = datetime.strptime(mo_item.get("postDate")+" 00:00:00",'%d/%m/%Y %H:%M:%S')
                        date_planned_finished_pivot = datetime.strptime(mo_item.get("postDate")+str(finished_time_string),'%d/%m/%Y %H:%M:%S')
                        fg_lot_id = stock_production_lot_obj.search([('name','=',lot),('product_id','=',self.product_id.id)])
                    
                        if not fg_lot_id:
                            self.action_log_to_middleware(accessToken,self.name,"Not found Lot Number for FG on Odoo")
                            fg_lot_id = stock_production_lot_obj.create({
                                "name":lot,
                                "product_id":self.product_id.id,
                            })
                        for rec in self:
                            rec.product_qty = quantity
                            rec.qty_producing = quantity
                            rec.qty_produced = quantity
                            rec.date_planned_start_pivot = date_planned_start_pivot
                            rec.lot_producing_id = fg_lot_id.id
                        for workorder in self.workorder_ids:
                            if mrp_workcenter_id and workorder.workcenter_id.id == mrp_workcenter_id.id:
                                workorder.write({
                                    "date_planned_start_wo":date_planned_start_pivot,
                                })
                                if working_float_time:
                                    workorder.write({
                                    "duration":working_float_time
                                    })
                                if setup_float_time > 0.00:
                                    workorder.write({
                                    "overall_duration":working_float_time+setup_float_time
                                    })

                        self.action_update_flag_read_middleware(accessToken,recordId,"TbGoodreceiveFgs")
                            
                        tb_movement_rms_uri = middleware_uri+"/api/services/app/TbMovementsRms/GetAll?ManufacturingOrderNoFilter="+manufacturing_order
                        response_movement_rms = None
                        content_movement_rms = requests.get(tb_movement_rms_uri,params=None,headers=headers)
                        if content_movement_rms.status_code == 200 and 'application/json' in content_movement_rms.headers['Content-Type']:
                            response_movement_rms = content_movement_rms.json()
                            # _logger.info(response_movement_rms)
                            items = response_movement_rms.get("result",{}).get("items")
                            for item in items:
                                tbMovementsRm = item.get("tbMovementsRm",{})
                                componentCode = tbMovementsRm.get("componentCode")
                                
                                quantity_rm = tbMovementsRm.get("entryQnt")
                                recordComponentId = tbMovementsRm.get("id")
                                product_id = product_product_obj.search([('default_code','=',componentCode)])
                                if not product_id:
                                    self.action_log_to_middleware(accessToken,self.name,"Not found component code: "+str(componentCode)+" on odoo")
                                uom_id = None
                                if tbMovementsRm.get("entryUom") == 'KG':
                                    uom_id = uom_obj.search(['&',('name','=','KG'),('category_id.name','=','Weight')],limit=1)
                                else:
                                    uom_id = uom_obj.search([('name','=',tbMovementsRm.get("entryUom"))],limit=1)
                                # _logger.info(uom_id.id)
                                if not uom_id:
                                    self.action_log_to_middleware(accessToken,self.name,"Not Found Product UOM in odoo")
                                stock_move_obj = self.env['stock.move']
                                move_line_ids = []
                                location_id = None
                                if product_id and product_id.tracking == 'lot':                                    
                                    for stock_move in self.move_raw_ids:
                                        if stock_move.product_id.id == product_id.id:
                                            location_id = stock_move.location_id.id
                                            product_lots = self.compute_product_multi_lot(product_id.id,quantity_rm,uom_id.id)
                                            for product in product_lots:
                                                move_line_ids.append((0,0,{
                                                    'production_id':self._origin.id,
                                                    'reference':self.name,
                                                    'product_id':product_id.id,
                                                    'location_id':location_id,
                                                    'location_dest_id':production_consumption_dest_location_id.id,
                                                    'lot_id':product['lot_id'],
                                                    'qty_done':product["quantity_done"],
                                                    'product_uom_id':uom_id.id,
                                                    'description_picking':'From Middleware Function',
                                                    "date":self.date_planned_start_pivot,
                                                    'tracking':product_id.tracking,
                                                }))
                                                stock_move_obj.write({
                                                    "move_line_ids":move_line_ids
                                                })
                                                self.action_update_flag_read_middleware(accessToken,recordComponentId,"TbMovementsRms")
                                                move_line_ids = []
                                        else:
                                            next
                                                
                                else:
                                    for product in product_lots:
                                        move_line_ids.append((0,0,{
                                            'product_id':product_id.id,
                                            'product_uom_qty':quantity_rm,
                                            'location_id':location_id,
                                            'location_dest_id':production_consumption_dest_location_id.id,
                                            'qty_done':quantity_rm,
                                            'product_uom_id':uom_id.id,
                                            'description_picking':'From Middleware Function',
                                            "date":self.date_planned_start_pivot,
                                            'tracking':product_id.tracking,
                                        }))
                                    stock_move_obj.write({
                                        "move_line_ids":move_line_ids
                                    })
                                    move_line_ids = []

    def create_or_edit_mos_exist_middleware(self):
        accessToken = self.authenticate_middleware()
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        if accessToken:
            manufacturing_order = str(self.name).replace("/","%2F")
            # manufacturing_order = str(name).replace("/","%2F")
            mos_uri = middleware_uri+"/api/services/app/Mos/GetAll?ManufacturingOrderNoFilter="+manufacturing_order
            mos_create_or_update_uri = middleware_uri+"/api/services/app/Mos/CreateOrEdit"
            headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
            response_mos = None
            content_mos = requests.get(mos_uri,params=None,headers=headers)
            
            # _logger.info(content)
            if content_mos.status_code == 200 and 'application/json' in content_mos.headers['Content-Type']:
                response_mos = content_mos.json()
                # _logger.info(response)
            else:
                _logger.info("{}".format(content_mos.status_code,content_mos.headers['Content-Type'].split(";")[0]))
            if response_mos.get("result",{}).get("totalCount") == 0:
                data = {
                    "manufacturingOrderNo":self.name,
                    "bomId":self.bom_id.id,
                    "plant":self.picking_type_id.warehouse_id.code,
                    "totalPlordQty":self.qty_producing,
                    "baseUom":self.product_uom_id.name,
                    "prodStartDate":str(datetime.strftime(self.date_planned_start_pivot+timedelta(hours=7),'%d/%m/%Y %H:%M:%S')),
                    "prodFinishDate":str(datetime.strftime(self.date_planned_finished_pivot+timedelta(hours=7),'%d/%m/%Y %H:%M:%S')),
                    "productionType":self.x_studio_production_type_bom,
                    "uomSize":str(self.product_id.weight)+" "+self.product_id.weight_uom_name,
                }
                response_mos = None
                content_mos = requests.post(mos_uri,json=data,headers=headers)
                # _logger.info(content)
                if content_mos.status_code == 200 and 'application/json' in content_mos.headers['Content-Type']:
                    response_mos = content_mos.json()
                    return
            

    def action_interface_middleware_mos(self):
        accessToken = self.authenticate_middleware()
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        if accessToken:
            manufacturing_order = str(self.name).replace("/","%2F")
            # manufacturing_order = str(name).replace("/","%2F")
            mos_uri = middleware_uri+"/api/services/app/Mos/GetAll?ManufacturingOrderNoFilter="+manufacturing_order
            mos_create_or_update_uri = middleware_uri+"/api/services/app/Mos/CreateOrEdit"
            headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
            response_mos = None
            content_mos = requests.get(mos_uri,params=None,headers=headers)
            
            # _logger.info(content)
            if content_mos.status_code == 200 and 'application/json' in content_mos.headers['Content-Type']:
                response_mos = content_mos.json()
                # _logger.info(response)
            else:
                _logger.info("{}".format(content_mos.status_code,content_mos.headers['Content-Type'].split(";")[0]))
            if response_mos.get("result",{}).get("totalCount") == 0:
                _logger.info("If totalCount == 0")
                data = {
                    "manufacturingOrderNo":self.name,
                    "bomId":self.bom_id.id,
                    "plant":self.picking_type_id.warehouse_id.code,
                    "totalPlordQty":self.qty_producing,
                    "baseUom":self.product_uom_id.name,
                    "prodStartDate":str(datetime.strftime(self.date_planned_start_pivot+timedelta(hours=7),'%d/%m/%Y %H:%M:%S')),
                    "prodFinishDate":str(datetime.strftime(self.date_planned_finished_pivot+timedelta(hours=7),'%d/%m/%Y %H:%M:%S')),
                    "productionType":self.x_studio_production_type_bom,
                    "materialCode":self.product_id.default_code,
                    "uomSize":str(self.product_id.weight)+" "+self.product_id.weight_uom_name,
                }
                response_mos = None
                content_mos = requests.post(mos_create_or_update_uri,json=data,headers=headers)
                # _logger.info(content)
                if content_mos.status_code == 200 and 'application/json' in content_mos.headers['Content-Type']:
                    response_mos = content_mos.json()
                    return
            else:
                mos_items = response_mos.get("result",{}).get("items")
                mos_item = mos_items[0].get("mo",{})
                flagRead = mos_item.get("flagRead")
                mosID = mos_item.get("id")
                if flagRead == 'Y':
                    _logger.info("If flagRead == Y")
                    return
                else:
                    _logger.info("If flagRead == N")
                    data = {
                        "manufacturingOrderNo":self.name,
                        "bomId":self.bom_id.id,
                        "plant":self.picking_type_id.warehouse_id.code,
                        "totalPlordQty":self.qty_producing,
                        "baseUom":self.product_uom_id.name,
                        "prodStartDate":str(datetime.strftime(self.date_planned_start_pivot+timedelta(hours=7),'%d/%m/%Y %H:%M:%S')),
                        "prodFinishDate":str(datetime.strftime(self.date_planned_finished_pivot+timedelta(hours=7),'%d/%m/%Y %H:%M:%S')),
                        "productionType":self.x_studio_production_type_bom,
                        "uomSize":str(self.product_id.weight)+" "+self.product_id.weight_uom_name,
                        "materialCode":self.product_id.default_code,
                        "id":mosID,
                    }
                    response_mos = None
                    content_mos = requests.post(mos_create_or_update_uri,json=data,headers=headers)
                    # _logger.info(content)
                    if content_mos.status_code == 200 and 'application/json' in content_mos.headers['Content-Type']:
                        response_mos = content_mos.json()
                        return
            

    def action_confirm(self):
        res = super(MrpProduction, self).action_confirm()
        if not res:
            return res
        for rec in self:
            rec.create_or_edit_mos_exist_middleware()
        return res
    
    def get_middleware_goodreceive_fgs_before_update_wo_confirmation(self):
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        stock_production_lot_obj = self.env['stock.production.lot']
        stock_move_obj = self.env['stock.move']
        stock_move_line_obj = self.env['stock.move.line']
        stock_picking_obj = self.env['stock.picking']
        stock_location_obj = self.env['stock.location']
        product_product_obj = self.env['product.product']
        workcenter_obj = self.env['mrp.workcenter']
        uom_obj = self.env['uom.uom']
        production_consumption_dest_location_id = stock_location_obj.search(['&',('name','=','Production'),('usage','=','production')])
        accessToken = self.authenticate_middleware()
        working_float_time = 0.00
        setup_float_time = 0.00
        is_middleware_data = False
        if accessToken:
            # name = "BP101/PMM/00135"
            manufacturing_order = str(self.name).replace("/","%2F")
            tb_goodreceivefgs_uri = middleware_uri+"/api/services/app/TbGoodreceiveFgs/GetAll?ManufacturingOrderNoFilter="+manufacturing_order
            # _logger.info(tb_goodreceivefgs_uri)
            headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
            response_goodreceive = None
            content_goodreceive = requests.get(tb_goodreceivefgs_uri,params=None,headers=headers)
            # _logger.info(content)
            if content_goodreceive.status_code == 200 and 'application/json' in content_goodreceive.headers['Content-Type']:
                response_goodreceive = content_goodreceive.json()
                # _logger.info(response)
            else:
                _logger.info("{}".format(content_goodreceive.status_code,content_goodreceive.headers['Content-Type'].split(";")[0]))
            if response_goodreceive and response_goodreceive.get("success",False) == True:
                mo_items = response_goodreceive.get("result",{}).get("items")
                if len(mo_items) > 0:
                    mo_item = mo_items[0].get("tbGoodreceiveFg",{})
                    # _logger.info(mo_items)
                    quantity = round(mo_item.get("backflquant"))
                    unit_name = mo_item.get("unit")
                    lot = mo_item.get("lot")
                    working_time = mo_item.get("workingTime")
                    setup_time = mo_item.get("setupTime") or "00:00"
                    workcenter = mo_item.get("workCenter")
                    is_middleware_data = True
                    # _logger.info(setup_time)
                    if workcenter:
                        mrp_workcenter_id = workcenter_obj.search([('name','=',workcenter)])
                    if working_time:
                        working_float_time = self.conv_time_float(working_time)
                    if setup_time != "00:00":
                        setup_float_time = self.conv_time_float(setup_time)

                    date_planned_start_pivot = datetime.strptime(mo_item.get("postDate")+" 00:00:00",'%d/%m/%Y %H:%M:%S')
                    fg_lot_id = stock_production_lot_obj.search([('name','=',lot),('product_id','=',self.product_id.id)])
                    if not fg_lot_id:
                        fg_lot_id = stock_production_lot_obj.create({
                            "name":lot,
                            "product_id":self.product_id.id,
                        })
                    for rec in self:
                        rec.product_qty = quantity
                        rec.qty_producing = quantity
                        rec.qty_produced = quantity
                        rec.date_planned_start_pivot = date_planned_start_pivot
                        rec.lot_producing_id = fg_lot_id.id
        return is_middleware_data,working_float_time,setup_float_time

    
    def action_open_mrp_confirmation_wizard(self):
        # action = self.env.ref('mrp_shop_floor_control.action_mrp_confirmation').read()[0]
        is_middleware_data,working_float_time,setup_float_time = self.get_middleware_goodreceive_fgs_before_update_wo_confirmation()
        default_working_duration = 0.00
        default_setup_duration = 0.00
        default_is_middleware_data = False
        if working_float_time:
            default_working_duration = working_float_time
        if setup_float_time:
            default_setup_duration = setup_float_time
        if is_middleware_data:
            default_is_middleware_data = is_middleware_data
        return {
            'view_type':'form',
            'view_mode':'form',
            'res_model':'mrp.confirmation',
            'target':'new',
            'type':'ir.actions.act_window',
            'context':{
                'default_production_id':self._origin.id,
                'default_setup_duration':default_setup_duration,
                'default_working_duration':default_working_duration,
                'default_is_middleware_data':default_is_middleware_data,
                },
        }
    
    def action_log_to_middleware(self,accessToken,jobName,message):
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        authenticate_url = middleware_uri+"/api/services/app/TbLogs/Create"
        headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
        data = {
            "jobName":"Odoo "+str(jobName),
            "message":message
        }
        response = None
        content = requests.post(authenticate_url,json=data,headers=headers)
        if content.status_code == 200:
            content.encoding = 'utf-8'
            response = content.json()
            # _logger.info(response)
        if response and response.get("success",False) == True:
            # accessToken = response.get("result",{}).get("accessToken")
            # return accessToken
            return
        return

    def action_update_flag_read_middleware(self,accessToken,recordId,tableName):
        middleware_uri = self.env['ir.config_parameter'].sudo().get_param('middleware_api_uri')
        authenticate_url = middleware_uri+"/api/services/app/"+tableName+"/CreateOrEdit"
        headers = {
                'Authorization': 'Bearer %s' %(accessToken)
            }
        data = {
            "id":recordId,
            "flagRead":"Y",
        }
        response = None
        content = requests.post(authenticate_url,json=data,headers=headers)
        if content.status_code == 200:
            content.encoding = 'utf-8'
            response = content.json()
        if response and response.get("success",False) == True:
            return
        return
