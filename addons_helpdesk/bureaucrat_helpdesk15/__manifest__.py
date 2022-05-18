{
    'name': "Bureaucrat Helpdesk",

    'summary': """
        Help desk
    """,

    'author': "Center of Research and Development",
    'website': "https://crnd.pro",
    'version': '15.0.1.3.0',
    'category': 'Helpdesk',

    # any module necessary for this one to work correctly
    'depends': [
        'bureaucrat_helpdesk_lite15',
    ],

    # always loaded
    'data': [
    ],
    'images': ['static/description/banner.gif'],
    'demo': [],

    'installable': True,
    'application': True,
    'license': 'OPL-1',

    'price': 1.0,
    'currency': 'EUR',
    "live_test_url": "https://yodoo.systems/saas/template/bureaucrat-itsm-16",
}
