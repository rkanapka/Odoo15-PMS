# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.http import Controller, request, route


class CommitController(Controller):

    @route('/repository/commit', type="json", auth="user", methods=['POST'])
    def call_commit(self):
        json_vals = request.jsonrequest
        is_commit_valid = request.env['repository.repository'].pre_commit(json_vals)
        if is_commit_valid:
            commit_id = request.env['repository.repository'].post_commit(json_vals)
            res = self._get_commit_response(commit_id)
        else:
            res = self._get_commit_response()
        return res

    @route('/repository/code_review', type="json", auth="user", methods=['POST'])
    def call_user_need_code_review(self):
        json_vals = request.jsonrequest
        user_login = json_vals['user_login']
        user_id = request.env['res.users'].get_user_with_login_for_code_review(user_login)
        res = self._get_user_review_response(user_id, user_login)
        return res

    @route('/repository/revision_number', type="json", auth="user", methods=['POST'])
    def call_revision_number(self):
        json_vals = request.jsonrequest
        min_number = json_vals['min_rev_no']
        max_number = json_vals['max_rev_no']
        rev_number = request.env['repository.revision'].get_revision_number(min_number, max_number)
        res = self._get_revision_number_response(rev_number)
        return res

    @staticmethod
    def _get_commit_response(commit_id=None):
        if commit_id is None:
            res = {
                "success": False,
                "message": "Bad Request",
                "id": None
            }
        else:
            res = {
                "success": True,
                "message": "Success",
                "id": commit_id
            }
        return res

    @staticmethod
    def _get_user_review_response(user_id, user_login):
        if not user_id:
            res = {
                "success": False,
                "message": "\n No User with login %s. \n" % user_login,
                "need_code_review": False
            }
        else:
            res = {
                "success": True,
                "message": "\n Found User with login %s. \n" % user_login,
                "need_code_review": user_id.need_code_review
            }
        return res

    @staticmethod
    def _get_revision_number_response(rev_number):
        if not rev_number:
            res = {
                "success": False,
                "message": "\n Revision not found \n",
                "revision_id": None
            }
        else:
            res = {
                "success": True,
                "message": "\n Revision number %s. \n" % rev_number,
                "revision_no": rev_number
            }
        return res
