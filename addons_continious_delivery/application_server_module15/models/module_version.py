# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import _, fields, models
from odoo.exceptions import UserError


class ModuleVersion(models.Model):
    _name = 'module.version'
    _description = 'Version'
    _order = 'create_date DESC'
    _rec_name = 'version_name'

    version_name = fields.Char(compute="_compute_version_name", store=True, string="Version Name")
    code_id = fields.Many2one('module.version.code', string='Code', required=True)
    branch_id = fields.Many2one('repository.branch', string='Branch', required=True)
    no = fields.Integer(string='Modification No', required=True)

    active = fields.Boolean(string='Active', default=True)
    release_date = fields.Datetime(string='Release Date')
    user_released_id = fields.Many2one('res.users', string='User Released')

    odoo_version_id = fields.Many2one('repository.version', string='Odoo Version')
    module_ids = fields.Many2many(
        'application_server.module', 'application_module_rel',
        'application_id', 'module_id', string='Modules'
    )
    application_version_ids = fields.Many2many('application_server.application.version', string='Versions')
    commit_ids = fields.One2many('repository.revision', 'version_id', string='Versions')
    server_module_id = fields.Many2one('application_server.module', string='Modules')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(code_id, branch_id, no)', 'Version name must be unique!'),
    ]

    def _compute_version_name(self):
        for version in self:
            version.version_name = \
                f"{version.code_id.code}.{version.odoo_version_id.odoo_version}.{version.branch_id.name}.{version.no}"

    def validate_commit(self, vals):
        _UNKNOWN_FORMAT = _(
            'Unknown commit format. Comment must have minus or plus symbol, code, ID, date-time and short description '
            '(plus symbol means what description is public, minus symbol means what description is private. '
            'For example: -DU3 CASE13 1:30 Some short description. Another example with date: '
            '+DU3 CASE13 091025-1:30 Some short description'
        )

        version_obj = self.env['module.version']
        usr_obj = self.env['res.users']
        rep_obj = self.env['repository.repository']

        if not vals['log']:
            raise UserError(_(_UNKNOWN_FORMAT))
        usr = usr_obj.browse(rep_obj.get_user_id(vals['author']))
        log_elements = vals['log'].split(' ', 3)
        if len(log_elements) != 4:
            raise UserError(_(_UNKNOWN_FORMAT))
        version_txt = log_elements[0]

        if not (version_txt[0] == '+' or version_txt[0] == '-'):
            raise UserError(_(_UNKNOWN_FORMAT))

        version_ids = version_obj.search([('version_name', '=', version_txt)]).ids
        if not version_ids:
            raise UserError(_('Unknown version %s.') % version_txt)
        version = version_obj.browse(version_ids[0])

        data = {
            'version': version,
            'usr': usr,
        }

        module_names = []
        for module in data['version'].module_ids:
            if module.name not in module_names:
                module_names.append(module.name)
        for change in vals['changed'].split('\n'):
            path_list = change[4:].strip().split('/')
            if path_list and path_list[-1].endswith('.pyc') and change[0] != 'D':
                raise UserError(
                    _('You try to commit pyc file: %s.'
                      'Committing of pyc files is forbidden, it is only allowed to delete them.') % (change[:4])
                )
            if (len(path_list) == 1) or (len(path_list) == 2 and not path_list[1]):
                if path_list[0] and path_list[0] not in module_names:
                    raise UserError(
                        _('Module %s do not belong to version %s.'
                          'To this version you can commit only these modules %s.') %
                        (path_list[0], data['version'].name, ', '.join(module_names))
                    )
            elif len(path_list) == 2:
                if path_list[0] and path_list[1] and (
                        (path_list[0] not in module_names) or (path_list[1] != data['version'].branch_id.name)
                ):
                    raise UserError(
                        _('Module %s branch %s do not belong to version %s.'
                          'To this version you can commit only this(these) module(es) %s and branch %s.') % (
                            path_list[0], data['version'].branch_id.name,
                            data['version'].name, ', '.join(module_names),
                            data['version'].branch_id.name
                        )
                    )
            elif len(path_list) >= 3:
                if path_list[0] and path_list[2] and (
                        (path_list[0] not in module_names) or (path_list[2] != data['version'].branch_id.name)
                ):
                    if not (

                            (path_list[0] in module_names)
                    ):
                        raise UserError(
                            _('Module %s branch %s do not belong to version %s. '
                              'To this version you can commit only this(these) module(es) %s and branch %s.') % (
                                path_list[0], data['version'].branch_id.name,
                                data['version'].version_name, ', '.join(module_names),
                                data['version'].branch_id.name
                            )
                        )
        return data


class ModuleVersionCode(models.Model):
    _name = 'module.version.code'
    _description = 'Version Code'

    _order = 'create_date DESC'
    _rec_name = 'code'

    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)
    category_id = fields.Many2one('module.version.category', 'Category')

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Version code must be unique!'),
    ]

    def write(self, vals):
        if 'code' in vals:
            for ver_code in self:
                if 'code' in vals and vals['code'] != ver_code.code:
                    raise UserError(
                        _('Editing Code is forbidden.')
                    )
        return super(ModuleVersionCode, self).write(vals)


class ModuleVersionCategory(models.Model):
    _name = 'module.version.category'
    _description = 'Version Category'
    _order = 'sequence'

    name = fields.Char(string='Name', size=128, required=True)
    sequence = fields.Integer(string='Sequence', default=10)
