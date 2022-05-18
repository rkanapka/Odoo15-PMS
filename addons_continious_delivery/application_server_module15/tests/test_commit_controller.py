# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo.tests import HttpCase, tagged
import json


@tagged('post_install', '-at_install')
class TestCommitControllers(HttpCase):
    def setUp(self):
        super().setUp()
        self.repository_name = 'addons15'
        self.github_user = 'test_user'
        self.version = 'HELPDESK'
        self.module_name = 'sandas_maintenance15'

        self.json_data = {
            'rep_name': self.repository_name,
            'rev_no': 15000000,
            'log': f'-{self.version} CASE162018 00:45 [ADD] Assign task id to revision.',
            'author': self.github_user,
            'changed': f'....{self.module_name}/branch/15.0/model/maintenance.py',
            'versioned': True,
            'branch_name': None
        }

        self.headers = {
            'Content-Type': 'application/json',
            "Accept": "application/json"
        }

    def test_unauthenticated_commit_response(self):
        response = self.url_open('/repository/commit')
        # Method not allowed without authentication
        self.assertEqual(response.status_code, 405)

    def test_authenticated_commit_response(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/commit', headers=self.headers, data=json.dumps(self.json_data))
        # Method allowed with authentication
        self.assertEqual(response.status_code, 200, msg="Response should = OK")

    def test_valid_commit_repository(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/commit', headers=self.headers, data=json.dumps(self.json_data))
        response_data = json.loads(response.text)

        self.assertEqual(response_data['error']['data']['message'], f"Unknown repository {self.repository_name}.")

    def test_valid_commit_user(self):
        self._create_test_repository()
        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/commit', headers=self.headers, data=json.dumps(self.json_data))
        response_data = json.loads(response.text)

        self.assertEqual(
            response_data['error']['data']['message'],
            f"Unknown Odoo user {self.github_user}. Please create user with this login or repository identification."
        )

    def test_valid_commit_version(self):
        self._create_test_repository()
        self._create_test_user()
        self.authenticate('admin', 'admin')
        response = self.url_open(
            '/repository/commit',
            headers=self.headers,
            data=json.dumps(self.json_data)
        )
        response_data = json.loads(response.text)
        self.assertEqual(response_data['error']['data']['message'], f"Unknown version -{self.version}.")

    def test_valid_commit_module_assignment_to_version(self):
        self._create_test_repository()
        self._create_test_user()
        self.repository_version_layout = self.env['repository.version'].create({
            "odoo_version": '15.0',
        })
        self.repository_branch_layout = self.env['repository.branch'].create({
            "name": 'Developing',
            "branch_type": 'dev'
        })
        self.version_code_layout = self.env['module.version.code'].create({
            "code": f'-{self.version}',
        })
        self.version_layout = self.env['module.version'].create({
            "no": 1,
            "code_id": self.version_code_layout.id,
            "branch_id": self.repository_branch_layout.id,
            "odoo_version_id": self.repository_version_layout.id
        })

        self.version_layout._compute_version_name()

        self.json_data['log'] = f'-HELPDESK.15.0.Developing.1 CASE162018 00:45 [ADD] Assign task id to revision.'
        self.authenticate('admin', 'admin')
        response = self.url_open(
            '/repository/commit',
            headers=self.headers,
            data=json.dumps(self.json_data)
        )

        response_data = json.loads(response.text)

        self.assertEqual(
            response_data['error']['data']['message'],
            f"Module {self.module_name} branch {self.version_layout.branch_id.name} "
            f"do not belong to version {self.version_layout.version_name}. "
            f"To this version you can commit only this(these) module(es)  "
            f"and branch {self.version_layout.branch_id.name}."
        )

    def _create_test_repository(self):
        self.repository_layout = self.env['repository.repository'].create({
            'name': self.repository_name,
            'url': 'https://sandas.lt'
        })

    def _create_test_user(self):
        self.user_layout = self.env['res.users'].create({
            "login": self.github_user,
            "name": "Jonas",
        })
