# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models


class ApplicationServerModuleType(models.Model):
    _name = 'application_server.module.type'
    _description = 'Module Type'

    name = fields.Char(string='Name', required=True, translate=True)
    module_ids = fields.One2many('application_server.module', 'type_id', string='Modules')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Module type name must be unique!')
    ]


class ApplicationServerModuleCategory(models.Model):
    _name = 'application_server.module.category'
    _description = 'Module Category'

    name = fields.Char(string='Name', required=True, translate=True)
    parent_id = fields.Many2one('application_server.module.category', string='Parent Category')
    child_ids = fields.One2many('application_server.module.category', 'parent_id', string='Child Categories')
    module_ids = fields.One2many('application_server.module', 'category_id', string='Modules')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Module category name must be unique!')
    ]


class ApplicationServerModule(models.Model):
    _name = 'application_server.module'
    _description = 'Module'

    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    application_id = fields.Many2one('application_server.application', string='Application', required=True)
    type_id = fields.Many2one('application_server.module.type', string='Type', required=True)
    category_id = fields.Many2one('application_server.module.category', string='Category', required=True)
    repository_id = fields.Many2one('repository.repository', string='Repository', required=True)
    odoo_version_id = fields.Many2one('repository.version', string='Odoo Version', required=True)

    dev_version_ids = fields.One2many(
        'module.version', 'server_module_id', string='Dev Versions', domain=[('branch_id', '=', 'dev')]
    )
    prod_version_ids = fields.One2many(
        'module.version', 'server_module_id', string='Prod Versions', domain=[('branch_id', '=', 'prod')]
    )

    _sql_constraints = [
        ('name_appl_uniq', 'UNIQUE(name, odoo_version_id)', 'Module name and version bust be unique combination!')
    ]
