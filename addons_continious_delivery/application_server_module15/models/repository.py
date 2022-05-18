# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models


class RepositoryRevision(models.Model):
    _inherit = "repository.revision"

    version_id = fields.Many2one('module.version', string='Version', readonly=True)


class RepositoryRepository(models.Model):
    _inherit = "repository.repository"

    def get_rev_vals(self, vals):
        res_vals = super(RepositoryRepository, self).get_rev_vals(vals)
        ver_obj = self.env['module.version']
        if vals['versioned']:
            data = ver_obj.validate_commit(vals)
            res_vals['version_id'] = data['version'].id
            res_vals['project_task_id'] = res_vals['project_task_id'].id
            return res_vals
