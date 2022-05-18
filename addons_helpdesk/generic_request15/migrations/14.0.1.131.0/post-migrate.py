from odoo import api, SUPERUSER_ID


def migrate(cr, installed_version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = env['request.request'].search([('email_from', '!=', False)])
    for request in requests:
        try:
            author_name, author_email = request.env[
                'res.partner'
            ]._parse_partner_name(request.email_from)
        except Exception:  # nosec
            continue

        if not author_email or '@' not in author_email:
            continue

        data = {
            'email_from': author_email,
        }
        if not request.author_name and author_name:
            data['author_name'] = author_name

        request.write(data)
