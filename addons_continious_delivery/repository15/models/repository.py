# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import _, fields, models
from odoo import tools
from odoo.exceptions import UserError

from git import repo

import os
import time
import shutil

# Folder where sandas addons are
_SANDAS_ADDONS = "sandas_addons"
_TO_SKIP = [_SANDAS_ADDONS]


class RepositoryRepository(models.Model):
    _name = "repository.repository"
    _description = "Repository"

    name = fields.Char(string='Name', required=True)
    odoo_version_id = fields.Many2one('repository.version', string='Odoo Version')
    url = fields.Char(string='URL', required=True)
    release_application_dir = fields.Char(string='Release Application Dir', help='Release Application Directory')
    release_addons_dir = fields.Char(string='Release Addons Dir', help='Release Addons Directory')
    branch_ids = fields.Many2many('repository.branch', 'repository_branch_rel', string='Branches')
    revision_ids = fields.One2many('repository.revision', 'repository_id', string='Revisions')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name of the repository must be unique !')
    ]

    def copy(self, default=None):
        if default is None:
            default = {}
        rep = self.browse()
        default['name'] = _('%s (copy)') % (tools.ustr(rep.name))
        default['revision_ids'] = []
        return super(RepositoryRepository, self).copy(default=default)

    def get_user_id(self, author):
        usr_obj = self.env['res.users']
        usr_ids = usr_obj.search(['|', ('login', '=', author), ('repository_ident', 'like', author)], limit=1)
        if not usr_ids:
            raise UserError(
                _('Unknown Odoo user %s. Please create user with this login or repository identification.') % (
                    author
                )
            )
        return usr_ids[0]

    def get_rep_id(self, rep_name):
        rep_ids = self.search([('name', '=', rep_name)], limit=1)
        if not rep_ids:
            raise UserError(_('Unknown repository %s.') % rep_name)
        return rep_ids[0]

    def get_rev_vals(self, vals):
        return {
            'repository_id': self.get_rep_id(vals['rep_name']).id,
            'no': vals['rev_no'],
            'name': vals['rev_no'],
            'log': vals['log'],
            'user_id': self.get_user_id(vals['author']).id,
            'changed': vals.get('changed', False),
            'branch_name': vals.get('branch_name', False),
        }

    def commit_check(self, vals):
        self.get_rep_id(vals['rep_name'])
        self.get_user_id(vals['author'])
        return True

    def pre_commit(self, vals):
        self.commit_check(vals)
        return True

    def post_commit(self, vals):
        rev_obj = self.env['repository.revision']
        rev_id = rev_obj.create(self.get_rev_vals(vals)).id
        return rev_id

    @staticmethod
    def pull_changes_from_git(git_path):
        git_rep = repo.Repo(git_path)
        origin_branch = git_rep.remotes.origin
        origin_branch.pull()

    @staticmethod
    def copy_to_another_path(src, dst, to_skip=None):
        for item in os.listdir(src):
            s = os.path.join(src, item)
            # when we realise server itself, we don't want sandas_addons and other files inside
            if to_skip and item in to_skip:
                continue
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

    def move_required_modules(self, rep, module, version, branch, version_no):
        module_full_version = "%s.%s.%s" % (version, branch, str(version_no))

        module_name = module.name
        version_dest_path = os.path.join(
            rep.release_sources_dir, module_full_version
        )
        if os.path.exists(version_dest_path):
            shutil.rmtree

        if not os.path.exists(version_dest_path):
            os.mkdir(version_dest_path)

        dest_path = os.path.join(version_dest_path, module_name)
        os.mkdir(dest_path)

        sandas_addons_path = os.path.join(rep.url, _SANDAS_ADDONS)

        module_path = os.path.join(sandas_addons_path, module_name)
        self.copy_to_another_path(module_path, dest_path)
        return True

    def export_git_url(self, rep, module=None, version=None, dest_path=None):
        self.pull_changes_from_git(rep.url)
        if module:
            self.move_required_modules(rep, module, version.code_id.code, version.branch_id.name, version.no)
        else:
            os.mkdir(dest_path)
            self.copy_to_another_path(rep.url, dest_path, _TO_SKIP)
        return True


class RepositoryRevision(models.Model):
    _name = "repository.revision"
    _description = "Repository Revision"
    _order = "date DESC"

    repository_id = fields.Many2one('repository.repository', string='Repository', required=True, readonly=True)
    no = fields.Integer(string='No', required=True, readonly=True)
    name = fields.Char(string='Name', required=True, readonly=True)
    date = fields.Datetime(
        string='Date', required=True, readonly=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S')
    )
    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True)
    log = fields.Text(string='Log', readonly=True)
    changed = fields.Text(string='Changed', readonly=True)
    branch_name = fields.Char(string='Branch Name', readonly=True)

    def name_get(self):
        if not self.ids:
            return []
        res = []
        for rev in self.browse(self.ids):
            name = '%s, %d' % (tools.ustr(rev.repository_id.name), rev.no)
            res.append((rev.id, name))
        return res

    def get_revision_number(self, min_number, max_number):
        rev_id = self.search([
            ('no', '>', min_number),
            ('no', '<', max_number)
        ], order='no DESC', limit=1)
        rev_no = min_number + 1 if not rev_id else rev_id.no + 1
        return rev_no


class RepositoryVersion(models.Model):
    _name = "repository.version"
    _description = "Repository Version"
    _order = "odoo_version DESC"
    _rec_name = "odoo_version"

    odoo_version = fields.Char(string="Odoo Version")
