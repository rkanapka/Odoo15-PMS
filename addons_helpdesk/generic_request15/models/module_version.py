# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import _, fields, models
from odoo.exceptions import UserError


class ModuleVersion(models.Model):
    _inherit = 'module.version'

    def validate_commit(self, vals):
        res = super(ModuleVersion, self).validate_commit(vals)

        proj_task_obj = self.env['project.task']
        log_elements = vals['log'].split(' ', 3)
        task_id_element = log_elements[1]
        task_id_str = task_id_element[4:]

        try:
            task_id_integer = int(task_id_str)
        except Exception:
            raise UserError(_(_UNKNOWN_FORMAT))

        project_task_id = proj_task_obj.search([('id', '=', task_id_integer)], limit=1)
        if not project_task_id:
            raise UserError(_('Project Task: %s not found' % task_id_str))

        res['project_task_id'] = project_task_id
        return res
