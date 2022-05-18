# pylint:disable=too-many-lines
import logging
from datetime import datetime
from odoo import models, fields, api, tools, _, http, exceptions, SUPERUSER_ID
from odoo.addons.generic_mixin15 import pre_write, post_write, pre_create
from odoo.osv import expression
from ..tools.utils import html2text
from ..constants import (
    TRACK_FIELD_CHANGES,
    REQUEST_TEXT_SAMPLE_MAX_LINES,
    KANBAN_READONLY_FIELDS,
    MAIL_REQUEST_TEXT_TMPL,
    AVAILABLE_PRIORITIES,
    AVAILABLE_IMPACTS,
    AVAILABLE_URGENCIES,
    PRIORITY_MAP,
)

_logger = logging.getLogger(__name__)


class RequestRequest(models.Model):
    _name = "request.request"
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'generic.mixin.track.changes',
        'generic.tag.mixin',
        'generic.mixin.get.action',
    ]
    _description = 'Request'
    _order = 'date_created DESC'
    _needaction = True

    name = fields.Char(
        required=True, index=True, readonly=True, default="New", copy=False)
    help_html = fields.Html(
        "Help", related="type_id.help_html", readonly=True)
    category_help_html = fields.Html(
        related='category_id.help_html', readonly=True, string="Category help")
    stage_help_html = fields.Html(
        "Stage help", related="stage_id.help_html", readonly=True)
    instruction_html = fields.Html(
        related='type_id.instruction_html',
        readonly=True, string='Instruction')
    note_html = fields.Html(
        related='type_id.note_html', readonly=True, string="Note")
    active = fields.Boolean(default=True, index=True)

    # Priority
    _priority = fields.Char(
        default='3', readonly=True,
        string='Priority (Technical)')
    priority = fields.Selection(
        selection=AVAILABLE_PRIORITIES,
        tracking=True,
        index=True,
        store=True,
        compute='_compute_priority',
        inverse='_inverse_priority',
        help="Actual priority of request"
    )
    impact = fields.Selection(
        selection=AVAILABLE_IMPACTS,
        index=True
    )
    urgency = fields.Selection(
        selection=AVAILABLE_URGENCIES,
        index=True
    )
    is_priority_complex = fields.Boolean(
        related='type_id.complex_priority', readonly=True)

    # Type and stage related fields
    type_id = fields.Many2one(
        'request.type', 'Type', ondelete='restrict',
        required=True, index=True, tracking=True,
        help="Type of request")
    type_color = fields.Char(related="type_id.color", readonly=True)
    kind_id = fields.Many2one(
        'request.kind', related='type_id.kind_id',
        store=True, index=True, readonly=True,
        help="Kind of request")
    category_id = fields.Many2one(
        'request.category', 'Category', index=True,
        required=False, ondelete="restrict", tracking=True,
        help="Category of request")
    channel_id = fields.Many2one(
        'request.channel', 'Channel', index=True, required=False,
        default=lambda self: self.env.ref(
            'generic_request15.request_channel_other', raise_if_not_found=False),
        help="Channel of request")
    stage_id = fields.Many2one(
        'request.stage', 'Stage', ondelete='restrict',
        required=True, index=True, tracking=True, copy=False)
    stage_type_id = fields.Many2one(
        'request.stage.type', related="stage_id.type_id", string="Stage Type",
        index=True, readonly=True, store=True)
    stage_bg_color = fields.Char(
        compute="_compute_stage_colors", string="Stage Background Color")
    stage_label_color = fields.Char(
        compute="_compute_stage_colors")
    last_route_id = fields.Many2one('request.stage.route', 'Last Route')
    closed = fields.Boolean(
        related='stage_id.closed', store=True, index=True, readonly=True)
    can_be_closed = fields.Boolean(
        compute='_compute_can_be_closed', readonly=True)
    is_assigned = fields.Boolean(
        compute="_compute_is_assigned", store=True, readonly=True)

    kanban_state = fields.Selection(
        selection=[
            ('normal', 'In Progress'),
            ('blocked', 'Blocked'),
            ('done', 'Ready for next stage')],
        required='True',
        default='normal',
        tracking=True,
        help="A requests kanban state indicates special"
             " situations affecting it:\n"
             " * Grey is the default situation\n"
             " * Red indicates something is preventing the"
             "progress of this request\n"
             " * Green indicates the request is ready to be pulled"
             "to the next stage")

    # 12.0 compatability. required to generate xmlid for this field
    tag_ids = fields.Many2many()

    # Is this request new (does not have ID yet)?
    # This field could be used in domains in views for True and False leafs:
    # [1, '=', 1] -> True,
    # [0, '=', 1] -> False
    is_new_request = fields.Integer(
        compute='_compute_is_new_request', readonly=True, default=1)

    # UI change restriction fields
    can_change_request_text = fields.Boolean(
        compute='_compute_can_change_request_text', readonly=True,
        compute_sudo=False)
    can_change_assignee = fields.Boolean(
        compute='_compute_can_change_assignee', readonly=True,
        compute_sudo=False)
    can_change_author = fields.Boolean(
        compute='_compute_can_change_author', readonly=True,
        compute_sudo=False)
    can_change_category = fields.Boolean(
        compute='_compute_can_change_category', readonly=True,
        compute_sudo=False)
    can_change_deadline = fields.Boolean(
        compute='_compute_can_change_deadline', readonly=True,
        compute_sudo=False)
    next_stage_ids = fields.Many2many(
        'request.stage', compute="_compute_next_stage_ids", readonly=True)

    # Request data fields
    request_text = fields.Html(required=True)
    response_text = fields.Html(required=False)
    request_text_sample = fields.Text(
        compute="_compute_request_text_sample", tracking=True,
        string='Request text')

    deadline_date = fields.Date('Deadline')
    deadline_state = fields.Selection(selection=[
        ('ok', 'Ok'),
        ('today', 'Today'),
        ('overdue', 'Overdue')], compute='_compute_deadline_state')
    date_created = fields.Datetime(
        'Created', default=fields.Datetime.now, readonly=True, copy=False)
    date_closed = fields.Datetime('Closed Date', readonly=True, copy=False)
    date_assigned = fields.Datetime('Assigned', readonly=True, copy=False)
    date_moved = fields.Datetime('Moved', readonly=True, copy=False)
    created_by_id = fields.Many2one(
        'res.users', 'Created by User', readonly=True, ondelete='restrict',
        default=lambda self: self.env.user, index=True,
        help="Request was created by this user", copy=False)
    moved_by_id = fields.Many2one(
        'res.users', 'Moved by', readonly=True, ondelete='restrict',
        copy=False)
    closed_by_id = fields.Many2one(
        'res.users', 'Closed by', readonly=True, ondelete='restrict',
        copy=False, help="Request was closed by this user")
    partner_id = fields.Many2one(
        'res.partner', 'Partner', index=True, tracking=True,
        ondelete='restrict', help="Partner related to this request")
    author_id = fields.Many2one(
        'res.partner', 'Author', index=True, required=False,
        ondelete='restrict', tracking=True,
        domain=[('is_company', '=', False)],
        default=lambda self: self.env.user.partner_id,
        help="Author of this request")
    user_id = fields.Many2one(
        'res.users', 'Assigned to',
        ondelete='restrict', tracking=True, index=True,
        help="User responsible for next action on this request.")

    # Email support
    email_from = fields.Char(
        'Email', help="Email address of the contact", index=True,
        readonly=True)
    email_cc = fields.Text(
        'Global CC', readonly=True,
        help="These email addresses will be added to the CC field "
             "of all inbound and outbound emails for this record "
             "before being sent. "
             "Separate multiple email addresses with a comma")
    author_name = fields.Char(
        readonly=True,
        help="Name of author based on incoming email")

    message_discussion_ids = fields.One2many(
        'mail.message', 'res_id', string='Discussion Messages', store=False,
        compute="_compute_message_discussion_ids", compute_sudo=False)
    original_message_id = fields.Char(
        help='Technical field. '
             'ID of original message that started this request.')
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        domain=[('res_model', '=', 'request.request')],
        string='Attachments')

    instruction_visible = fields.Boolean(
        compute='_compute_instruction_visible', default=False,
        compute_sudo=False)

    # We have to explicitly set compute_sudo to True to avoid access errors
    activity_date_deadline = fields.Date(compute_sudo=True)

    # Events
    request_event_ids = fields.One2many(
        'request.event', 'request_id', 'Events', readonly=True)
    request_event_count = fields.Integer(
        compute='_compute_request_event_count', readonly=True)

    # Timesheets
    timesheet_line_ids = fields.One2many(
        'request.timesheet.line', 'request_id')
    timesheet_planned_amount = fields.Float(
        help="Planned time")
    timesheet_amount = fields.Float(
        compute='_compute_timesheet_line_data',
        readonly=True, store=True,
        help="Time spent")
    timesheet_remaining_amount = fields.Float(
        compute='_compute_timesheet_line_data',
        readonly=True, store=True,
        help="Remaining time")
    timesheet_progress = fields.Float(
        compute='_compute_timesheet_line_data',
        readonly=True, store=True,
        help="Request progress, calculated as the ratio of time spent "
             "to planned time")
    timesheet_start_status = fields.Selection(
        [('started', 'Started'),
         ('not-started', 'Not Started')],
        compute='_compute_timesheet_start_status', readonly=True)
    use_timesheet = fields.Boolean(
        related='type_id.use_timesheet', readonly=True)

    author_related_request_open_count = fields.Integer(
        compute='_compute_related_a_p_request_ids')
    author_related_request_closed_count = fields.Integer(
        compute='_compute_related_a_p_request_ids')

    partner_related_request_open_count = fields.Integer(
        compute='_compute_related_a_p_request_ids')
    partner_related_request_closed_count = fields.Integer(
        compute='_compute_related_a_p_request_ids')

    # Project Integration
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    project_id = fields.Many2one('project.project', string="Project", help="Project related to Request")
    is_project_required = fields.Boolean(related='company_id.is_project_required', readonly=True)
    odoo_version = fields.Selection(
        related="project_id.odoo_version", string="Odoo Version", help="Odoo Version filled in Project", readonly=True
    )
    task_ids = fields.One2many('project.task', 'request_id', string="Tasks")

    _sql_constraints = [
        ('name_uniq',
         'UNIQUE (name)',
         'Request name must be unique.'),
    ]

    @api.model
    def default_get(self, fields_list):
        res = super(RequestRequest, self).default_get(fields_list)

        path = http.request.httprequest.path if http.request else False
        if path and path.startswith('/web') or path == '/web':
            res.update({'channel_id': self.env.ref(
                'generic_request15.request_channel_web').id})
        elif path and path.startswith('/xmlrpc') or path == '/xmlrpc':
            res.update({'channel_id': self.env.ref(
                'generic_request15.request_channel_api').id})
        elif path and path.startswith('/jsonrpc') or path == '/jsonrpc':
            res.update({'channel_id': self.env.ref(
                'generic_request15.request_channel_api').id})

        return res

    @api.depends('deadline_date', 'date_closed')
    def _compute_deadline_state(self):
        now = datetime.now().date()
        for rec in self:
            date_deadline = fields.Date.from_string(
                rec.deadline_date) if rec.deadline_date else False
            date_closed = fields.Date.from_string(
                rec.date_closed) if rec.date_closed else False
            if not date_deadline:
                rec.deadline_state = False
                continue

            if date_closed:
                if date_closed <= date_deadline:
                    rec.deadline_state = 'ok'
                else:
                    rec.deadline_state = 'overdue'
            else:
                if date_deadline > now:
                    rec.deadline_state = 'ok'
                elif date_deadline < now:
                    rec.deadline_state = 'overdue'
                elif date_deadline == now:
                    rec.deadline_state = 'today'

    @api.depends('message_ids')
    def _compute_message_discussion_ids(self):
        for request in self:
            request.message_discussion_ids = request.message_ids.filtered(
                lambda r: r.subtype_id == self.env.ref('mail.mt_comment'))

    @api.depends('stage_id', 'stage_id.type_id')
    def _compute_stage_colors(self):
        for rec in self:
            rec.stage_bg_color = rec.stage_id.res_bg_color
            rec.stage_label_color = rec.stage_id.res_label_color

    @api.depends('stage_id.route_out_ids.stage_to_id.closed')
    def _compute_can_be_closed(self):
        for record in self:
            record.can_be_closed = any((
                r.close for r in record.stage_id.route_out_ids))

    @api.depends('request_event_ids')
    def _compute_request_event_count(self):
        for record in self:
            record.request_event_count = len(record.request_event_ids)

    @api.depends()
    def _compute_is_new_request(self):
        for record in self:
            record.is_new_request = int(not bool(record.id))

    def _hook_can_change_request_text(self):
        self.ensure_one()
        return not self.closed

    def _hook_can_change_assignee(self):
        self.ensure_one()
        return not self.closed

    def _hook_can_change_category(self):
        self.ensure_one()
        return self.stage_id == self.type_id.sudo().start_stage_id

    def _hook_can_change_deadline(self):
        self.ensure_one()
        return not self.closed

    def _hook_can_change_author(self):
        self.ensure_one()
        return self.stage_id == self.type_id.sudo().start_stage_id

    @api.depends('type_id', 'stage_id', 'user_id',
                 'partner_id', 'created_by_id', 'category_id')
    def _compute_can_change_request_text(self):
        for rec in self:
            rec.can_change_request_text = rec._hook_can_change_request_text()

    @api.depends('type_id', 'stage_id', 'user_id',
                 'partner_id', 'created_by_id', 'category_id')
    def _compute_can_change_assignee(self):
        for rec in self:
            rec.can_change_assignee = rec._hook_can_change_assignee()

    @api.depends('type_id', 'type_id.start_stage_id', 'stage_id',
                 'user_id', 'partner_id', 'created_by_id', 'request_text',
                 'category_id')
    def _compute_can_change_author(self):
        for record in self:
            if not self.env.user.has_group(
                    'generic_request15.group_request_user_can_change_author'):
                record.can_change_author = False
            else:
                record.can_change_author = record._hook_can_change_author()

    @api.depends('type_id', 'type_id.start_stage_id', 'stage_id')
    def _compute_can_change_category(self):
        for record in self:
            record.can_change_category = record._hook_can_change_category()

    @api.depends('type_id', 'type_id.start_stage_id', 'stage_id',
                 'deadline_date', 'category_id')
    def _compute_can_change_deadline(self):
        for record in self:
            record.can_change_deadline = record._hook_can_change_deadline()

    def _get_next_stage_route_domain(self):
        self.ensure_one()
        return [
            ('request_type_id', '=', self.type_id.id),
            ('stage_from_id', '=', self.stage_id.id),
            ('close', '=', False)
        ]

    @api.depends('type_id', 'stage_id')
    def _compute_next_stage_ids(self):
        for record in self:
            routes = self.env['request.stage.route'].search(
                record._get_next_stage_route_domain())
            record.next_stage_ids = (
                    record.stage_id + routes.mapped('stage_to_id'))

    @api.depends('request_text')
    def _compute_request_text_sample(self):
        for request in self:
            text_list = html2text(request.request_text).splitlines()
            result = []
            while len(result) <= REQUEST_TEXT_SAMPLE_MAX_LINES and text_list:
                line = text_list.pop(0)
                line = line.lstrip('#').strip()
                if not line:
                    continue
                result.append(line)
            request.request_text_sample = "\n".join(result)

    @api.depends('user_id')
    def _compute_instruction_visible(self):
        for rec in self:
            rec.instruction_visible = (
                    (
                            self.env.user == rec.user_id or
                            self.env.user.id == SUPERUSER_ID or
                            self.env.user.has_group(
                                'generic_request15.group_request_manager')
                    ) and (
                            rec.instruction_html and
                            rec.instruction_html != '<p><br></p>'
                    )
            )

    @api.depends('type_id')
    def _compute_is_priority_complex(self):
        for rec in self:
            rec.is_priority_complex = rec.sudo().type_id.complex_priority

    @api.depends('_priority', 'impact', 'urgency')
    def _compute_priority(self):
        for rec in self:
            if rec.is_priority_complex:
                rec.priority = str(
                    PRIORITY_MAP[int(rec.impact)][int(rec.urgency)])
            else:
                rec.priority = rec._priority

    @api.depends('user_id')
    def _compute_is_assigned(self):
        for rec in self:
            rec.is_assigned = bool(rec.user_id)

    # When priority is complex, it is computed from impact and urgency
    # We do not need to write it directly from the field
    def _inverse_priority(self):
        for rec in self:
            if not rec.is_priority_complex:
                rec._priority = rec.priority

    @api.depends('author_id', 'partner_id')
    def _compute_related_a_p_request_ids(self):
        for record in self:
            # Usually this will be called on request form view and thus
            # computed only for one record. So, it will lead only to 4
            # search_counts per request to compute stat
            if record.id and record.author_id:
                record.update({
                    'author_related_request_open_count': self.search_count(
                        [('author_id', '=', record.author_id.id),
                         ('closed', '=', False),
                         ('id', '!=', record.id)]),
                    'author_related_request_closed_count': self.search_count(
                        [('author_id', '=', record.author_id.id),
                         ('closed', '=', True),
                         ('id', '!=', record.id)]),
                })
            else:
                record.update({
                    'author_related_request_open_count': 0,
                    'author_related_request_closed_count': 0,
                })

            if record.id and record.partner_id:
                record.update({
                    'partner_related_request_open_count': self.search_count(
                        [('partner_id', '=', record.partner_id.id),
                         ('closed', '=', False),
                         ('id', '!=', record.id)]),
                    'partner_related_request_closed_count': self.search_count(
                        [('partner_id', '=', record.partner_id.id),
                         ('closed', '=', True),
                         ('id', '!=', record.id)]),
                })
            else:
                record.update({
                    'partner_related_request_open_count': 0,
                    'partner_related_request_closed_count': 0,
                })

    @api.depends('timesheet_line_ids', 'timesheet_line_ids.amount',
                 'timesheet_planned_amount')
    def _compute_timesheet_line_data(self):
        for rec in self:
            timesheet_amount = 0.0
            for line in rec.timesheet_line_ids:
                timesheet_amount += line.amount
            rec.timesheet_amount = timesheet_amount

            if rec.timesheet_planned_amount:
                rec.timesheet_remaining_amount = (
                        rec.timesheet_planned_amount - timesheet_amount)
                rec.timesheet_progress = (
                        100.0 * (timesheet_amount / rec.timesheet_planned_amount))
            else:
                rec.timesheet_remaining_amount = 0.0
                rec.timesheet_progress = 0.0

    @api.depends('timesheet_line_ids', 'timesheet_line_ids.date_start',
                 'timesheet_line_ids.date_end')
    def _compute_timesheet_start_status(self):
        TimesheetLines = self.env['request.timesheet.line']
        domain = expression.AND([
            TimesheetLines._get_running_lines_domain(),
            [('request_id', 'in', self.ids)],
        ])
        grouped = self.env["request.timesheet.line"].read_group(
            domain=domain,
            fields=["id", 'request_id'],
            groupby=['request_id'],
        )
        lines_per_record = {
            group['request_id'][0]: group["request_id_count"]
            for group in grouped
        }

        for record in self:
            if lines_per_record.get(record.id, 0) > 0:
                record.timesheet_start_status = 'started'
            else:
                record.timesheet_start_status = 'not-started'

    def _create_update_from_type(self, r_type, vals):
        # Name update
        if vals.get('name') == "###new###":
            # To set correct name for request generated from mail aliases
            # See code `mail.models.mail_thread.MailThread.message_new` - it
            # attempts to set name if it is empty. So we pass special name in
            # our method overload, and handle it here, to keep all request name
            # related logic in one place
            vals['name'] = False
        if not vals.get('name') and r_type.sequence_id:
            vals['name'] = r_type.sudo().sequence_id.next_by_id()
        elif not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                'request.request.name')

        # Update stage
        if r_type.start_stage_id:
            vals['stage_id'] = r_type.start_stage_id.id
        else:
            raise exceptions.ValidationError(_(
                "Cannot create request of type '%(type_name)s':"
                " This type have no start stage defined!"
            ) % {'type_name': r_type.name})

        # Set default priority
        if r_type.sudo().complex_priority:
            if not vals.get('impact'):
                vals['impact'] = r_type.sudo().default_impact
            if not vals.get('urgency'):
                vals['urgency'] = r_type.sudo().default_urgency
        else:
            if not vals.get('priority'):
                vals['priority'] = r_type.sudo().default_priority

        return vals

    @api.model
    def _add_missing_default_values(self, values):
        if values.get('created_by_id') and 'author_id' not in values:
            # This is required to be present before super call, because
            # 'author_id' has it's own default value, and and unless it is set
            # explicitly, original default value (partner of current user)
            # will be used.
            create_user = self.env['res.users'].sudo().browse(
                values['created_by_id'])
            values = dict(
                values,
                author_id=create_user.partner_id.id)
        res = super(RequestRequest, self)._add_missing_default_values(values)

        if res.get('author_id') and 'partner_id' not in values:
            author = self.env['res.partner'].browse(res['author_id'])
            if author.commercial_partner_id != author:
                res['partner_id'] = author.commercial_partner_id.id
        return res

    @api.model
    def create(self, vals):
        if vals.get('type_id', False):
            r_type = self.env['request.type'].browse(vals['type_id'])
            vals = self._create_update_from_type(r_type, vals)

        self_ctx = self.with_context(mail_create_nolog=False)
        request = super(RequestRequest, self_ctx).create(vals)
        request.trigger_event('created')
        return request

    def _get_generic_tracking_fields(self):
        """ Compute list of fields that have to be tracked
        """
        # TODO: Do we need it? it seems that we have migrated most of code to
        # use pre/post_write decorators
        return super(
            RequestRequest, self
        )._get_generic_tracking_fields() | TRACK_FIELD_CHANGES

    @pre_write('active')
    def _before_active_changed(self, changes):
        if self.env.user.id == SUPERUSER_ID:
            return
        if not self.env.user.has_group(
                'generic_request15.group_request_manager_can_archive_request'):
            raise exceptions.AccessError(_(
                "Operation change active is not allowed!"))

    @pre_write('type_id')
    def _before_type_id_changed(self, changes):
        raise exceptions.ValidationError(_(
            'It is not allowed to change request type'))

    @pre_create('user_id')
    @pre_write('user_id')
    def _before_user_id_changed(self, changes):
        if changes['user_id'].new_val:
            return {'date_assigned': fields.Datetime.now()}
        return {'date_assigned': False}

    @pre_write('stage_id')
    def _before_stage_id_changed(self, changes):
        Route = self.env['request.stage.route']
        old_stage, new_stage = changes['stage_id']
        route = Route.ensure_route(self, new_stage.id)

        vals = {}
        vals['last_route_id'] = route.id
        vals['date_moved'] = fields.Datetime.now()
        vals['moved_by_id'] = self.env.user.id

        if not old_stage.closed and new_stage.closed:
            vals['date_closed'] = fields.Datetime.now()
            vals['closed_by_id'] = self.env.user.id
        elif old_stage.closed and not new_stage.closed:
            vals['date_closed'] = False
            vals['closed_by_id'] = False
        return vals

    @post_write('stage_id')
    def _after_stage_id_changed(self, changes):
        old_stage, new_stage = changes['stage_id']
        event_data = {
            'route_id': self.last_route_id.id,
            'old_stage_id': old_stage.id,
            'new_stage_id': new_stage.id,
        }
        if new_stage.closed and not old_stage.closed:
            self.trigger_event('closed', event_data)
        elif old_stage.closed and not new_stage.closed:
            self.trigger_event('reopened', event_data)
        else:
            self.trigger_event('stage-changed', event_data)

    @post_write('user_id')
    def _after_user_id_changed(self, changes):
        old_user, new_user = changes['user_id']
        event_data = {
            'old_user_id': old_user.id,
            'new_user_id': new_user.id,
            'assign_comment': self.env.context.get('assign_comment', False)
        }
        if not old_user and new_user:
            self.trigger_event('assigned', event_data)
        elif old_user and new_user:
            self.trigger_event('reassigned', event_data)
        elif old_user and not new_user:
            self.trigger_event('unassigned', event_data)

    @post_write('request_text')
    def _after_request_text_changed(self, changes):
        self.trigger_event('changed', {
            'old_text': changes['request_text'][0],
            'new_text': changes['request_text'][1]})

    @post_write('category_id')
    def _after_category_id_changed(self, changes):
        self.trigger_event('category-changed', {
            'old_category_id': changes['category_id'][0].id,
            'new_category_id': changes['category_id'][1].id,
        })

    @post_write('author_id')
    def _after_author_id_changed(self, changes):
        self.trigger_event('author-changed', {
            'old_author_id': changes['author_id'][0].id,
            'new_author_id': changes['author_id'][1].id,
        })

    @post_write('partner_id')
    def _after_partner_id_changed(self, changes):
        self.trigger_event('partner-changed', {
            'old_partner_id': changes['partner_id'][0].id,
            'new_partner_id': changes['partner_id'][1].id,
        })

    @post_write('priority', 'impact', 'urgency')
    def _after_priority_changed(self, changes):
        if 'priority' in changes:
            self.trigger_event('priority-changed', {
                'old_priority': changes['priority'][0],
                'new_priority': changes['priority'][1]})
        if 'impact' in changes:
            old, new = changes['impact']
            old_priority = str(
                PRIORITY_MAP[int(old)][int(self.urgency)])
            new_priority = str(
                PRIORITY_MAP[int(new)][int(self.urgency)])
            self.trigger_event('priority-changed', {
                'old_priority': old_priority,
                'new_priority': new_priority})
            self.trigger_event('impact-changed', {
                'old_impact': old,
                'new_impact': new})
        if 'urgency' in changes:
            old, new = changes['urgency']
            old_priority = str(
                PRIORITY_MAP[int(self.impact)][int(old)])
            new_priority = str(
                PRIORITY_MAP[int(self.impact)][int(new)])
            self.trigger_event('priority-changed', {
                'old_priority': old_priority,
                'new_priority': new_priority})
            self.trigger_event('urgency-changed', {
                'old_urgency': old,
                'new_urgency': new})

    @post_write('deadline_date')
    def _after_deadline_changed(self, changes):
        self.trigger_event('deadline-changed', {
            'old_deadline': changes['deadline_date'][0],
            'new_deadline': changes['deadline_date'][1]})

    @post_write('kanban_state')
    def _after_kanban_state_changed(self, changes):
        self.trigger_event('kanban-state-changed', {
            'old_kanban_state': changes['kanban_state'][0],
            'new_kanban_state': changes['kanban_state'][1]})

    @post_write('active')
    def _after_active_changed(self, changes):
        __, new_active = changes['active']
        if new_active:
            event_code = 'request-unarchived'
        else:
            event_code = 'request-archived'
        self.trigger_event(event_code, {
            'request_active': event_code})

    def _creation_subtype(self):
        """ Determine mail subtype for request creation message/notification
        """
        return self.env.ref('generic_request15.mt_request_created')

    def _track_subtype(self, init_values):
        """ Give the subtypes triggered by the changes on the record according
        to values that have been updated.

        :param init_values: the original values of the record;
                            only modified fields are present in the dict
        :type init_values: dict
        :returns: a subtype xml_id or False if no subtype is triggered
        """
        self.ensure_one()
        if 'stage_id' in init_values:
            init_stage = init_values['stage_id']
            if init_stage and init_stage != self.stage_id and \
                    self.stage_id.closed and not init_stage.closed:
                return self.env.ref('generic_request15.mt_request_closed')
            if init_stage and init_stage != self.stage_id and \
                    not self.stage_id.closed and init_stage.closed:
                return self.env.ref('generic_request15.mt_request_reopened')
            if init_stage != self.stage_id:
                return self.env.ref('generic_request15.mt_request_stage_changed')

        return self.env.ref('generic_request15.mt_request_updated')

    @api.onchange('type_id')
    def onchange_type_id(self):
        """ Set default stage_id
        """
        for request in self:
            if request.type_id and request.type_id.start_stage_id:
                request.stage_id = request.type_id.start_stage_id
            else:
                request.stage_id = self.env['request.stage'].browse([])

            # Set default priority
            if not request.is_priority_complex:
                request.priority = request.type_id.default_priority
            else:
                request.impact = request.type_id.default_impact
                request.urgency = request.type_id.default_urgency

            # Set default text for request
            if self.env.context.get('default_request_text'):
                continue
            if request.type_id and request.type_id.default_request_text:
                request.request_text = request.type_id.default_request_text

    @api.onchange('category_id', 'type_id', 'is_new_request')
    def _onchange_category_type(self):
        if self.type_id and self.category_id and self.is_new_request:
            # Clear type if it does not in allowed type for selected category
            # Or if request category is not selected
            if self.type_id not in self.category_id.request_type_ids:
                self.type_id = False

        res = {'domain': {}}
        domain = res['domain']
        if self.category_id:
            domain['type_id'] = [
                ('category_ids', '=', self.category_id.id),
                ('start_stage_id', '!=', False)]
        else:
            domain['type_id'] = [
                ('category_ids', '=', False),
                ('start_stage_id', '!=', False)]
        if not self.is_new_request:
            domain['category_id'] = [
                ('request_type_ids', '=', self.type_id.id)]
        else:
            domain['category_id'] = []
        return res

    @api.onchange('author_id')
    def _onchange_author_id(self):
        for rec in self:
            if rec.author_id:
                rec.partner_id = self.author_id.parent_id
            else:
                rec.partner_id = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        result = super(RequestRequest, self).fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu)

        # Make type_id and stage_id readonly for kanban mode.
        # this is required to disable kanban drag-and-drop features for this
        # fields, because changing request type or request stage in this way,
        # may lead to broken workflow for requests (no routes to move request
        # to next stage)
        if view_type == 'kanban':
            for rfield in KANBAN_READONLY_FIELDS:
                if rfield in result['fields']:
                    result['fields'][rfield]['readonly'] = True
        return result

    def ensure_can_assign(self):
        for record in self:
            if not record.can_change_assignee:
                raise exceptions.UserError(_(
                    "You can not assign this (%(request)s) request"
                ) % {'request': record.display_name})

    def action_request_assign(self):
        self.ensure_can_assign()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_request_wizard_assign',
            context={'default_request_ids': [(6, 0, self.ids)]})

    def action_request_assign_to_me(self):
        self.ensure_can_assign()
        self.write({'user_id': self.env.user.id})

    # Default notifications
    def _send_default_notification__get_email_from(self, **kw):
        """ To be overloaded to change 'email_from' field for notifications
        """
        return False

    def _send_default_notification__get_context(self, event):
        """ Compute context for default notification
        """
        values = event.get_context()
        values['company'] = self.env.user.company_id
        return values

    def _send_default_notification__get_msg_params(self, **kw):
        return dict(
            composition_mode='mass_mail',
            auto_delete=True,
            auto_delete_message=False,
            parent_id=False,  # override accidental context defaults
            subtype_id=self.env.ref('mail.mt_note').id,
            **kw,
        )

    def _send_default_notification__send(self, template, partners,
                                         event, **kw):
        """ Send default notification

            :param str template: XMLID of template to use for notification
            :param Recordset partners: List of partenrs that have to receive
                                       this notification
            :param Recordset event: Single record of 'request.event'
            :param function lazy_subject: function (self) that have to return
                                          translated string for subject
                                          for notification
        """
        values_g = self._send_default_notification__get_context(event)
        message_data_g = self._send_default_notification__get_msg_params(**kw)
        email_from = self._send_default_notification__get_email_from(**kw)
        if email_from:
            message_data_g['email_from'] = email_from

        # In order to handle translatable subjects, we use specific argument:
        # lazy_subject, which is function that receives 'self' and returns
        # string.
        lazy_subject = message_data_g.pop('lazy_subject', None)

        for partner in partners.sudo():
            # Skip partners without emails to avoid errors
            if not partner.email:
                continue
            values = dict(
                values_g,
                partner=partner,
            )
            self_ctx = self.sudo()

            # remove default author from context
            # This is required to fix bug in generic_request_crm:
            # when use create new request from lead, and there is default
            # author specified in context, then all notification messages use
            # that author as author of message. This way customer notification
            # has customer as author. Next block of code have to fix
            # this issue.
            if self_ctx.env.context.get('default_author_id'):
                new_ctx = dict(self_ctx.env.context)
                new_ctx.pop('default_author_id')
                self_ctx = self_ctx.with_context(new_ctx)

            if partner.lang:
                self_ctx = self_ctx.with_context(lang=partner.sudo().lang)
            message_data = dict(
                message_data_g,
                partner_ids=[(4, partner.id)],
                values=values)
            if lazy_subject:
                message_data['subject'] = lazy_subject(self_ctx)
            self_ctx.message_post_with_view(
                template,
                **message_data)

    def _send_default_notification_created(self, event):
        if not self.sudo().type_id.send_default_created_notification:
            return

        self._send_default_notification__send(
            'generic_request15.message_request_created__author',
            self.sudo().author_id,
            event,
            lazy_subject=lambda self: _(
                "Request %(request)s successfully created!"
            ) % {'request': self.name},
        )

    def _send_default_notification_assigned(self, event):
        if not self.sudo().type_id.send_default_assigned_notification:
            return

        self._send_default_notification__send(
            'generic_request15.message_request_assigned__assignee',
            event.sudo().new_user_id.partner_id,
            event,
            lazy_subject=lambda self: _(
                "You have been assigned to request %(request)s!"
            ) % {'request': self.name},
        )

    def _send_default_notification_closed(self, event):
        if not self.sudo().type_id.send_default_closed_notification:
            return

        self._send_default_notification__send(
            'generic_request15.message_request_closed__author',
            self.sudo().author_id,
            event,
            lazy_subject=lambda self: _(
                "Your request %(request)s has been closed!"
            ) % {'request': self.name},
        )

    def _send_default_notification_reopened(self, event):
        if not self.sudo().type_id.send_default_reopened_notification:
            return

        self._send_default_notification__send(
            'generic_request15.message_request_reopened__author',
            self.sudo().author_id,
            event,
            lazy_subject=lambda self: _(
                "Your request %(request)s has been reopened!"
            ) % {'request': self.name},
        )

    def handle_request_event(self, event):
        """ Place to handle request events
        """
        if event.event_type_id.code in ('assigned', 'reassigned'):
            self._send_default_notification_assigned(event)
        elif event.event_type_id.code == 'created':
            self._send_default_notification_created(event)
        elif event.event_type_id.code == 'closed':
            self._send_default_notification_closed(event)
        elif event.event_type_id.code == 'reopened':
            self._send_default_notification_reopened(event)

    def trigger_event(self, event_type, event_data=None):
        """ Trigger an event.

            :param str event_type: code of event type
            :param dict event_data: dictionary with data to be written to event
        """
        event_type_id = self.env['request.event.type'].get_event_type_id(
            event_type)
        event_data = event_data if event_data is not None else {}
        event_data.update({
            'event_type_id': event_type_id,
            'request_id': self.id,
            'user_id': self.env.user.id,
            'date': fields.Datetime.now(),
        })
        event = self.env['request.event'].sudo().create(event_data)
        self.handle_request_event(event)

    def get_mail_url(self):
        """ Get request URL to be used in mails
        """
        return "/mail/view/request/%s" % self.id

    def _notify_get_groups(self, *args, **kwargs):
        """ Use custom url for *button_access* in notification emails
        """
        self.ensure_one()
        groups = super(RequestRequest, self)._notify_get_groups(
            *args, **kwargs)

        view_title = _('View Request')
        access_link = self.get_mail_url()

        # pylint: disable=unused-variable
        for group_name, group_method, group_data in groups:
            group_data['button_access'] = {
                'title': view_title,
                'url': access_link,
            }

        return groups

    def _message_auto_subscribe_followers(self, updated_values,
                                          default_subtype_ids):
        res = super(RequestRequest, self)._message_auto_subscribe_followers(
            updated_values, default_subtype_ids)

        if updated_values.get('author_id'):
            author = self.env['res.partner'].browse(
                updated_values['author_id'])
            if author.active:
                res.append((
                    author.id, default_subtype_ids, False))
        return res

    def _message_auto_subscribe_notify(self, partner_ids, template):
        # Disable sending mail to assigne, when request was assigned.
        # Custom notification will be sent, see _after_user_id_changed method
        # pylint: disable=useless-super-delegation
        return super(
            RequestRequest,
            self.with_context(mail_auto_subscribe_no_notify=True)
        )._message_auto_subscribe_notify(partner_ids, template)

    def _find_emails_from_msg(self, msg):
        """ Find emais from email message.
            Check 'to' and 'cc' fields

            :return: List of emails
        """
        # TODO: do we need to parse 'to' header here?
        return tools.email_split(
            (msg.get('to') or '') + ',' + (msg.get('cc') or ''))

    def _get_or_create_partner_from_email(self, email, force_create=False):
        """ This method will try to find partner by email.
            And if "force_create" is set to True, then it will try to create
            new partner (contact) for this email
        """
        partner_ids = self._mail_find_partner_from_emails(
            [email], force_create=force_create)
        if partner_ids:
            return partner_ids[0].id
        return False

    @api.model
    def _ensure_email_from_is_not_alias(self, msg_dict):
        """ Check that email is not come from alias.

            This needed to protect from infinite loops.
            If email come to odoo from alias managed by odoo,
            then it seems that there is going on something strage.
        """
        __, from_email = (
            self.env['res.partner']._parse_partner_name(msg_dict['from'])
            if msg_dict.get('from')
            else (False, False)
        )
        email_addr, email_domain = from_email.split('@')

        alias_domain = self.sudo().env["ir.config_parameter"].get_param(
            "mail.catchall.domain")
        if not alias_domain:
            # If alias domain is no configured, then assume that everything is
            # ok
            return
        if alias_domain.lower().strip() != email_domain.lower().strip():
            # If email come from different domain then everything seems to be
            # ok
            return

        check_domain = [
            ('alias_name', 'ilike', email_addr),
        ]
        if self.env['mail.alias'].search(check_domain, limit=1):
            raise ValueError(
                "Cannot create request from email sent from alias '%s'!\n"
                "Possible infinite loop, thus this email will be skipped!\n"
                "Subject: %s\n"
                "From: %s\n"
                "To: %s\n"
                "Message ID: %s" % (from_email,
                                    msg_dict.get('subject'),
                                    msg_dict.get('from'),
                                    msg_dict.get('to'),
                                    msg_dict.get('message_id')))

    def _validate_incoming_message(self, msg_dict):
        """ Validate incoming message, and if it is not acceptable,
            then raise error.

            This method could be overriden in third-party modules
            to provide extra validation options.
        """
        self._ensure_email_from_is_not_alias(msg_dict)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        self._validate_incoming_message(msg_dict)
        company = self.env.user.company_id
        Partner = self.env['res.partner']
        defaults = dict(custom_values) if custom_values is not None else {}

        # Ensure we have message_id
        if not msg_dict.get('message_id'):
            msg_dict['message_id'] = self.env['mail.message']._get_message_id(
                msg_dict)

        # Compute default request text
        request_text = MAIL_REQUEST_TEXT_TMPL % {
            'subject': msg_dict.get('subject', _("No Subject")),
            'body': msg_dict.get('body', ''),
        }

        author_name, author_email = (
            Partner._parse_partner_name(msg_dict['from'])
            if msg_dict.get('from')
            else (False, False)
        )

        # Update defaults with partner and created_by_id if possible
        defaults.update({
            'name': "###new###",  # Spec name to avoid using subj as req name
            'request_text': request_text,
            'original_message_id': msg_dict['message_id'],
            'email_from': author_email,
            'email_cc': msg_dict.get('cc', ''),
        })
        author_id = msg_dict.get('author_id')

        # Create author from email if needed
        if not author_id and company.request_mail_create_partner_from_email:
            author_id = self._get_or_create_partner_from_email(
                msg_dict['from'], force_create=True)
            if author_id:
                msg_dict['author_id'] = author_id

        if author_id:
            author = self.env['res.partner'].browse(author_id)
            defaults['author_id'] = author.id
            # TODO: May be we have to rely on autodetection of partner?
            #       (without explicitly setting it here)
            defaults['partner_id'] = author.commercial_partner_id.id
            if len(author.user_ids) == 1:
                defaults['created_by_id'] = author.user_ids[0].id
        else:
            author = False
            defaults['author_id'] = False
            defaults['partner_id'] = False
            defaults['author_name'] = author_name

        defaults.update({'channel_id': self.env.ref(
            'generic_request15.request_channel_email').id})

        request = super(RequestRequest, self).message_new(
            msg_dict, custom_values=defaults)

        # Find partners from emails (cc) and subscribe them
        partner_ids = request._mail_find_partner_from_emails(
            self._find_emails_from_msg(msg_dict),
            force_create=company.request_mail_create_partner_from_email)
        partner_ids = [p.id for p in partner_ids if p]

        if author:
            partner_ids += [author.id]

        request.message_subscribe(partner_ids)
        return request

    def message_update(self, msg, update_vals=None):
        # Subscribe partners found in received email
        email_list = self._find_emails_from_msg(msg)

        # TODO: Add option in settings that could allow to force create
        # contacts mentioned in cc
        partner_ids = self._mail_find_partner_from_emails(
            email_list, force_create=False)
        partner_ids = [p.id for p in partner_ids if p]
        if partner_ids:
            self.message_subscribe(partner_ids)

        return super(RequestRequest, self).message_update(
            msg, update_vals=update_vals)

    def request_add_suggested_recipients(self, recipients):
        for record in self:
            if record.author_id:
                reason = _('Author')
                record._message_add_suggested_recipient(
                    recipients, partner=record.author_id, reason=reason)
            elif record.email_from:
                record._message_add_suggested_recipient(
                    recipients,
                    email="%s <%s>" % (record.author_name, record.email_from),
                    reason=_('Author Email'))
            if (record.email_cc and
                    self.env.user.company_id.request_mail_suggest_global_cc):
                for email in tools.email_split(record.email_cc):
                    record._message_add_suggested_recipient(
                        recipients, email=email,
                        reason=_('Global CC'))
            if (record.partner_id and
                    self.env.user.company_id.request_mail_suggest_partner):
                reason = _('Partner')
                record._message_add_suggested_recipient(
                    recipients, partner=record.partner_id, reason=reason)

    def _message_get_suggested_recipients(self):
        recipients = super(
            RequestRequest, self
        )._message_get_suggested_recipients()
        try:
            self.request_add_suggested_recipients(recipients)
        except exceptions.AcccessError:  # pylint: disable=except-pass
            pass
        return recipients

    def _message_post_after_hook(self, message, msg_vals, *args, **kwargs):
        # Overridden to add update request text with data from original message
        # This is required to make images display correctly,
        # because usualy, in emails, image's src looks liks:
        #     src="cid:ii_151b51a290ed6a91"
        if self and self.original_message_id == message.message_id:
            # We have to add this processing only in case when request is
            # created from email, and in this case, this method is called on
            # recordset with single record
            self.with_context(
                mail_notrack=True,
            ).write({
                'request_text': MAIL_REQUEST_TEXT_TMPL % {
                    'subject': message.subject,
                    'body': message.body,
                },
                'original_message_id': False,
            })

        return super(RequestRequest, self)._message_post_after_hook(
            message, msg_vals, *args, **kwargs
        )

    def action_show_request_events(self):
        self.ensure_one()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_request_event_view',
            domain=[('request_id', '=', self.id)])

    def _request_timesheet_get_defaults(self):
        return {
            'request_id': self.id,
        }

    def action_start_work(self):
        self.ensure_one()
        TimesheetLines = self.env['request.timesheet.line']
        running_lines = TimesheetLines._find_running_lines()
        if running_lines:
            return self.env['generic.mixin.get.action'].get_action_by_xmlid(
                'generic_request15.action_request_wizard_stop_work',
                context={
                    'default_timesheet_line_id': running_lines[0].id,
                    'request_timesheet_start_request_id': self.id,
                })

        data = self._request_timesheet_get_defaults()
        data['date_start'] = fields.Datetime.now()
        timesheet_line = TimesheetLines.create(data)
        self.trigger_event('timetracking-start-work', {
            'timesheet_line_id': timesheet_line.id,
        })
        return False

    def action_stop_work(self):
        self.ensure_one()
        TimesheetLines = self.env['request.timesheet.line']
        running_lines = TimesheetLines._find_running_lines()
        if running_lines:
            return self.env['generic.mixin.get.action'].get_action_by_xmlid(
                'generic_request15.action_request_wizard_stop_work',
                context={'default_timesheet_line_id': running_lines[0].id})
        return False

    def action_request_view_timesheet_lines(self):
        self.ensure_one()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_timesheet_line',
            context={'default_request_id': self.id},
            domain=[('request_id', '=', self.id)],
        )

    def action_show_related_author_requests_closed(self):
        self.ensure_one()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_request_window',
            domain=[('author_id', '=', self.author_id.id),
                    ('id', '!=', self.id)],
            context={
                'search_default_filter_closed': 1,
            })

    def action_show_related_author_requests_opened(self):
        self.ensure_one()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_request_window',
            domain=[('author_id', '=', self.author_id.id),
                    ('id', '!=', self.id)],
            context={
                'search_default_filter_open': 1,
            })

    def action_show_related_partner_requests_closed(self):
        self.ensure_one()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_request_window',
            domain=[('partner_id', '=', self.partner_id.id),
                    ('id', '!=', self.id)],
            context={
                'search_default_filter_closed': 1,
            })

    def action_show_related_partner_requests_opened(self):
        self.ensure_one()
        return self.env['generic.mixin.get.action'].get_action_by_xmlid(
            'generic_request15.action_request_window',
            domain=[('partner_id', '=', self.partner_id.id),
                    ('id', '!=', self.id)],
            context={
                'search_default_filter_open': 1,
            })
