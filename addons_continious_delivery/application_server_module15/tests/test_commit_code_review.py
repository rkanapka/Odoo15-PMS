# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo.tests import HttpCase, tagged
import json


@tagged('post_install', '-at_install')
class TestCommitCodeReview(HttpCase):
    def setUp(self):
        super().setUp()
        self.github_user = 'Johnny'
        self.json_data = {'user_login': self.github_user}
        self.headers = {
            'Content-Type': 'application/json',
            "Accept": "application/json"
        }

    def test_user_does_not_exists(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/code_review', headers=self.headers, data=json.dumps(self.json_data))
        response_data = json.loads(response.text)
        self.assertEqual(response_data['result']['message'], f"\n No User with login {self.github_user}. \n")

    def test_user_exists(self):
        self.user_layout = self.env['res.users'].create({
            "login": "johnny@gmail.com",
            "repository_ident": self.github_user,
            "name": "John",
        })
        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/code_review', headers=self.headers, data=json.dumps(self.json_data))
        response_data = json.loads(response.text)
        self.assertEqual(response_data['result']['message'], f"\n Found User with login {self.github_user}. \n")
