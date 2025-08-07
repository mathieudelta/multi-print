import time
from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
import zipfile
import io
import base64

class PrintAction(models.TransientModel):
  _name = 'print.action'
  _description = 'Print Action'
  _inherit = 'mail.thread'

  name = fields.Char('Name', required=True)
  res_ids = fields.Char('Ids', required=True)
  res_model = fields.Char('Model', required=True)
  report_id = fields.Many2one('ir.actions.report', string='PDF', required=True, domain="[('model', '=', res_model)]")
  status = fields.Selection([
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('error', 'Error'),
  ], string='Status', default='pending')
  status_display = fields.Html(string='Status', compute='_compute_status_display')
  attachment_id = fields.Many2one('ir.attachment', string='Generated Attachment')
  error_message = fields.Text('Error Message')
  processed_count = fields.Integer('Processed Count', default=0)
  total_count = fields.Integer('Total Count', compute='_compute_total_count')

  @api.depends('status')
  def _compute_status_display(self):
    for record in self:
      if record.status == 'pending':
        record.status_display = """<span class="status-loader"></span>"""
      elif record.status == 'completed':
        record.status_display = """<span>✅</span>"""
      else:
        record.status_display = """<span>❌</span>"""

  @api.depends('res_ids')
  def _compute_total_count(self):
    for record in self:
      if record.res_ids:
        ids = safe_eval(record.res_ids)
        record.total_count = len(ids)
      else:
        record.total_count = 0

  def cron_print_actions(self):
    start_time = time.time()
    max_execution_time = 60 
    print_actions = self.search([('status', '=', 'pending')], limit=5)
    for print_action in print_actions:
      print_action.print_pdf()
      if time.time() - start_time >= max_execution_time:
        break

  def print_pdf(self):
    try:
      ids = safe_eval(self.res_ids)
      max_execution_time = 60  # 60 seconds
      start_time = time.time()
      
      # Get all existing PDF attachments for this print action
      existing_attachments = self.env['ir.attachment'].search([
        ('res_model', '=', 'print.action'),
        ('res_id', '=', self.id),
        ('name', 'like', '%.pdf')
      ])
      
      # Calculate how many PDFs we need to generate
      already_processed = len(existing_attachments)
      remaining_ids = ids[already_processed:]
      
      if not remaining_ids:
        # All PDFs are generated, create the zip file
        return self._create_zip_from_attachments()
      
      # Process PDFs until time limit is reached
      processed_in_batch = 0
      for id in remaining_ids:
        # Check if we've exceeded the time limit
        if time.time() - start_time >= max_execution_time:
          break
          
        entry = self.env[self.res_model].browse(int(id))
        pdf_content, dummy = self.env['ir.actions.report']._render_qweb_pdf(self.report_id, [entry.id])
        
        # Create individual PDF attachment
        pdf_name = safe_eval(self.report_id.print_report_name, {'object': entry}) + '.pdf'
        self.env['ir.attachment'].create({
          'name': pdf_name,
          'datas': base64.b64encode(pdf_content),
          'res_model': 'print.action',
          'res_id': self.id,
        })
        
        processed_in_batch += 1
      
      # Update processed count
      new_processed_count = already_processed + processed_in_batch
      self.write({
        'processed_count': new_processed_count,
      })
      
      if new_processed_count == self.total_count and time.time() - start_time < max_execution_time:
        self._create_zip_from_attachments()
      
      return True;
        
    except Exception as e:
      # Update status and store error message
      self.write({
        'status': 'error',
        'error_message': str(e),
        'attachment_id': False,  # Clear attachment if there was an error
      })
      
      # Re-raise the exception to show it to the user
      raise

  def _create_zip_from_attachments(self):
    """Create a zip file containing all PDF attachments"""
    try:
      # Get all PDF attachments for this print action
      pdf_attachments = self.env['ir.attachment'].search([
        ('res_model', '=', 'print.action'),
        ('res_id', '=', self.id),
        ('name', 'like', '%.pdf')
      ])
      
      if not pdf_attachments:
        raise Exception("No PDF attachments found to create zip file")
      
      # Create zip file
      zip_bytes_io = io.BytesIO()
      with zipfile.ZipFile(zip_bytes_io, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for attachment in pdf_attachments:
          pdf_content = base64.b64decode(attachment.datas)
          zipped.writestr(attachment.name, pdf_content)
      
      zip_file_base64 = zip_bytes_io.getvalue()
      
      # Create zip attachment
      zip_attachment = self.env['ir.attachment'].create({
        'name': 'pdf.zip',
        'datas': base64.b64encode(zip_file_base64),
        'res_model': 'print.action',
        'res_id': self.id,
      })
      
      # Update print action
      self.write({
        'attachment_id': zip_attachment.id,
        'status': 'completed',
        'error_message': False,
      })
      
      self._notify_user()
      
      zip_bytes_io.close()
      
      return {
        'type': 'ir.actions.act_window',
        'res_model': 'ir.attachment',
        'res_id': zip_attachment.id,
        'view_mode': 'form',
        'target': 'current',
      }
      
    except Exception as e:
      self.write({
        'status': 'error',
        'error_message': str(e),
      })
      raise

  def _notify_user(self):
    self.message_post(
      body=_("Your zip file is ready to download."),
      message_type='comment',
      partner_ids=[self.create_uid.partner_id.id],
    )