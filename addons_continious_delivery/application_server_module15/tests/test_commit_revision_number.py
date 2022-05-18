# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo.tests import HttpCase, tagged
import json


@tagged('post_install', '-at_install')
class TestCommitRevisionNumber(HttpCase):
    def setUp(self):
        super().setUp()
        self.github_user = 'Johnny'
        self.json_data = {
            'min_rev_no': 1_600_000_000,
            'max_rev_no': 1_700_000_000,
        }
        self.headers = {
            'Content-Type': 'application/json',
            "Accept": "application/json"
        }

    def test_commit_get_first_revision_number(self):
        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/revision_number', headers=self.headers, data=json.dumps(self.json_data))
        response_data = json.loads(response.text)
        self.assertEqual(response_data['result']['message'], "\n Revision number 1600000001. \n")

    def test_commit_get_revision_number(self):
        self.repository_layout = self.env['repository.repository'].create({
            'name': 'addons15',
            'url': 'https://sandas.lt'
        })

        self.revision_layout = self.env['repository.revision'].create({
            'repository_id': self.repository_layout.id,
            'no': 1_600_450_019,
            'name': '1_600_450_019',
            'date': '2022-05-10 00:33:38',
            'user_id': self.env.ref('base.user_admin').id,
            'log': '-MAINT CASE2 00:05 [UPD] Formatting changes.',
            'changed': '....sandas_maintenance15/branch/15.0/views/maintenance_view.xml'
        })

        self.authenticate('admin', 'admin')
        response = self.url_open('/repository/revision_number', headers=self.headers, data=json.dumps(self.json_data))
        response_data = json.loads(response.text)
        self.assertEqual(response_data['result']['message'], '\n Revision number 1600450020. \n')
