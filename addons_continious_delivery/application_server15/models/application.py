# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models
from odoo import tools


class ApplicationServerApplication(models.Model):
    _name = 'application_server.application'
    _description = 'Application'

    name = fields.Char(string='Name', required=True)
    version_ids = fields.One2many('application_server.application.version', 'application_id', string='Versions')


class ApplicationServerApplicationVersion(models.Model):
    _name = 'application_server.application.version'
    _description = 'Version'

    name = fields.Char(string='Name', required=True)
    application_id = fields.Many2one('application_server.application', string='Application', required=True)
    release_ids = fields.One2many('application_server.application.version.release', 'version_id', string='Releases')


class ApplicationServerApplicationRelease(models.Model):
    _name = 'application_server.application.version.release'
    _description = 'Version'
    _order = 'version_id, no desc'

    name = fields.Char(string='Name', required=True)
    no = fields.Integer(string="No", required=True)
    version_id = fields.Many2one('application_server.application.version', string='Versions', required=True)
    application_id = fields.Many2one(
        'application_server.application.version', string='Application', readonly=True
    )

    def name_get(self):
        if not self.ids:
            return []
        res = []
        for rel in self.browse(self.ids):
            name = ' '.join([
                tools.ustr(rel.application_id.name),
                tools.ustr(rel.version_id.name),
                rel.name
            ])
            res.append((rel.id, name))
        return res


class ApplicationServerServerOS(models.Model):
    _name = 'application_server.server.os'
    _description = 'Operating System'

    name = fields.Char(string='Name', required=True)
    platform = fields.Selection([('win', 'Windows'), ('linux', 'Linux')], string='Platform', required=True)


class ApplicationServerServerDBVersion(models.Model):
    _name = 'application_server.server.db_version'
    _description = 'Application Server Database Version'

    name = fields.Char(string='Name', required=True)


class ApplicationServerServerConnectType(models.Model):
    _name = 'application_server.server.connect_type'
    _description = 'Application Server Connection Type'

    name = fields.Char(string='Name', required=True)


class ApplicationServerServerPythonVersion(models.Model):
    _name = 'application_server.server.python_version'
    _description = 'Application Server Python Version'

    name = fields.Char(string='Name', required=True)
