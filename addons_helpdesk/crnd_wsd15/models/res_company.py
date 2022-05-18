from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    request_wsd_public_ui_visibility = fields.Selection(
        selection=[
            ('redirect', 'Redirect to login'),
            ('restrict', 'Restricted UI'),
            ('create-request', 'Allow to create request'),
        ],
        default='redirect')
    request_limit_max_text_size = fields.Integer(default=0)

    request_allowed_upload_file_types = fields.Char()
    request_limit_max_upload_file_size = fields.Integer(default=25)
    request_limit_max_upload_file_size_uom = fields.Selection([
        ('gbytes', 'GB'),
        ('mbytes', 'MB'),
        ('kbytes', 'KB')], default='mbytes')

    def _get_request_max_upload_file_size(self):
        if self.request_limit_max_upload_file_size_uom == 'gbytes':
            return self.request_limit_max_upload_file_size * 1024 * 1024 * 1024
        if self.request_limit_max_upload_file_size_uom == 'mbytes':
            return self.request_limit_max_upload_file_size * 1024 * 1024
        if self.request_limit_max_upload_file_size_uom == 'kbytes':
            return self.request_limit_max_upload_file_size * 1024
        return self.request_limit_max_upload_file_size

    def _get_request_max_upload_file_size_label(self):
        label = (
            dict(self.env['res.company']._fields[
                'request_limit_max_upload_file_size_uom'].selection).get(
                    self.request_limit_max_upload_file_size_uom))
        return (
            "%(value)s%(label)s" % {
                'value': self.request_limit_max_upload_file_size,
                'label': label,
            })

    def _get_allowed_upload_file_types(self):
        return self.request_allowed_upload_file_types.split(',')
