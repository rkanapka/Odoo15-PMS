{
    'name': 'CRnD Web Diagram Plus',
    'category': 'Technical Settings',
    'summary': """
        Odoo Web Diagram view by CRnD.
    """,
    'author': 'Center of Research and Development',
    'support': 'info@crnd.pro',
    'website': 'https://crnd.pro',
    'license': 'LGPL-3',
    'version': '15.0.0.5.0',
    'depends': [
        'web',
    ],
    'data': [
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crnd_web_diagram_plus15/static/src/scss/diagram_view.scss',
            'crnd_web_diagram_plus15/static/src/js/vec2.js',
            'crnd_web_diagram_plus15/static/src/js/graph.js',
            'crnd_web_diagram_plus15/static/src/js/diagram_model.js',
            'crnd_web_diagram_plus15/static/src/js/diagram_controller.js',
            'crnd_web_diagram_plus15/static/src/js/diagram_renderer.js',
            'crnd_web_diagram_plus15/static/src/js/diagram_view.js',
            'crnd_web_diagram_plus15/static/src/js/view_registry.js',
        ],
        'web.qunit_suite_tests': [
            ('after', 'web/static/tests/legacy/views/kanban_tests.js',
             'crnd_web_diagram_plus15/static/tests/diagram_tests.js')
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,

}
