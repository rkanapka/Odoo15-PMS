# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource

import time
import subprocess


class ApplicationServerServerType(models.Model):
    _name = 'application_server.server.type'
    _description = 'Server Type'

    code = fields.Char(string='Code')
    name = fields.Char(string='Name', required=True)


class ApplicationServerServer(models.Model):
    _name = 'application_server.server'
    _inherit = 'mail.thread'
    _description = 'Server'

    def _get_server_types(self):
        server_type_obj = self.env['application_server.server.type']
        server_type_ids = server_type_obj.search([])
        return [(st.code, st.name) for st in server_type_obj.browse(server_type_ids.ids) if server_type_ids]

    name = fields.Char(string='Name', required=True)
    server_type = fields.Selection(selection=[
        ('production', 'Production Environment'),
        ('test', 'Testing Environment'),
    ], string='Server Type')
    type = fields.Selection(selection=_get_server_types, string='Odoo Version')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    installation_ids = fields.One2many('application_server.server.installation', 'server_id', string='Installations')
    active = fields.Boolean(string='Active', default=True)

    # Fields from project_version_repository
    ssh_username = fields.Char(string='SSH User Name', required=True)
    ssh_port = fields.Integer(string='SSH Port', default=22)

    # -----------------------------------
    host = fields.Char(string='Host', default='127.0.0.1')
    protocol = fields.Selection(selection=[('https', 'https'), ('http', 'http')], string='Protocol', default='http')
    port = fields.Integer(string='Port', default=8069)

    db_host = fields.Char(string='Database Host', default='127.0.0.1')
    db_port = fields.Integer(string='Database Port', default=5432)
    db_dir = fields.Char(string='Databases Directory')
    db_version_id = fields.Many2one('application_server.server.db_version', string='Database Version')

    os_id = fields.Many2one('application_server.server.os', string='Operating System')

    log_path = fields.Text(string='Log Path')
    server_restart = fields.Text(string='Server Restart')
    connection = fields.Char(string='SSH Connection')
    connection_client = fields.Char(string='Connection for Client')
    connection_type_id = fields.Many2one('application_server.server.connect_type', string='Connection Type')
    description = fields.Html(string='Description')
    # Continuous Integration / Continuous delivery
    auto_install = fields.Boolean(
        string='Auto Install', help='Automatically create installations after new code is pushed.', default=False
    )
    addons_path = fields.Char(string='Addons')
    versions_archive_path = fields.Char(string='Versions Archive')
    applications_archive_path = fields.Char(string='Applications Archive')
    restart_cmd = fields.Char(string='Restart command', help="Odoo instances restart command.")
    configs = fields.Text(string='Configs', help="All server config files. Each config must be separated with space.")
    venv_path = fields.Char(string='Virtual Env', help="Virtual Environment")
    # Applications and Versions
    last_version_ids = fields.Many2many(
        'project.version.version', 'server_last_version_rel',
        'server_id', 'version_id', string='Last Versions'
    )
    last_application_ids = fields.Many2many(
        'application_server.application.version.release', 'server_last_application_rel',
        'server_id', 'application_id', string='Last Applications'
    )
    prohibited_app_ids = fields.Many2many(
        'application_server.application', 'server_prohibited_application_rel',
        'server_id', 'application_id', string='Prohibited Applications'
    )
    prohibited_versions_ids = fields.Many2many(
        'project.version.code', 'server_prohibited_version_rel',
        'server_id', 'version_code_id', string='Prohibited Versions'
    )

    portal_username = fields.Char(string='Portal Username')
    portal_password = fields.Char(string='Portal Password')
    use_sources = fields.Boolean('Use Sources')
    python_version = fields.Many2one('application_server.server.python_version', string='Python Version')

    def copy(self, default=None):
        if default is None:
            default = {}
        default['installation_ids'] = False
        return super(ApplicationServerServer, self).copy(default)

    def _generate_installation_get_vals(self, server, only_with_modifications, only_released):
        rel_obj = self.env['application_server.application.version.release']
        install_obj = self.env['application_server.server.installation']
        vals = {'server_id': server.id}
        new_rel_ids = []
        inst_versions = {}
        install_ids = install_obj.search([('server_id', '=', server.id)], order='date')
        for install in install_obj.browse(install_ids):
            for rel in install.application_ids:
                inst_versions[rel.version_id.id] = rel.id
        for ver_id in inst_versions.keys():
            rel_ids = rel_obj.search([('version_id', '=', ver_id)], order='no DESC', limit=1)
            if rel_ids and (rel_ids[0] != inst_versions[ver_id]):
                new_rel_ids.append(rel_ids[0])
        if new_rel_ids:
            vals['application_ids'] = [(6, 0, new_rel_ids)]
        return vals

    def generate_installation(self, only_with_modifications, only_released):
        res = []
        install_obj = self.env['application_server.server.installation']
        for server in self.browse(self.ids):
            vals = self._generate_installation_get_vals(server, only_with_modifications, only_released)
            res.append(install_obj.create(vals))
        return res

    def open_client_website(self):
        if self.connection_client:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s' % self.connection_client,
                'target': 'new',
            }

    def fill_last_versions(self):
        return {}


