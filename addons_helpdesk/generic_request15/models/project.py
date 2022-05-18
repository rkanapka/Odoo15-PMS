# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models, api


class Project(models.Model):
    _inherit = "project.project"

    odoo_version = fields.Selection(selection='_get_project_odoo_version', string='Odoo Version', required=True)

    def _get_project_odoo_version(self):
        proj_odoo_ver_obj = self.env['project.odoo.version']
        odoo_version_ids = proj_odoo_ver_obj.search([])
        return [(st.name, st.odoo_version) for st in proj_odoo_ver_obj.browse(odoo_version_ids.ids) if odoo_version_ids]


class ProjectOdooVersion(models.Model):
    _name = 'project.odoo.version'
    _description = 'Project Odoo Version'

    name = fields.Char(string='Name', required=True)
    odoo_version = fields.Char(string='Odoo version', required=True)


class ProjectTask(models.Model):
    _inherit = "project.task"

    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
    is_request_required = fields.Boolean(related='company_id.is_request_required', readonly=True)
    request_id = fields.Many2one('request.request', string='Request')
    task_time = fields.Float(string="Task Time")
    commit_id = fields.Char(compute="_get_commit_id", string="Commit ID", readonly=True)

    commit_ids = fields.One2many('repository.revision', 'project_task_id', string='Request')

    @api.onchange('request_id')
    def _get_project_id(self):
        for rec in self:
            if rec.request_id and rec.request_id.project_id:
                rec.project_id = rec.request_id.project_id

    def _get_commit_id(self):
        for rec in self:
            rec.commit_id = f"CASE{rec.id}"
