import xmlrpc.client

url_openerp = "http://localhost:8069"
db_openerp = 'database_name'
username_openerp = 'openerp_username'
password_openerp = 'openerp_password'

common_openerp = xmlrpc.client.ServerProxy('%s/xmlrpc/common' % url_openerp)
uid_openerp = common_openerp.login(db_openerp, username_openerp, password_openerp)
sock_openerp = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/object')

domain = []
server_ids = sock_openerp.execute(db_openerp, uid_openerp, password_openerp, 'application_server.server', 'search', domain)
partner_ids = sock_openerp.execute(db_openerp, uid_openerp, password_openerp, 'res.partner', 'search', domain)
partner_address_ids = sock_openerp.execute(db_openerp, uid_openerp, password_openerp, 'res.partner.address', 'search', domain)
#fields to read
server_fields = [
    'name',
    'active',
    'partner_id',
    'comment',
    'portal_username',
    'portal_password',
    'ssh_username',
    'ssh_port',
    'host',
    'port',
    'db_port',
    'db_host',
    'log_path',
    'server_restart',
    'connection',
    'connection_client',
    'restart_cmd',
    'configs',
    'versions_archive_path',
    'addons_path',
    'venv_path'
    ]
partner_fields = [
    'search_name',
    'active',
    'ref'
    ]
partner_address_fields = [
    'name',
    'type',
    'phone',
    'mobile',
    'email',
    'street',
    'street2',
    'zip',
    'partner_id'
]
server_data = sock_openerp.execute(db_openerp, uid_openerp, password_openerp, 'application_server.server', 'read', server_ids, server_fields)
partner_data = sock_openerp.execute(db_openerp, uid_openerp, password_openerp, 'res.partner', 'read', partner_ids, partner_fields)
partner_address_data = sock_openerp.execute(db_openerp, uid_openerp, password_openerp, 'res.partner.address', 'read', partner_address_ids, partner_address_fields)


url = 'http://odoo-url.lt:8069'
db = 'odoo_database'
username = 'odoo_username'
password = 'odoo_password'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

uid = common.authenticate(db, username, password, {})

def create_server_odoo(server_data, db, password, models, uid):
    for server in server_data:
        server['description'] = server.pop('comment')
        server_id_odoo = models.execute(db, uid, password, 'application_server.server', 'search', [('name', '=', server['name'])])
        if server_id_odoo:
            print(f"Server { server['name'] } already exists.")
        else:
            print(f"Creating new server { server['name'] }.")
            partner_name = server['partner_id'][1]
            partner_id_odoo = models.execute(db, uid, password, 'res.partner', 'search', [('name', '=', partner_name)])
            if not partner_id_odoo:
                continue
            else:
                partner_id_odoo = partner_id_odoo[0]
            server['partner_id'] = partner_id_odoo
            if not server['ssh_username']:
                server['ssh_username'] = 'MISSING'
            models.execute(db, uid, password, 'application_server.server', 'create', [server])

def create_partner_odoo(partner_data, db, password, models, uid):
    for partner in partner_data:
        partner['name'] = partner.pop('search_name')
        del partner['id']
        partner_id_odoo = models.execute(db, uid, password, 'res.partner', 'search', [('name', '=', partner['name'])])
        if partner_id_odoo:
            print(f"Partner { partner['name'] } already exists.")
        else:
            print(f"Creating new partner { partner['name'] }.")
            models.execute_kw(db, uid, password, 'res.partner', 'create', [partner])

def create_partner_address_odoo(partner_address_data, db, password, models, uid):
    for partner_address in partner_address_data:
        if partner_address['partner_id'] and partner_address['name']:        
            partner_id_odoo = models.execute(db, uid, password, 'res.partner', 'search', [('name', '=', partner_address['partner_id'][1])])
            if not partner_id_odoo:
                continue
            if partner_address['type'] == 'default':
                partner_address['type'] = 'other'
            partner_address['parent_id'] = partner_id_odoo[0]
            del partner_address['partner_id']
            del partner_address['id']

            partner_address_id_odoo = models.execute(db, uid, password, 'res.partner', 'search', [('name', '=', partner_address['name'])])
            if partner_address_id_odoo:
                print(f"Partner address { partner_address['name'] } already exists.")
            else:
                print(f"Creating new partner address { partner_address['name'] }.")
                models.execute_kw(db, uid, password, 'res.partner', 'create', [partner_address])

if __name__ == '__main__':
    create_partner_odoo(partner_data, db, password, models, uid)
    create_partner_address_odoo(partner_address_data, db, password, models, uid)
    create_server_odoo(server_data, db, password, models, uid)
