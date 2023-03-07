from odoo import models
import math

class StockingPicking(models.Model):
  _inherit="stock.picking"


  def ceil(self,number1,number2):
        return math.ceil(number1/number2)