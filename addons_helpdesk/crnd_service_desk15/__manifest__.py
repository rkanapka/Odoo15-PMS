{
    'name': 'Service Desk',
    'category': 'Service Desk',
    'summary': """
        Process addon for the Website Service Desk application.
    """,
    'author': "Center of Research and Development",
    'website': "https://crnd.pro",
    'license': 'LGPL-3',
    'version': '15.0.1.4.0',
    'depends': [
        'generic_request15',
    ],
    'data': [
        'data/init_data.xml',
        'data/request_type_incident.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
