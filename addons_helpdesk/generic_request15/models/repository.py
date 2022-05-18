# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models


class RepositoryRevision(models.Model):
    _inherit = "repository.revision"

    project_task_id = fields.Many2one('project.task', string="Task")
