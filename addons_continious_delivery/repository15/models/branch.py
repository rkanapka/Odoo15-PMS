# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models


class RepositoryBranch(models.Model):
    _name = 'repository.branch'
    _description = 'Branches'

    _rec_name = 'name'
    _order = 'create_date DESC'

    branch_type = fields.Selection([('dev', 'Developing'), ('test', 'Testing'), ('prod', 'Production')], required=True)
    name = fields.Char(string='Name', required=True)

