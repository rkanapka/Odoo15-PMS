from odoo import models, fields


class RequestWizardAssign(models.TransientModel):
    _name = 'request.wizard.assign'
    _description = 'Request Wizard: Assign'

    def _default_user_id(self):
        return self.env.user

    request_ids = fields.Many2many(
        'request.request', string='Requests', required=True)
    user_id = fields.Many2one(
        'res.users', string="User", default=_default_user_id, required=True)
    partner_id = fields.Many2one(
        'res.partner', related="user_id.partner_id",
        readonly=True, store=False)
    comment = fields.Text()

    def _prepare_assign(self):
        """ Prepare assign data

            This method have to prepare dict with data to be written to request
        """
        self.ensure_one()
        return {
            'user_id': self.user_id.id,
        }

    def _do_assign(self):
        self.ensure_one()
        self.request_ids.with_context(
            assign_comment=self.comment
        ).write(self._prepare_assign())

    def do_assign(self):
        self.ensure_one()
        self.request_ids.ensure_can_assign()
        self._do_assign()
        if self.comment:
            for request in self.request_ids:
                request.message_post(body=self.comment)
