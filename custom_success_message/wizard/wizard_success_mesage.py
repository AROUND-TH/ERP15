from odoo import models,fields


class WizardSuccessMessage(models.TransientModel):
  _name = 'wizard.success.message'
  _description = 'WizardSuccessMessage'

  message= fields.Text('Message',required=True)


  def action_close(self):
    return {'type':'ir.actions.act_window_close'}