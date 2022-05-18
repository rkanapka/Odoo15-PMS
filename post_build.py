#!/usr/bin/python
# -*- encoding: utf-8 -*-

import sys
import paramiko
import xmlrpc.client
import json
import os
import re
import subprocess
import requests


_SANDAS_ADDONS = 'sandas_addons'
_ODOO_SERVER_REP = 'server15'
_ODOO_ADDONS_REP = 'addons15'
_ODOO_BRANCH = 'branch/15.0'
_MIN_NO = 1_600_000_000
_MAX_NO = 1_700_000_000


class PostBuild:
    def __init__(self):
        self.author = None
        self.uid = None
        self.pwd = None
        self.dbname = None
        self.port = None
        self.user = None
        self.base_url = None
        self.rpc_obj = None
        self.commit_msg = None
        self.changes = None
        self.repository = None
        self.data_dict = None
        self.rev_no = None
        self.commits_number = None
        self.versioned = False
        self.branch_name_from = None

        sys.stderr.write("\n TESTAS\n")
        sys.stderr.write("\n All parameters. %s\n" % str(sys.argv))
        branch_name = sys.argv[-1]

        data_dict_list = self.get_commits_data_dict_list()
        self.get_total_commits_number(data_dict_list)
        sys.stderr.write("\n data_dict_list: %s\nLen: %s\n Branch: %s\n" % (
            data_dict_list, self.commits_number, branch_name
        ))

        if branch_name.endswith('master') or branch_name.endswith('developing') and data_dict_list:
            for commit_number, data_dict in enumerate(data_dict_list, start=1):
                self.set_data_dict(data_dict)
                self.set_data_from_system_args()
                self.set_repository()
                self.set_login_data_from_ssh_config()
                self.set_rev_no()
                is_last_commit = True if commit_number == len(data_dict_list) else False
                sys.stderr.write("\n Commit number: %s\n Commit data: %s\n" % (commit_number, data_dict))
                sys.stderr.write("Total commits: %s\n" % self.commits_number)
                sys.stderr.write("Is last commit: %s\n" % is_last_commit)
                self.odoo_post_commit_actions()
        elif branch_name.endswith('testing'):
            last_data_dict = data_dict_list[-1]
            self.set_data_dict(last_data_dict)
            self.merge_to_master()
            sys.stderr.write("\n PUSHED TO MASTER. \n")
        else:
            branch_name = branch_name.split('/')[-1]
            last_data_dict = data_dict_list[-1]
            self.set_data_dict(last_data_dict)
            if self.check_if_need_code_review():
                self.make_pull_request(branch_name)
                sys.stderr.write("\n PULL REQUEST MADE. \n")
            else:
                self.merge_to_developing(branch_name)
                sys.stderr.write("\n PUSHED TO DEVELOPING. \n")

    def get_total_commits_number(self, data_dict_list):
        self.commits_number = len(data_dict_list)

    def check_if_need_code_review(self):
        self.set_login_data_from_ssh_config()
        return self.check_if_user_need_code_review()

    def check_if_user_need_code_review(self):
        route_url = "/repository/code_review"

        user_login = self.data_dict.get('author', {}).get('name')
        if not user_login:
            sys.stderr.write("\n No author in git commit data. \n")
            return True

        headers = self._get_headers()
        cookies_data = self._get_cookies_data(self.base_url, headers)

        json_data = {'user_login': user_login}

        response = requests.post(
            self.base_url + route_url, data=json.dumps(json_data), headers=headers, cookies=cookies_data
        )
        response_dict = json.loads(response.text)
        sys.stderr.write("\n Code review request response: %s \n" % response_dict['result'])

        if response.status_code != 200:
            return True

        return response_dict['result']['need_code_review']

    @staticmethod
    def merge_to_master():
        os.system("git checkout master")
        merge = '''git merge origin/testing'''
        sys.stderr.write("\n " + merge + "\n ")
        os.system(merge)
        push = '''git push'''
        sys.stderr.write("\n " + push + "\n ")
        os.system(push)

    @staticmethod
    def merge_to_developing(branch_name):
        os.system("git checkout %s" % branch_name)
        os.system("git checkout developing")
        merge = '''git merge origin/%s''' % branch_name
        sys.stderr.write("\n " + merge + "\n ")
        os.system(merge)
        push = '''git push'''
        sys.stderr.write("\n " + push + "\n ")
        os.system(push)

    def make_pull_request(self, branch_name):
        user_login = self.data_dict.get('author', {}).get('name', '')
        os.system("git checkout %s" % branch_name)
        message = '[PUSH BY %s] ' % user_login
        message += self.data_dict.get('message', 'No Message')
        pull_request = '''hub pull-request -m "%s" -b sandas1:developing -h sandas1:%s''' % (message, branch_name)
        sys.stderr.write("\n " + pull_request + "\n ")
        os.system(pull_request)

    @staticmethod
    def get_commits_data_dict_list():
        system_args = sys.argv
        info_from_jenkins_str = ' '.join(system_args[2:-1])
        return json.loads(info_from_jenkins_str)

    def set_data_dict(self, data_dict):
        self.data_dict = data_dict

    def set_changes(self):
        changes_list = []
        all_changes_list = \
            self.data_dict.get('added', []) + self.data_dict.get('removed', []) \
            + self.data_dict.get('modified', [])
        for change in all_changes_list:
            if change.startswith(_SANDAS_ADDONS):
                changes_path = change[len(_SANDAS_ADDONS) + 1:]
                split_changes_path = changes_path.split('/', 1)
                if len(split_changes_path) > 1:
                    # Imitates branch
                    changes_path = '/'.join([split_changes_path[0], _ODOO_BRANCH, split_changes_path[1]])

                # 4 dummy dots just because in checks first 4 symbols are cut. Maybe "SVN/" is expected
                changes_list.append("...." + changes_path)
            else:
                changes_list.append(change)

        self.changes = "\n".join(changes_list)

    def set_data_from_system_args(self):
        self.author = self.data_dict.get('author', {}).get('name')
        self.commit_msg = self.data_dict.get('message')
        if self.commit_msg.startswith("Merge"):
            self._get_branch_name_from()
            # Ignore merge commits
            sys.exit(0)
        self.set_changes()

    def _get_branch_name_from(self):
        branch_exists = re.search('sandas1/(.*)\n\n', self.commit_msg)  # Pull Request regex
        if branch_exists is None:
            branch_exists = re.search('origin/(.*)\' into', self.commit_msg)  # Standard merge regex
        sys.stderr.write("\n branch exists: %s\n" % branch_exists)
        if branch_exists is not None:
            self.branch_name_from = branch_exists.group(1)
            sys.stderr.write("\n branch name: %s\n" % self.branch_name_from)

    def set_repository(self):
        for data_key in ('added', 'removed', 'modified'):
            if self.data_dict.get(data_key):
                changed_dir_list = self.data_dict.get(data_key)
                if changed_dir_list[0].startswith(_SANDAS_ADDONS):
                    self.repository = _ODOO_ADDONS_REP
                    self.versioned = True
                else:
                    self.repository = _ODOO_SERVER_REP
                break

    def set_rev_no(self):
        route_url = "/repository/revision_number"

        headers = self._get_headers()
        cookies_data = self._get_cookies_data(self.base_url, headers)

        json_data = {
            'min_rev_no': _MIN_NO,
            'max_rev_no': _MAX_NO,
        }
        response = requests.post(
            self.base_url + route_url, data=json.dumps(json_data), headers=headers, cookies=cookies_data
        )
        sys.stderr.write("\n Odoo revision number response: %s \n" % response.text)
        response_dict = json.loads(response.text)
        if response_dict['result']['revision_no']:
            self.rev_no = response_dict['result']['revision_no']

    def set_login_data_from_ssh_config(self):
        import configparser

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname='server.sandas.lt', port=6123, username='employee'
        )
        sftp_client = ssh_client.open_sftp()
        with sftp_client.open('/home/user/connection_data') as remote_file:
            cfg_parser = configparser.ConfigParser()
            cfg_parser.read_file(remote_file)

            self.pwd = cfg_parser.get('login', 'pw')
            self.dbname = cfg_parser.get('login', 'db')
            self.port = cfg_parser.get('login', 'port')
            self.user = cfg_parser.get('login', 'user')
            self.base_url = "http://demo.sandas.lt:%s" % self.port

    def odoo_post_commit_actions(self):
        route_url = "/repository/commit"

        headers = self._get_headers()
        cookies_data = self._get_cookies_data(self.base_url, headers)

        json_data = {
            'rep_name': self.repository,
            'rev_no': self.rev_no,
            'log': self.commit_msg,
            'author': self.author,
            'changed': self.changes,
            'versioned': self.versioned,
            'branch_name': self.branch_name_from
        }
        response = requests.post(
            self.base_url + route_url, data=json.dumps(json_data), headers=headers, cookies=cookies_data
        )
        sys.stderr.write("\n Odoo post commit response: %s \n" % response.text)

        if response.status_code != 200:
            raise Exception("\n Odoo post commit response: %s \n" % response.text)

    @staticmethod
    def _get_headers():
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Catch-Control": "no-cache"
        }
        return headers

    def _get_cookies_data(self, base_url, headers):
        auth_data = {
            "params": {
                'db': self.dbname,
                'login': self.user,
                'password': self.pwd,
            }
        }
        session_details = requests.get(
            url=base_url + '/web/session/authenticate', data=json.dumps(auth_data), params=auth_data, headers=headers
        )
        session_id = str(session_details.cookies.get('session_id'))
        cookies_data = {
            'login': self.user,
            'password': self.pwd,
            'session_id': session_id
        }
        return cookies_data


if __name__ == "__main__":
    PostBuild()