class ApplicationServerServerInstallation(models.Model):
    _name = 'application_server.server.installation'
    _description = 'Server Installation'
    _rec_name = 'date'
    _order = 'date desc, id desc'

    server_id = fields.Many2one('application_server.server', string='Server', required=True)
    date = fields.Date(string='Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    user_id = fields.Many2one('res.users', string='Users', required=True, default=lambda self: self.env.user)
    application_ids = fields.Many2many(
        'application_server.application.version.release',
        'server_installation_application_version_release_rel',
        'installation_id', 'release_id', string='Applications'
    )
    notes = fields.Text(string='Notes')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('done', 'Done')
        ], string='State', required=True, readonly=True, default=lambda *a: 'draft'
    )

    def name_get(self):
        if self.ids:
            return []
        res = []
        for rec in self.browse(self.ids):
            name = rec.server_id.name + ' - ' + rec.date
            res.append((rec.id, name))
        return res

    def set_to_in_progress(self):
        self.write({'state': 'in_progress'})

    def set_to_done(self):
        inst_ids = self.search([('server_id', '=', self.server_id.id), ('state', '=', 'in_progress')], limit=1)
        if inst_ids and inst_ids.ids > 1:
            raise UserError(_('There already exists an installation with state "In Progress" for this server'))
        # if self.server_id.auto_install and self.user_id.name == "Helpdesk":
        #     self.deploy_modules_with_ansible()

        self.write({'state': 'done'})

    def set_to_draft(self):
        self.write({'state': 'draft'})

    def deploy_modules_with_ansible(self):
        for install in self.browse(self.ids):
            inst_ids = self.search([
                ('server_id', '=', install.server_id.id),
                ('state', '=', 'in_progress'),
            ])
            if inst_ids:
                raise UserError(
                    _('There already exists an installation with state "In Progress" for this server')
                )

            data = self.get_data_for_deployment(install)

            if data.get('host_ip', False) \
                    and data.get('host_user', False) \
                    and data.get('modules_str', False) \
                    and data.get('version_list', False) \
                    and data.get('vers_path', False) \
                    and data.get('addons_path', False) \
                    and data.get('db_host', False) \
                    and data.get('db_port', False) \
                    and data.get('restart_command', False) \
                    and data.get('configs', False):
                self.execute_ansible_script(data)
            else:
                raise UserError(
                    _('Missing db host, db port, host, host user, versions / addons paths, restart command,'
                      'config paths in Server Card or versions in Server Installation.')
                )
        return True

    def get_data_for_deployment(self, install):
        res = {
            'host_ip': install.server_id.host if install.server_id.host else False,
            'host_user': install.server_id.ssh_username if install.server_id.ssh_username else False,
            'db_host': install.server_id.db_host if install.server_id.db_host else False,
            'db_port': install.server_id.db_port if install.server_id.db_port else False,
            'vers_path': install.server_id.versions_archive_path if install.server_id.versions_archive_path else False,
            'addons_path': install.server_id.addons_path if install.server_id.addons_path else False,
            'restart_command': install.server_id.restart_cmd if install.server_id.restart_cmd else False,
            'configs': install.server_id.configs if install.server_id.configs else False,
            'venv_path': install.server_id.venv_path if install.server_id.venv_path else False,
            'version_list': [],
            'modules_str': ""
        }
        for ver in install.version_ids:
            self.get_all_modules_to_str(res, ver)
            if ver.name:
                res['version_list'].append(ver.name.encode("utf-8"))
        return res

    @staticmethod
    def get_all_modules_to_str(res, ver):
        if ver.modules and res['modules_str']:
            res['modules_str'] += "," + ver.modules.encode("utf-8")
        elif ver.modules and not res['modules_str']:
            res['modules_str'] = ver.modules.encode("utf-8")

    @staticmethod
    def execute_ansible_script(data):
        ansible_script_path = get_module_resource('application_server', 'data', 'ansible_deploy_script.yml')
        restart_script_path = get_module_resource('application_server', 'data', 'restart.sh')

        bash_command = [
            "ansible-playbook",
            "-i", "%s," % data['host_ip'],
            "-e", "ansible_user=%s" % data['host_user'],
            ansible_script_path,
            "-e", '{"sandas_versions": %s, "versions_path": %s, "addons_path": %s, "venv_path": %s,'
                  '"db_conn": {'
                  '"host": %s, "port": %s, "user": %s},'
                  '"modules_to_upgrade": %s,'
                  '"restart_command": %s,'
                  '"restart_script_path": %s,'
                  '"configs": %s'
                  '}' %
                  (data['version_list'], data['vers_path'], data['addons_path'], data['venv_path'], data['db_host'],
                   data['db_port'], data['host_user'], data['modules_str'], data['restart_command'],
                   restart_script_path, data['configs'],)
        ]
        process = subprocess.Popen(bash_command, stdout=subprocess.PIPE)
        process.communicate()
