from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
import zipfile
import io
import base64
import logging

_logger = logging.getLogger(__name__)

class PrintPdfWizard(models.TransientModel):
  _name = 'print.pdf.wizard'
  _description = 'Print PDF Wizard'

  res_ids = fields.Char('Ids', required=True)
  res_model = fields.Char('Model', required=True)
  report_id = fields.Many2one('ir.actions.report', string='PDF', required=True, domain="[('model', '=', res_model)]")

  def print_pdf(self):
    model = self.env[self.res_model]
    model_name = model._description
    
    print_action = self.env['print.action'].create({
      'res_ids': self.res_ids,
      'res_model': self.res_model,
      'report_id': self.report_id.id,
      'name': _(f"Export {model_name} du {fields.Datetime.now()}"),
    })
    
    return {
      'type': 'ir.actions.act_window',
      'res_model': 'print.action',
      'res_id': print_action.id,
      'view_mode': 'form',
      'target': 'current',
    }