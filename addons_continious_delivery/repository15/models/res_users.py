# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    repository_ident = fields.Char(string='Github Repository Ident')
    need_code_review = fields.Boolean(string='Need Code Review When Pushing to GIT', default=False)

    def get_user_with_login_for_code_review(self, user_login):
        user_id = self.search([('repository_ident', '=', user_login)], limit=1)
        return user_id
